from sqlalchemy.orm import Session
from whoopdata.models.models import Sleep


def get_sleep(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Sleep).order_by(Sleep.created_at.desc()).offset(skip).limit(limit).all()
