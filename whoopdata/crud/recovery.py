from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from whoopdata.models.models import Recovery


def get_recoveries(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Recovery).offset(skip).limit(limit).all()


def get_top_recoveries(db: Session, limit: int = 10):
    """
    Get the Top N Recoveries
    """
    return (
        db.query(Recovery).order_by(Recovery.recovery_score.desc()).limit(limit).all()
    )


def get_recent_recovories(db: Session, limit: int = 7):
    """
    Get Recoveries for the last 7 days
    """
    return db.query(Recovery).limit(limit).all()


def get_avg_recovery_by_week(db: Session, weeks: int = 4):
    """
    Compute average recovery score grouped by ISO week number for the last `weeks` weeks.
    """
    since_date = datetime.now() - timedelta(weeks=weeks)

    return (
        db.query(
            func.strftime("%Y-%W", Recovery.created_at).label("week"),  # ISO week
            func.avg(Recovery.recovery_score).label("avg_recovery_score"),
            func.avg(Recovery.resting_heart_rate).label("avg_resting_heart_rate"),
        )
        .filter(Recovery.created_at >= since_date)
        .group_by("week")
        .order_by("week")
        .all()
    )
