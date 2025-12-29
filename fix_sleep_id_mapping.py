#!/usr/bin/env python3
"""
Migration script to fix sleep_id foreign key values in recovery table.

The issue: Recovery records have sleep_id as UUID strings (from WHOOP API),
but they need to be mapped to the integer database ID of the Sleep records.
"""

from sqlalchemy import text
from whoopdata.database.database import SessionLocal
from whoopdata.models.models import Recovery, Sleep
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def fix_sleep_id_mapping():
    """Fix sleep_id values in recovery table by mapping UUID to integer ID."""

    console.print("[bold cyan]🔧 Starting sleep_id migration...[/bold cyan]\n")

    db = SessionLocal()

    try:
        # Get all recovery records
        recoveries = db.query(Recovery).all()
        console.print(f"Found {len(recoveries)} recovery records\n")

        fixed_count = 0
        null_count = 0
        error_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task(f"Processing recovery records...", total=len(recoveries))

            for recovery in recoveries:
                try:
                    # Check if sleep_id looks like a UUID string
                    if recovery.sleep_id and isinstance(recovery.sleep_id, str):
                        # Try to find matching sleep record by whoop_id
                        sleep_record = (
                            db.query(Sleep).filter(Sleep.whoop_id == recovery.sleep_id).first()
                        )

                        if sleep_record:
                            # Update with integer ID
                            recovery.sleep_id = sleep_record.id
                            fixed_count += 1
                        else:
                            # No matching sleep record found
                            recovery.sleep_id = None
                            null_count += 1
                    elif recovery.sleep_id is None:
                        null_count += 1

                    progress.update(task, advance=1)

                except Exception as e:
                    console.print(f"[red]Error processing recovery {recovery.id}: {str(e)}[/red]")
                    error_count += 1
                    progress.update(task, advance=1)

        # Commit changes
        db.commit()

        console.print(f"\n[bold green]✅ Migration complete![/bold green]")
        console.print(f"  • Fixed: {fixed_count} records")
        console.print(f"  • Set to NULL (no matching sleep): {null_count} records")
        console.print(f"  • Errors: {error_count} records")

    except Exception as e:
        console.print(f"[bold red]❌ Migration failed: {str(e)}[/bold red]")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_sleep_id_mapping()
