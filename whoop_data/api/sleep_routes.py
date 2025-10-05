from db.database import get_db
from whoop_data.crud.sleep import get_sleep
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from whoop_data.schemas.sleep import SleepSchema

router = APIRouter()

@router.get("/sleep", response_model=List[SleepSchema])
def list_sleep(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_sleep(db, skip=skip, limit=limit)

@router.get("/sleep/",
            name="Get all sleeps",
            description="An endpoint for getting all sleep data",
            response_model=List[SleepSchema]
            )
def list_sleep_alt(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_sleep(db, skip=skip, limit=limit)

@router.get("/sleep/latest", response_model=SleepSchema)
def latest_sleep(db: Session = Depends(get_db)):
    sleeps = get_sleep(db, skip=0, limit=1)
    if not sleeps:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No sleep data found")
    return sleeps[0]
