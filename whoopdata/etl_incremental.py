"""
Incremental ETL loading module for efficient data updates.

This module provides intelligent date range calculation for fetching only
recent data from WHOOP and Withings APIs, making daily ETL runs much faster.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from whoopdata.models.models import Recovery, Sleep, Workout, Cycle, WithingsWeight, WithingsHeartRate


def get_latest_timestamps(db: Session) -> Dict[str, Optional[datetime]]:
    """
    Query database to find the latest timestamp for each data type.

    Args:
        db: Database session

    Returns:
        Dict with latest timestamps for each data type:
        {
            'recovery': datetime or None,
            'sleep': datetime or None,
            'workout': datetime or None,
            'withings_weight': datetime or None,
            'withings_heart_rate': datetime or None
        }
    """
    timestamps = {}

    # WHOOP Recovery - use created_at
    try:
        latest_recovery = db.query(Recovery).order_by(Recovery.created_at.desc()).first()
        timestamps["recovery"] = latest_recovery.created_at if latest_recovery else None
    except Exception:
        timestamps["recovery"] = None

    # WHOOP Sleep - use created_at
    try:
        latest_sleep = db.query(Sleep).order_by(Sleep.created_at.desc()).first()
        timestamps["sleep"] = latest_sleep.created_at if latest_sleep else None
    except Exception:
        timestamps["sleep"] = None

    # WHOOP Workout - use created_at
    try:
        latest_workout = db.query(Workout).order_by(Workout.created_at.desc()).first()
        timestamps["workout"] = latest_workout.created_at if latest_workout else None
    except Exception:
        timestamps["workout"] = None

    # WHOOP Cycle - use created_at
    try:
        latest_cycle = db.query(Cycle).order_by(Cycle.created_at.desc()).first()
        timestamps["cycle"] = latest_cycle.created_at if latest_cycle else None
    except Exception:
        timestamps["cycle"] = None

    # Withings Weight - use datetime
    try:
        latest_weight = (
            db.query(WithingsWeight)
            .filter(WithingsWeight.datetime.isnot(None))
            .order_by(WithingsWeight.datetime.desc())
            .first()
        )
        timestamps["withings_weight"] = latest_weight.datetime if latest_weight else None
    except Exception:
        timestamps["withings_weight"] = None

    # Withings Heart Rate - use datetime
    try:
        latest_hr = (
            db.query(WithingsHeartRate)
            .filter(WithingsHeartRate.datetime.isnot(None))
            .order_by(WithingsHeartRate.datetime.desc())
            .first()
        )
        timestamps["withings_heart_rate"] = latest_hr.datetime if latest_hr else None
    except Exception:
        timestamps["withings_heart_rate"] = None

    return timestamps


def calculate_fetch_window(
    latest_timestamp: Optional[datetime], safety_days: int = 1
) -> Tuple[Optional[datetime], datetime]:
    """
    Calculate the date window for fetching data.

    Strategy:
    - If no latest timestamp (empty DB): Return (None, now) for full load
    - If latest timestamp exists: Return (latest - safety_days, now) for incremental

    The safety_days buffer ensures we catch any late-arriving data and always
    include the current day for intraday updates.

    Args:
        latest_timestamp: Most recent timestamp in database for this data type
        safety_days: Number of days to go back from latest (default: 1)

    Returns:
        Tuple of (start_datetime, end_datetime)
        - start_datetime is None for full load
        - end_datetime is always current time
    """
    now = datetime.utcnow()

    # Empty database - do full load
    if latest_timestamp is None:
        return (None, now)

    # Incremental load - fetch from (latest - safety_days) to now
    # This ensures we always include yesterday + today
    start = latest_timestamp - timedelta(days=safety_days)

    return (start, now)


def format_datetime_for_whoop(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime for WHOOP API (ISO 8601 with Z suffix).

    Args:
        dt: Datetime object or None

    Returns:
        ISO formatted string like "2022-04-24T11:25:44.774Z" or None
    """
    if dt is None:
        return None

    # WHOOP expects ISO 8601 format with Z suffix
    # Format: 2022-04-24T11:25:44.774Z
    return dt.isoformat(timespec="milliseconds") + "Z"


def format_datetime_for_withings(dt: Optional[datetime]) -> Optional[int]:
    """
    Format datetime for Withings API (unix timestamp).

    Args:
        dt: Datetime object or None

    Returns:
        Unix timestamp (seconds since epoch) or None
    """
    if dt is None:
        return None

    # Withings expects unix timestamp (seconds)
    return int(dt.timestamp())


def should_use_incremental_load(db: Session, force_full_load: bool = False) -> bool:
    """
    Determine if incremental loading should be used.

    Args:
        db: Database session
        force_full_load: If True, always return False (force full load)

    Returns:
        True if incremental load should be used, False for full load
    """
    if force_full_load:
        return False

    # Check if database has any data
    timestamps = get_latest_timestamps(db)

    # If any data type has records, use incremental
    has_data = any(ts is not None for ts in timestamps.values())

    return has_data


def get_fetch_windows_for_all_types(
    db: Session, incremental: bool = True
) -> Dict[str, Tuple[Optional[datetime], datetime]]:
    """
    Get fetch windows for all data types.

    Args:
        db: Database session
        incremental: If True, calculate incremental windows; if False, use full load

    Returns:
        Dict with fetch windows for each data type:
        {
            'recovery': (start_dt, end_dt),
            'sleep': (start_dt, end_dt),
            'workout': (start_dt, end_dt),
            'withings_weight': (start_dt, end_dt),
            'withings_heart_rate': (start_dt, end_dt)
        }
    """
    if not incremental:
        # Full load - return None start dates
        now = datetime.utcnow()
        return {
            "recovery": (None, now),
            "sleep": (None, now),
            "workout": (None, now),
            "cycle": (None, now),
            "withings_weight": (None, now),
            "withings_heart_rate": (None, now),
        }

    # Get latest timestamps
    timestamps = get_latest_timestamps(db)

    # Calculate windows for each type
    windows = {}
    for data_type, latest_ts in timestamps.items():
        windows[data_type] = calculate_fetch_window(latest_ts)

    return windows
