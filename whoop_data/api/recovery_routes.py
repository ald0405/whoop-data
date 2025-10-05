from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from whoop_data.schemas.recovery import Recovery as RecoverySchema, AvgRecovery
from whoop_data.crud.recovery import get_recoveries, get_top_recoveries, get_avg_recovery_by_week
from db.database import get_db

router = APIRouter()


@router.get("/recovery", response_model=List[RecoverySchema])
def list_recoveries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_recoveries(db, skip=skip, limit=limit)

@router.get("/recoveries/", response_model=List[RecoverySchema])
def list_recoveries_alt(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_recoveries(db, skip=skip, limit=limit)


@router.get("/recoveries/top", response_model=List[RecoverySchema])
def top_recoveries(limit: int = 10, db: Session = Depends(get_db)):
    return get_top_recoveries(db, limit=limit)


@router.get("/recovery/latest", response_model=RecoverySchema)
def latest_recovery(db: Session = Depends(get_db)):
    recoveries = get_recoveries(db, skip=0, limit=1)
    if not recoveries:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No recovery data found")
    return recoveries[0]

@router.get(
    "/recoveries/avg_recoveries/",
    response_model=List[AvgRecovery],
    name="Average Recoveries",
    summary="Get average recovery scores by week",
    description="Returns weekly average recovery scores and resting heart rate for the last X weeks.",
)
def avg_recovery(week: int = 4, db: Session = Depends(get_db)):
    return get_avg_recovery_by_week(db, weeks=week)
