#!/usr/bin/env python3
"""
Database Table Creation Script
Creates all necessary tables for WHOOP and Withings data models
"""

import sys
import os
from rich.console import Console
from rich.panel import Panel

# Add current directory to path
sys.path.append(os.path.abspath("."))

console = Console()

def create_all_tables():
    """Create all database tables"""
    try:
        from whoopdata.database.database import engine
        from whoopdata.models.models import Base
        
        console.print("🗄️  [bold]Creating database tables...[/bold]")
        
        # Create all tables defined in Base metadata
        Base.metadata.create_all(bind=engine)
        
        console.print("✅ [bold green]All database tables created successfully![/bold green]")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        console.print(f"\n📊 [bold]Created tables ({len(table_names)}):[/bold]")
        for table_name in sorted(table_names):
            console.print(f"   • {table_name}")
        
        return True
        
    except Exception as e:
        console.print(f"❌ [bold red]Failed to create tables: {str(e)}[/bold red]")
        return False

def check_existing_tables():
    """Check what tables already exist"""
    try:
        from whoopdata.database.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        console.print(f"📋 [bold]Existing tables ({len(existing_tables)}):[/bold]")
        if existing_tables:
            for table_name in sorted(existing_tables):
                console.print(f"   • {table_name}")
        else:
            console.print("   (No tables found)")
        
        return existing_tables
        
    except Exception as e:
        console.print(f"❌ [bold red]Failed to check existing tables: {str(e)}[/bold red]")
        return []

def main():
    """Main function"""
    console.print(Panel.fit(
        "🗄️  [bold]Database Table Creation[/bold] 🗄️\n"
        "This will create all necessary tables for:\n"
        "• WHOOP data (recovery, workouts, sleep, cycles)\n"
        "• Withings data (weight, heart rate)\n\n"
        "[dim]Safe to run multiple times - won't delete existing data[/dim]",
        style="bold cyan"
    ))
    
    try:
        # Check existing tables
        console.print("\n" + "="*50)
        console.print("[bold yellow]Current Database State[/bold yellow]")
        console.print("="*50)
        existing_tables = check_existing_tables()
        
        # Create tables
        console.print("\n" + "="*50)
        console.print("[bold yellow]Creating Missing Tables[/bold yellow]")
        console.print("="*50)
        
        success = create_all_tables()
        
        if success:
            console.print("\n🎉 [bold green]Database setup complete![/bold green]")
            console.print("💡 You can now run the health app without table errors")
            return 0
        else:
            console.print("\n❌ [bold red]Database setup failed![/bold red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n⚠️ [bold yellow]Cancelled by user[/bold yellow]")
        return 0
    except Exception as e:
        console.print(f"\n❌ [bold red]Script failed: {str(e)}[/bold red]")
        return 1

if __name__ == "__main__":
    exit(main())