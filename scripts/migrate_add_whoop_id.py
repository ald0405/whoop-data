#!/usr/bin/env python3
"""
Database migration: Add whoop_id column to Sleep and Workout tables

This migration:
1. Adds whoop_id column to Sleep table
2. Adds whoop_id column to Workout table
3. For existing records, this should be run on a fresh database

WARNING: If you have existing data, back it up first!
For production use, it's recommended to drop and recreate the database
or export/import data with the new schema.
"""

import sys
import os
from rich.console import Console
from rich.panel import Panel

# Add current directory to path
sys.path.append(os.path.abspath("."))

console = Console()


def migrate_database():
    """Add whoop_id column to existing tables"""
    try:
        from whoopdata.database.database import engine
        from sqlalchemy import text, inspect
        
        console.print("🔄 [bold]Starting database migration...[/bold]")
        
        inspector = inspect(engine)
        
        # Check if tables exist
        tables = inspector.get_table_names()
        
        with engine.begin() as conn:
            # Migrate Sleep table
            if 'sleep' in tables:
                columns = [col['name'] for col in inspector.get_columns('sleep')]
                
                if 'whoop_id' not in columns:
                    console.print("📝 Adding whoop_id to sleep table...")
                    
                    # Since SQLite doesn't support ADD COLUMN with constraints easily,
                    # we need to check if table has data
                    result = conn.execute(text("SELECT COUNT(*) FROM sleep"))
                    count = result.scalar()
                    
                    if count > 0:
                        console.print(f"⚠️  [yellow]Sleep table has {count} existing records![/yellow]")
                        console.print("⚠️  [yellow]Recommended: Drop the database and reload with new schema[/yellow]")
                        console.print("⚠️  [yellow]Or manually export data and reimport[/yellow]")
                        return False
                    else:
                        # Safe to add column if table is empty
                        conn.execute(text("ALTER TABLE sleep ADD COLUMN whoop_id VARCHAR"))
                        console.print("✅ Added whoop_id to empty sleep table")
                else:
                    console.print("✅ Sleep table already has whoop_id column")
            
            # Migrate Workout table
            if 'workout' in tables:
                columns = [col['name'] for col in inspector.get_columns('workout')]
                
                if 'whoop_id' not in columns:
                    console.print("📝 Adding whoop_id to workout table...")
                    
                    result = conn.execute(text("SELECT COUNT(*) FROM workout"))
                    count = result.scalar()
                    
                    if count > 0:
                        console.print(f"⚠️  [yellow]Workout table has {count} existing records![/yellow]")
                        console.print("⚠️  [yellow]Recommended: Drop the database and reload with new schema[/yellow]")
                        console.print("⚠️  [yellow]Or manually export data and reimport[/yellow]")
                        return False
                    else:
                        conn.execute(text("ALTER TABLE workout ADD COLUMN whoop_id VARCHAR"))
                        console.print("✅ Added whoop_id to empty workout table")
                else:
                    console.print("✅ Workout table already has whoop_id column")
        
        console.print("✅ [bold green]Migration completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"❌ [bold red]Migration failed: {str(e)}[/bold red]")
        return False


def drop_and_recreate():
    """Drop existing tables and recreate with new schema"""
    try:
        from whoopdata.database.database import engine
        from whoopdata.models.models import Base
        
        console.print("⚠️  [bold yellow]DROPPING ALL TABLES![/bold yellow]")
        console.print("⚠️  All existing data will be lost!")
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        console.print("🗑️  Dropped all tables")
        
        # Recreate with new schema
        Base.metadata.create_all(bind=engine)
        console.print("✅ [bold green]Created tables with new schema![/bold green]")
        
        return True
        
    except Exception as e:
        console.print(f"❌ [bold red]Failed to drop/recreate: {str(e)}[/bold red]")
        return False


def main():
    """Main migration function"""
    console.print(Panel.fit(
        "🔄 [bold]Database Migration: Add whoop_id columns[/bold] 🔄\n\n"
        "This will add the whoop_id column to Sleep and Workout tables.\n\n"
        "[yellow]Options:[/yellow]\n"
        "1. Migrate existing database (only works if tables are empty)\n"
        "2. Drop all tables and recreate (⚠️  DESTROYS ALL DATA)\n"
        "3. Cancel",
        style="bold cyan"
    ))
    
    try:
        choice = console.input("\n[bold]Enter your choice (1/2/3): [/bold]")
        
        if choice == "1":
            success = migrate_database()
            if not success:
                console.print("\n💡 Consider option 2 (drop & recreate) or manually backup/restore data")
        elif choice == "2":
            confirm = console.input("[bold red]Are you sure? Type 'yes' to confirm: [/bold red]")
            if confirm.lower() == 'yes':
                drop_and_recreate()
            else:
                console.print("❌ Cancelled")
        elif choice == "3":
            console.print("✋ Migration cancelled")
        else:
            console.print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold yellow]Cancelled by user[/bold yellow]")
    except Exception as e:
        console.print(f"\n❌ [bold red]Error: {str(e)}[/bold red]")


if __name__ == "__main__":
    main()
