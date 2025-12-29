#!/bin/bash
# Daily ETL Script for WHOOP Data Platform
# This script runs the incremental ETL pipeline to fetch the latest health data
# 
# Usage:
#   ./scripts/daily_etl.sh
#
# Cron Example (runs daily at 11pm):
#   0 23 * * * /path/to/whoop-data/scripts/daily_etl.sh >> /path/to/whoop-data/logs/etl.log 2>&1
#
# Cron Example (runs every 4 hours):
#   0 */4 * * * /path/to/whoop-data/scripts/daily_etl.sh >> /path/to/whoop-data/logs/etl.log 2>&1

# Exit on any error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Log timestamp
echo "========================================="
echo "Running WHOOP Data ETL: $(date)"
echo "========================================="

# Run the incremental ETL pipeline using Python directly
# This bypasses the CLI menu and runs incremental load directly
python -c "
from whoopdata.etl import run_complete_etl
from whoopdata.database.database import engine
from whoopdata.models.models import Base
from rich.console import Console

console = Console()

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

# Run incremental ETL
console.print('[bold cyan]Starting incremental ETL pipeline...[/bold cyan]')
try:
    results = run_complete_etl(incremental=True)
    total_success = sum(stats['success'] for stats in results.values())
    total_errors = sum(stats['errors'] for stats in results.values())
    console.print(f'[bold green]✅ ETL Complete: {total_success} records loaded, {total_errors} errors[/bold green]')
except Exception as e:
    console.print(f'[bold red]❌ ETL failed: {str(e)}[/bold red]')
    exit(1)
"

# Log completion
echo "ETL completed successfully at $(date)"
echo ""
