"""
Date filtering utilities for consistent datetime handling across different data sources.

Handles the complexity of different datetime fields and timezone considerations.
"""

from datetime import datetime, date
from typing import Optional, Tuple
from sqlalchemy import and_
from sqlalchemy.orm import Query


def parse_date_string(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string in YYYY-MM-DD format to datetime object.
    Returns None if date_str is None or invalid.
    """
    if not date_str:
        return None
    
    try:
        # Parse YYYY-MM-DD and set to start of day
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Try ISO format with time
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None


def get_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Convert date strings to datetime objects for filtering.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_dt = parse_date_string(start_date)
    end_dt = parse_date_string(end_date)
    
    # If end_date is provided, set to end of day
    if end_dt:
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_dt, end_dt


def apply_recovery_date_filter(query: Query, start_date: Optional[str], end_date: Optional[str]) -> Query:
    """
    Apply date filtering to Recovery queries using created_at field.
    """
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    if start_dt:
        from whoop_data.models.models import Recovery
        query = query.filter(Recovery.created_at >= start_dt)
    
    if end_dt:
        from whoop_data.models.models import Recovery
        query = query.filter(Recovery.created_at <= end_dt)
    
    return query


def apply_workout_date_filter(query: Query, start_date: Optional[str], end_date: Optional[str], use_start_time: bool = False) -> Query:
    """
    Apply date filtering to Workout queries.
    
    Args:
        use_start_time: If True, filter by workout start time instead of created_at
    """
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    if start_dt or end_dt:
        from whoop_data.models.models import Workout
        date_field = Workout.start if use_start_time else Workout.created_at
        
        if start_dt:
            query = query.filter(date_field >= start_dt)
        if end_dt:
            query = query.filter(date_field <= end_dt)
    
    return query


def apply_sleep_date_filter(query: Query, start_date: Optional[str], end_date: Optional[str]) -> Query:
    """
    Apply date filtering to Sleep queries using created_at field.
    """
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    if start_dt or end_dt:
        from whoop_data.models.models import Sleep
        
        if start_dt:
            query = query.filter(Sleep.created_at >= start_dt)
        if end_dt:
            query = query.filter(Sleep.created_at <= end_dt)
    
    return query


def apply_withings_date_filter(query: Query, start_date: Optional[str], end_date: Optional[str]) -> Query:
    """
    Apply date filtering to Withings queries using datetime field (measurement time).
    """
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    if start_dt or end_dt:
        # Import here to avoid circular imports
        from whoop_data.models.models import WithingsWeight, WithingsHeartRate
        
        # Determine which model we're filtering
        # This is a bit hacky but works for now
        model_class = None
        try:
            # Check if query is for WithingsWeight or WithingsHeartRate
            if hasattr(query.column_descriptions[0]['entity'], '__tablename__'):
                if query.column_descriptions[0]['entity'].__tablename__ == 'withings_weight':
                    date_field = WithingsWeight.datetime
                elif query.column_descriptions[0]['entity'].__tablename__ == 'withings_heart_rate':
                    date_field = WithingsHeartRate.datetime
                else:
                    # Fallback - assume it has datetime field
                    date_field = getattr(query.column_descriptions[0]['entity'], 'datetime')
        except:
            # If we can't determine, just return original query
            return query
        
        if start_dt:
            query = query.filter(date_field >= start_dt)
        if end_dt:
            query = query.filter(date_field <= end_dt)
    
    return query


# Utility function for API endpoints
def standardize_date_params(start_date: Optional[str], end_date: Optional[str]) -> dict:
    """
    Standardize date parameters and provide helpful validation.
    
    Returns:
        Dict with parsed dates and validation info
    """
    start_dt, end_dt = get_date_range(start_date, end_date)
    
    result = {
        'start_datetime': start_dt,
        'end_datetime': end_dt,
        'valid_range': True,
        'error_message': None
    }
    
    # Validate date range
    if start_dt and end_dt and start_dt > end_dt:
        result['valid_range'] = False
        result['error_message'] = "Start date must be before end date"
    
    return result