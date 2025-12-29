"""Analytics results table for pre-computed ML insights.

This table stores pre-computed analytics results to avoid
training models on every API request.
"""

import sqlite3
from pathlib import Path


def create_analytics_results_table():
    """Create analytics_results table if it doesn't exist."""
    db_path = Path(__file__).parent / "whoop.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_type TEXT NOT NULL,
            result_data TEXT NOT NULL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            days_back INTEGER,
            UNIQUE(result_type, days_back)
        )
    """
    )

    # Create index for faster lookups
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_result_type 
        ON analytics_results(result_type)
    """
    )

    conn.commit()
    conn.close()
    print("✅ Analytics results table created")


if __name__ == "__main__":
    create_analytics_results_table()
