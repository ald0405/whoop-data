#!/usr/bin/env python3
"""Script to remove duplicate records from WHOOP database tables."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "whoopdata" / "database" / "whoop.db"


def cleanup_duplicates(table_name: str, unique_column: str):
    """
    Remove duplicate records from a table, keeping only the most recent (highest id).
    
    Args:
        table_name: Name of the table to clean
        unique_column: Column that should be unique (e.g., 'cycle_id', 'sleep_id')
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find duplicates
    cursor.execute(f"""
        SELECT {unique_column}, COUNT(*) as count 
        FROM {table_name} 
        GROUP BY {unique_column} 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print(f"✅ No duplicates found in {table_name}")
        conn.close()
        return
    
    print(f"🔍 Found {len(duplicates)} duplicate {unique_column}s in {table_name}")
    
    total_deleted = 0
    
    # For each duplicate, keep the one with the highest id (most recent)
    for unique_val, count in duplicates:
        cursor.execute(f"""
            SELECT id FROM {table_name}
            WHERE {unique_column} = ?
            ORDER BY id DESC
        """, (unique_val,))
        
        ids = [row[0] for row in cursor.fetchall()]
        
        # Keep the first (highest id), delete the rest
        ids_to_delete = ids[1:]
        
        if ids_to_delete:
            placeholders = ','.join('?' * len(ids_to_delete))
            cursor.execute(f"""
                DELETE FROM {table_name}
                WHERE id IN ({placeholders})
            """, ids_to_delete)
            
            total_deleted += len(ids_to_delete)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Deleted {total_deleted} duplicate records from {table_name}")


def main():
    """Clean up duplicates from all tables."""
    print("🧹 Starting database cleanup...\n")
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    # Clean up each table
    tables_to_clean = [
        ("recovery", "cycle_id"),
        ("sleep", "sleep_id"),
        ("workout", "workout_id")
    ]
    
    for table_name, unique_column in tables_to_clean:
        try:
            cleanup_duplicates(table_name, unique_column)
        except sqlite3.OperationalError as e:
            print(f"⚠️  Error cleaning {table_name}: {e}")
    
    print("\n✨ Database cleanup complete!")
    print("🔄 Restart your server to see the changes.")


if __name__ == "__main__":
    main()
