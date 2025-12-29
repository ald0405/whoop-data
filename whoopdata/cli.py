#!/usr/bin/env python3
"""
Complete Health Data Application Launcher
1. Loads data from WHOOP and Withings APIs
2. Starts FastAPI server with all endpoints
3. One-command setup for the complete health data platform
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.abspath("."))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def check_dependencies():
    """Check if required packages are installed"""
    console.print("🔍 [bold]Checking dependencies...[/bold]")

    required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pandas", "requests", "rich"]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        console.print(f"❌ [bold red]Missing packages: {', '.join(missing)}[/bold red]")
        console.print("💡 Install with: pip install " + " ".join(missing))
        return False

    console.print("✅ [bold green]All dependencies found[/bold green]")
    return True


def ensure_database_tables():
    """Ensure all database tables exist"""
    try:
        from whoopdata.database.database import engine
        from whoopdata.models.models import Base

        console.print("🗄️  [bold]Ensuring database tables exist...[/bold]")

        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)

        console.print("✅ [bold green]Database tables ready[/bold green]")
        return True

    except Exception as e:
        console.print(f"❌ [bold red]Failed to create database tables: {str(e)}[/bold red]")
        return False


def run_data_pipeline(incremental=True):
    """Run the complete ETL pipeline

    Args:
        incremental: If True, use incremental loading (fetch only recent data).
                    If False, do full load (fetch all historical data).
    """
    mode_str = "Incremental Load" if incremental else "Full Load"
    console.print("\n" + "=" * 60)
    console.print(f"📊 [bold cyan]Running Data Pipeline ({mode_str})[/bold cyan]")
    console.print("=" * 60)

    # First ensure database tables exist
    if not ensure_database_tables():
        console.print("❌ [bold red]Cannot proceed without database tables[/bold red]")
        return False

    try:
        # Import and run the ETL pipeline
        from whoopdata.etl import run_complete_etl

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:

            task = progress.add_task("Loading health data from APIs...", total=None)
            results = run_complete_etl(incremental=incremental)
            progress.update(task, completed=True)

        # Count total records
        total_success = sum(stats["success"] for stats in results.values())
        total_errors = sum(stats["errors"] for stats in results.values())

        console.print(f"\n🎉 [bold green]Data Pipeline Complete![/bold green]")
        console.print(f"📈 Records loaded: {total_success}")
        console.print(f"❌ Errors: {total_errors}")

        return total_success > 0

    except ImportError as e:
        console.print(f"❌ [bold red]Could not import ETL pipeline: {e}[/bold red]")
        console.print("💡 Make sure all files are in the correct location")
        return False
    except Exception as e:
        console.print(f"❌ [bold red]Data pipeline failed: {str(e)}[/bold red]")
        return False


def show_available_endpoints():
    """Show available API endpoints"""
    console.print("\n" + "=" * 60)
    console.print("🌐 [bold cyan]Available API Endpoints[/bold cyan]")
    console.print("=" * 60)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="dim", width=15)
    table.add_column("Endpoint", style="cyan", width=35)
    table.add_column("Description", width=30)

    endpoints = [
        ("WHOOP", "/recovery", "Recovery scores and metrics"),
        ("WHOOP", "/recovery/latest", "Most recent recovery"),
        ("WHOOP", "/workout", "Workout data and strain"),
        ("WHOOP", "/workout/latest", "Most recent workout"),
        ("WHOOP", "/sleep", "Sleep performance data"),
        ("WHOOP", "/sleep/latest", "Most recent sleep"),
        ("Withings", "/withings/weight", "Weight and body composition"),
        ("Withings", "/withings/weight/latest", "Most recent weight"),
        ("Withings", "/withings/weight/stats", "Weight statistics"),
        ("Withings", "/withings/heart-rate", "Heart rate and blood pressure"),
        ("Withings", "/withings/heart-rate/latest", "Most recent heart rate"),
        ("Withings", "/withings/summary", "Withings data summary"),
        ("General", "/docs", "Interactive API documentation"),
        ("General", "/redoc", "Alternative API docs"),
    ]

    for category, endpoint, description in endpoints:
        table.add_row(category, endpoint, description)

    console.print(table)

    console.print(f"\n💡 [bold]Quick test URLs:[/bold]")
    console.print("   • Latest recovery: http://localhost:8000/recovery/latest")
    console.print("   • Latest weight: http://localhost:8000/withings/weight/latest")
    console.print("   • API docs: http://localhost:8000/docs")


def start_fastapi_server():
    """Start the FastAPI server"""
    console.print("\n" + "=" * 60)
    console.print("🚀 [bold cyan]Starting FastAPI Server[/bold cyan]")
    console.print("=" * 60)

    console.print("🌐 [bold]Server will be available at:[/bold]")
    console.print("   • Main API: http://localhost:8000")
    console.print("   • Interactive Docs: http://localhost:8000/docs")
    console.print("   • ReDoc: http://localhost:8000/redoc")

    console.print("\n⚡ [bold yellow]Starting uvicorn server...[/bold yellow]")
    console.print("Press Ctrl+C to stop the server\n")

    try:
        # Start uvicorn server
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [bold red]Failed to start server: {e}[/bold red]")
        console.print("💡 Try: pip install uvicorn")
        return False
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold yellow]Server stopped by user[/bold yellow]")
        return True

    return True


def run_analytics_pipeline():
    """Run the ML analytics pipeline"""
    console.print("\n" + "=" * 60)
    console.print("🤖 [bold cyan]Running Analytics Pipeline[/bold cyan]")
    console.print("=" * 60)

    try:
        from whoopdata.pipelines.analytics_pipeline import run_analytics_pipeline

        run_analytics_pipeline(days_back=365)
        return True

    except Exception as e:
        console.print(f"❌ [bold red]Analytics pipeline failed: {str(e)}[/bold red]")
        import traceback

        console.print(traceback.format_exc())
        return False


def main():
    """Main application launcher"""

    # Welcome message
    console.print(
        Panel.fit(
            "🏥 [bold]Complete Health Data Platform[/bold] 🏥\n"
            "WHOOP + Withings Integration with FastAPI\n\n"
            "[dim]This will:\n"
            "1. Load data from WHOOP and Withings APIs\n"
            "2. Store data in local database\n"
            "3. Start FastAPI server with all endpoints[/dim]",
            style="bold magenta",
        )
    )

    # Check if we should run data pipeline
    console.print("\n🤔 [bold]What would you like to do?[/bold]")
    console.print(
        "1. Run complete pipeline - incremental load (load data + start server) [recommended]"
    )
    console.print("2. Run complete pipeline - full load (load all historical data + start server)")
    console.print("3. Skip data loading and just start server")
    console.print("4. Only run data pipeline - incremental load (no server)")
    console.print("5. Only run data pipeline - full load (no server)")
    console.print("6. Run analytics pipeline (train ML models + compute insights)")

    try:
        choice = input("\nEnter choice (1-6) [default: 1]: ").strip() or "1"

        if choice == "1":
            # Complete pipeline - incremental
            if not check_dependencies():
                return 1

            # Run data pipeline with incremental loading
            data_success = run_data_pipeline(incremental=True)

            if not data_success:
                console.print(
                    "⚠️ [bold yellow]Data pipeline had issues, but continuing with server...[/bold yellow]"
                )

            # Show endpoints
            show_available_endpoints()

            # Start server
            start_fastapi_server()

        elif choice == "2":
            # Complete pipeline - full load
            if not check_dependencies():
                return 1

            # Run data pipeline with full loading
            data_success = run_data_pipeline(incremental=False)

            if not data_success:
                console.print(
                    "⚠️ [bold yellow]Data pipeline had issues, but continuing with server...[/bold yellow]"
                )

            # Show endpoints
            show_available_endpoints()

            # Start server
            start_fastapi_server()

        elif choice == "3":
            # Just start server
            if not check_dependencies():
                return 1

            show_available_endpoints()
            start_fastapi_server()

        elif choice == "4":
            # Only data pipeline - incremental
            if not check_dependencies():
                return 1

            run_data_pipeline(incremental=True)
            console.print(
                "\n✅ [bold green]Data pipeline complete! Use choice 3 to start server later.[/bold green]"
            )

        elif choice == "5":
            # Only data pipeline - full load
            if not check_dependencies():
                return 1

            run_data_pipeline(incremental=False)
            console.print(
                "\n✅ [bold green]Data pipeline complete! Use choice 3 to start server later.[/bold green]"
            )

        elif choice == "6":
            # Analytics pipeline
            if not check_dependencies():
                return 1

            success = run_analytics_pipeline()
            if success:
                console.print(
                    "\n✅ [bold green]Analytics pipeline complete! ML models trained and insights computed.[/bold green]"
                )
                console.print(
                    "💡 Use choice 3 to start server and access analytics via /analytics/* endpoints"
                )
            else:
                console.print(
                    "\n❌ [bold red]Analytics pipeline failed. See errors above.[/bold red]"
                )

        else:
            console.print("❌ Invalid choice. Please run again with 1-6.")
            return 1

    except KeyboardInterrupt:
        console.print("\n⚠️ [bold yellow]Cancelled by user[/bold yellow]")
        return 0
    except Exception as e:
        console.print(f"❌ [bold red]Application failed: {str(e)}[/bold red]")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
