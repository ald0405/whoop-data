#!/usr/bin/env python3
"""
Combined Extract-Transform-Load script for WHOOP and Withings data
Seamless setup and data pipeline for both health platforms
"""

from sqlalchemy.orm import sessionmaker
from whoopdata.analysis.whoop_client import Whoop
from whoopdata.clients.withings_client import WithingsClient
from whoopdata.models.models import Recovery, Cycle, Workout, Sleep, WithingsWeight, WithingsHeartRate
from datetime import datetime
from whoopdata.utils import DBLoader
from whoopdata.model_transformation import (
    transform_sleep,
    transform_recovery,
    transform_workout,
    transform_withings_weight,
    transform_withings_heart_rate,
)
import sys
import os
from rich import print as rich_print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from whoopdata.database.database import SessionLocal, engine

console = Console()

# Add current directory to path
sys.path.append(os.path.abspath("."))

# DB setup
db = SessionLocal()
loader = DBLoader(db)


def whoop_etl_run(whoop_endpoint, transformer, loader_fn, start_date=None, end_date=None):
    """
    Generic Extract-Transform-Load function for WHOOP API data.
    
    Args:
        whoop_endpoint: Name of WHOOP endpoint (recovery, workout, sleep)
        transformer: Transform function for the data
        loader_fn: Database loader function
        start_date: Start date in ISO 8601 format (e.g. "2022-04-24T11:25:44.774Z")
        end_date: End date in ISO 8601 format (e.g. "2022-04-24T11:25:44.774Z")
    """
    console.print(f"🔄 [bold blue]Starting WHOOP {whoop_endpoint} ETL...[/bold blue]")
    
    try:
        whoop = Whoop()
        whoop.authenticate()
        
        # Get data as DataFrame (already transformed for database compatibility)
        df = whoop.make_paginated_request(
            whoop.get_endpoint_url(endpoint_name=whoop_endpoint),
            transform_for_db=True,
            start=start_date,
            end=end_date
        )
        
        console.print(f"📊 Processing {len(df)} {whoop_endpoint} records...")
        
        success_count = 0
        error_count = 0
        
        # Convert DataFrame to records and process each one
        for index, row in df.iterrows():
            try:
                # Convert pandas Series to dict
                item_dict = row.to_dict()
                
                # Apply transformer
                data = transformer(item_dict)
                
                # Load into database
                loader_fn(data)
                success_count += 1
                
            except Exception as e:
                console.print(f"❌ Error processing record {index}: {str(e)}")
                error_count += 1
        
        console.print(f"✅ [bold green]WHOOP {whoop_endpoint}: {success_count} successful, {error_count} errors[/bold green]")
        return success_count, error_count
        
    except Exception as e:
        console.print(f"❌ [bold red]WHOOP {whoop_endpoint} ETL failed: {str(e)}[/bold red]")
        return 0, 1


def withings_etl_run(data_type="weight", limit=None, startdate=None, enddate=None):
    """
    Extract-Transform-Load function for Withings data.
    
    Args:
        data_type: "weight" or "heart_rate"
        limit: Maximum number of records to process (None for all)
        startdate: Start date as unix timestamp (seconds since epoch)
        enddate: End date as unix timestamp (seconds since epoch)
    """
    console.print(f"🏥 [bold blue]Starting Withings {data_type} ETL...[/bold blue]")
    
    try:
        client = WithingsClient()
        client.authenticate()
        
        success_count = 0
        error_count = 0
        
        if data_type == "weight":
            # Get body measurements
            response = client.get_body_measurements(startdate=startdate, enddate=enddate)
            df = client.transform_to_dataframe(response)
            
            if limit:
                df = df.head(limit)
            
            console.print(f"📊 Processing {len(df)} weight/body composition records...")
            
            # Group by measurement group ID to combine measurements
            grouped = df.groupby('grpid')
            
            for grpid, group in grouped:
                try:
                    # Create a combined record for this measurement group
                    base_record = group.iloc[0].to_dict()  # Use first record as base
                    
                    # Add all measurement values to the record
                    for _, row in group.iterrows():
                        measure_type = row['measure_type']
                        actual_value = row['actual_value']
                        
                        if measure_type == 1:  # Weight
                            base_record['weight_kg'] = actual_value
                        elif measure_type == 4:  # Height
                            base_record['height_m'] = actual_value
                        elif measure_type == 5:  # Fat Free Mass
                            base_record['fat_free_mass_kg'] = actual_value
                        elif measure_type == 6:  # Fat Ratio
                            base_record['fat_ratio_percent'] = actual_value
                        elif measure_type == 8:  # Fat Mass
                            base_record['fat_mass_kg'] = actual_value
                        elif measure_type == 76:  # Muscle Mass
                            base_record['muscle_mass_kg'] = actual_value
                        elif measure_type == 77:  # Hydration
                            base_record['hydration_kg'] = actual_value
                        elif measure_type == 88:  # Bone Mass
                            base_record['bone_mass_kg'] = actual_value
                        elif measure_type == 170:  # Visceral Fat
                            base_record['visceral_fat'] = actual_value
                    
                    # Transform for database
                    data = {
                        "user_id": "default_user",
                        "grpid": base_record.get("grpid"),
                        "deviceid": base_record.get("deviceid"),
                        "created_at": datetime.now(),
                        "updated_at": base_record.get("datetime"),
                        "date": base_record.get("date"),
                        "datetime": base_record.get("datetime"),
                        "timezone": base_record.get("timezone"),
                        "comment": base_record.get("comment"),
                        "category": base_record.get("category", 1),
                        "weight_kg": base_record.get("weight_kg"),
                        "height_m": base_record.get("height_m"),
                        "fat_free_mass_kg": base_record.get("fat_free_mass_kg"),
                        "fat_ratio_percent": base_record.get("fat_ratio_percent"),
                        "fat_mass_kg": base_record.get("fat_mass_kg"),
                        "muscle_mass_kg": base_record.get("muscle_mass_kg"),
                        "bone_mass_kg": base_record.get("bone_mass_kg"),
                        "hydration_kg": base_record.get("hydration_kg"),
                        "visceral_fat": base_record.get("visceral_fat"),
                    }
                    
                    # Load into database
                    loader.load_withings_weight(data)
                    success_count += 1
                    
                except Exception as e:
                    console.print(f"❌ Error processing weight group {grpid}: {str(e)}")
                    error_count += 1
        
        elif data_type == "heart_rate":
            # Get heart rate measurements
            response = client.get_heart_measurements(startdate=startdate, enddate=enddate)
            df = client.transform_to_dataframe(response)
            
            if limit:
                df = df.head(limit)
            
            console.print(f"📊 Processing {len(df)} heart rate/BP records...")
            
            # Group by measurement group ID
            grouped = df.groupby('grpid')
            
            for grpid, group in grouped:
                try:
                    # Create a combined record for this measurement group
                    base_record = group.iloc[0].to_dict()
                    
                    # Add all measurement values to the record
                    for _, row in group.iterrows():
                        measure_type = row['measure_type']
                        actual_value = row['actual_value']
                        
                        if measure_type == 9:  # Diastolic BP
                            base_record['diastolic_bp_mmhg'] = actual_value
                        elif measure_type == 10:  # Systolic BP
                            base_record['systolic_bp_mmhg'] = actual_value
                        elif measure_type == 11:  # Heart Rate
                            base_record['heart_rate_bpm'] = actual_value
                    
                    # Transform for database
                    data = {
                        "user_id": "default_user",
                        "grpid": base_record.get("grpid"),
                        "deviceid": base_record.get("deviceid"),
                        "created_at": datetime.now(),
                        "updated_at": base_record.get("datetime"),
                        "date": base_record.get("date"),
                        "datetime": base_record.get("datetime"),
                        "timezone": base_record.get("timezone"),
                        "category": base_record.get("category", 1),
                        "heart_rate_bpm": base_record.get("heart_rate_bpm"),
                        "systolic_bp_mmhg": base_record.get("systolic_bp_mmhg"),
                        "diastolic_bp_mmhg": base_record.get("diastolic_bp_mmhg"),
                    }
                    
                    # Load into database
                    loader.load_withings_heart_rate(data)
                    success_count += 1
                    
                except Exception as e:
                    console.print(f"❌ Error processing heart rate group {grpid}: {str(e)}")
                    error_count += 1
        
        console.print(f"✅ [bold green]Withings {data_type}: {success_count} successful, {error_count} errors[/bold green]")
        return success_count, error_count
        
    except Exception as e:
        console.print(f"❌ [bold red]Withings {data_type} ETL failed: {str(e)}[/bold red]")
        return 0, 1


def run_complete_etl(incremental=True):
    """Run the complete ETL pipeline for both WHOOP and Withings.
    
    Args:
        incremental: If True, use incremental loading (fetch only recent data).
                    If False, do full load (fetch all historical data).
    """
    from whoopdata.etl_incremental import (
        get_fetch_windows_for_all_types,
        format_datetime_for_whoop,
        format_datetime_for_withings
    )
    
    mode_str = "Incremental" if incremental else "Full Load"
    console.print(Panel.fit(
        f"🚀 [bold]Complete Health Data ETL Pipeline[/bold] 🚀\n"
        f"Mode: [cyan]{mode_str}[/cyan]", 
        style="bold magenta"
    ))
    
    # Calculate fetch windows
    windows = get_fetch_windows_for_all_types(db, incremental=incremental)
    
    # Log date windows
    if incremental:
        console.print("\n📅 [bold]Fetch Windows:[/bold]")
        for data_type, (start, end) in windows.items():
            if start:
                console.print(f"   • {data_type}: {start.date()} to {end.date()}")
            else:
                console.print(f"   • {data_type}: Full load (empty database)")
    
    results = {}
    
    # WHOOP Data
    console.print("\n" + "="*60)
    console.print("[bold cyan]WHOOP Data Pipeline[/bold cyan]")
    console.print("="*60)
    
    # Recovery
    recovery_start, recovery_end = windows.get('recovery', (None, None))
    success, errors = whoop_etl_run(
        whoop_endpoint="recovery",
        transformer=transform_recovery,
        loader_fn=loader.load_recovery,
        start_date=format_datetime_for_whoop(recovery_start) if recovery_start else None,
        end_date=format_datetime_for_whoop(recovery_end) if recovery_end else None
    )
    results["whoop_recovery"] = {"success": success, "errors": errors}
    
    # Workout  
    workout_start, workout_end = windows.get('workout', (None, None))
    success, errors = whoop_etl_run(
        whoop_endpoint="workout",
        transformer=transform_workout,
        loader_fn=loader.load_workout,
        start_date=format_datetime_for_whoop(workout_start) if workout_start else None,
        end_date=format_datetime_for_whoop(workout_end) if workout_end else None
    )
    results["whoop_workout"] = {"success": success, "errors": errors}
    
    # Sleep
    sleep_start, sleep_end = windows.get('sleep', (None, None))
    success, errors = whoop_etl_run(
        whoop_endpoint="sleep",
        transformer=transform_sleep,
        loader_fn=loader.load_sleep,
        start_date=format_datetime_for_whoop(sleep_start) if sleep_start else None,
        end_date=format_datetime_for_whoop(sleep_end) if sleep_end else None
    )
    results["whoop_sleep"] = {"success": success, "errors": errors}
    
    # Withings Data
    console.print("\n" + "="*60)
    console.print("[bold cyan]Withings Data Pipeline[/bold cyan]")
    console.print("="*60)
    
    # Weight/Body Composition
    weight_start, weight_end = windows.get('withings_weight', (None, None))
    success, errors = withings_etl_run(
        data_type="weight",
        startdate=format_datetime_for_withings(weight_start) if weight_start else None,
        enddate=format_datetime_for_withings(weight_end) if weight_end else None
    )
    results["withings_weight"] = {"success": success, "errors": errors}
    
    # Heart Rate/Blood Pressure
    heart_start, heart_end = windows.get('withings_heart_rate', (None, None))
    success, errors = withings_etl_run(
        data_type="heart_rate",
        startdate=format_datetime_for_withings(heart_start) if heart_start else None,
        enddate=format_datetime_for_withings(heart_end) if heart_end else None
    )
    results["withings_heart_rate"] = {"success": success, "errors": errors}
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold green]ETL Pipeline Summary[/bold green]")
    console.print("="*60)
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Data Source", style="dim", width=20)
    table.add_column("Successful", justify="center", style="green")
    table.add_column("Errors", justify="center", style="red")
    table.add_column("Status", justify="center")
    
    total_success = 0
    total_errors = 0
    
    for source, stats in results.items():
        success = stats["success"]
        errors = stats["errors"]
        total_success += success
        total_errors += errors
        
        status = "✅ Success" if errors == 0 else "⚠️  With Errors" if success > 0 else "❌ Failed"
        
        table.add_row(
            source.replace("_", " ").title(),
            str(success),
            str(errors),
            status
        )
    
    console.print(table)
    
    console.print(f"\n[bold]Total Records Processed:[/bold] {total_success + total_errors}")
    console.print(f"[bold green]Successfully Loaded:[/bold green] {total_success}")
    console.print(f"[bold red]Errors:[/bold red] {total_errors}")
    
    # Show latest records
    show_sample_data()
    
    return results


def show_sample_data():
    """Show sample of the loaded data"""
    console.print("\n" + "="*60)
    console.print("[bold yellow]Sample Data Overview[/bold yellow]")
    console.print("="*60)
    
    try:
        # Latest recovery
        recovery = db.query(Recovery).order_by(Recovery.created_at.desc()).first()
        if recovery:
            console.print(f"🔋 [bold]Latest Recovery:[/bold] Score: {recovery.recovery_score}, "
                         f"RHR: {recovery.resting_heart_rate}, Category: {recovery.recovery_category()}")
        
        # Latest weight
        weight = db.query(WithingsWeight).filter(WithingsWeight.weight_kg.isnot(None))\
                   .order_by(WithingsWeight.datetime.desc()).first()
        if weight:
            console.print(f"⚖️  [bold]Latest Weight:[/bold] {weight.weight_kg}kg, "
                         f"BMI: {weight.bmi()}, Category: {weight.weight_category()}")
        
        # Latest workout
        workout = db.query(Workout).order_by(Workout.created_at.desc()).first()
        if workout:
            console.print(f"💪 [bold]Latest Workout:[/bold] Strain: {workout.strain}, "
                         f"Duration: {workout.zone_zero_minutes + workout.zone_one_minutes + workout.zone_two_minutes + workout.zone_three_minutes + workout.zone_four_minutes + workout.zone_five_minutes:.0f}min")
        
        # Data counts
        recovery_count = db.query(Recovery).count()
        weight_count = db.query(WithingsWeight).count()
        workout_count = db.query(Workout).count()
        sleep_count = db.query(Sleep).count()
        hr_count = db.query(WithingsHeartRate).count()
        
        console.print(f"\n📊 [bold]Database Summary:[/bold]")
        console.print(f"   • Recovery Records: {recovery_count}")
        console.print(f"   • Workout Records: {workout_count}")
        console.print(f"   • Sleep Records: {sleep_count}")
        console.print(f"   • Weight Records: {weight_count}")
        console.print(f"   • Heart Rate Records: {hr_count}")
        
    except Exception as e:
        console.print(f"❌ Error showing sample data: {str(e)}")


if __name__ == "__main__":
    console.print("🏥 [bold]Combined Health Data ETL Pipeline[/bold] 🏥")
    console.print("Integrating WHOOP + Withings data seamlessly\n")
    
    try:
        results = run_complete_etl()
        console.print("\n🎉 [bold green]ETL Pipeline Complete![/bold green] 🎉")
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold yellow]ETL Pipeline interrupted by user[/bold yellow]")
    except Exception as e:
        console.print(f"\n❌ [bold red]ETL Pipeline failed: {str(e)}[/bold red]")
    finally:
        db.close()