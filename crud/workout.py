from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models.models import Workout

def get_recoveries(db: Session, skip: int = 0, limit: int = 10  ):
    return (
        db.query(Workout)
        .offset(skip)
        .limit(limit)
        .all()
        )

def get_runs(db: Session, skip: int = 0, limit: int = 10):
    """
    Get workouts where sport_id = 0 (i.e., runs).
    """
    return (
        db.query(Workout)
        .filter(Workout.sport_id == 0)
        .order_by(Workout.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tennis(db:Session, skip:int=0,limit:int=10):
    """
    Get workouts where sport_id = 34 (Tennis)
    """
    return (
        db.query(Workout)
        .filter(Workout.sport_id == 34)
        .order_by(Workout.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )