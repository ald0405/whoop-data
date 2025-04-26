from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models.models import Sleep


def get_sleep(db: Session, skip: int = 0, limit: int = 10):
    return (
        db.query(Sleep)
        .order_by(Sleep.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
