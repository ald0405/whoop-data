"""Helper to load pre-computed analytics results from database."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime


class AnalyticsResultsLoader:
    """Load pre-computed analytics results from database."""

    def __init__(self):
        """Initialize loader."""
        self.db_path = Path(__file__).parent.parent / "database" / "whoop.db"

    def load_result(self, result_type: str, days_back: int = 365) -> Optional[Dict]:
        """Load analytics result from database.

        Args:
            result_type: Type of result (factor_importance, correlations, insights, trends, summary)
            days_back: Days parameter used when computing

        Returns:
            Dictionary with result data or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """SELECT result_data, computed_at FROM analytics_results 
               WHERE result_type = ? AND days_back = ?
               ORDER BY computed_at DESC LIMIT 1""",
            (result_type, days_back),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            data = json.loads(row[0])
            # Add metadata
            data["_computed_at"] = row[1]
            return data

        return None

    def result_exists(self, result_type: str, days_back: int = 365) -> bool:
        """Check if a result exists.

        Args:
            result_type: Type of result
            days_back: Days parameter

        Returns:
            True if result exists
        """
        return self.load_result(result_type, days_back) is not None


# Global instance
results_loader = AnalyticsResultsLoader()
