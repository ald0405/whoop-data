from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from whoop_data.models.models import Workout
from typing import Optional


def get_recoveries(db: Session, skip: int = 0, limit: int = 10, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Get all workouts with proper ordering and optional date filtering.
    
    Note: This function is named 'get_recoveries' for historical reasons but actually returns workouts.
    """
    query = db.query(Workout)
    
    # Add date filtering if provided
    if start_date:
        query = query.filter(Workout.created_at >= start_date)
    if end_date:
        query = query.filter(Workout.created_at <= end_date)
    
    # Always order by created_at descending (most recent first)
    return query.order_by(Workout.created_at.desc()).offset(skip).limit(limit).all()


def get_runs(db: Session, skip: int = 0, limit: int = 10, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Get workouts where sport_id = 0 (i.e., runs) with optional date filtering.
    """
    query = db.query(Workout).filter(Workout.sport_id == 0)
    
    # Add date filtering if provided
    if start_date:
        query = query.filter(Workout.created_at >= start_date)
    if end_date:
        query = query.filter(Workout.created_at <= end_date)
    
    return query.order_by(Workout.created_at.desc()).offset(skip).limit(limit).all()


def get_tennis(db: Session, skip: int = 0, limit: int = 10, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Get workouts where sport_id = 34 (Tennis) with optional date filtering.
    """
    query = db.query(Workout).filter(Workout.sport_id == 34)
    
    # Add date filtering if provided
    if start_date:
        query = query.filter(Workout.created_at >= start_date)
    if end_date:
        query = query.filter(Workout.created_at <= end_date)
    
    return query.order_by(Workout.created_at.desc()).offset(skip).limit(limit).all()
