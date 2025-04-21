from fastapi import APIRouter, Depends
from schemas.workout import Workouts as WorkoutSchema
from db.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from crud.workout import get_recoveries, get_runs, get_tennis
from typing import List

router = APIRouter()


@router.get("/workouts/", response_model=List[WorkoutSchema])
def list_workouts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_recoveries(db, skip=skip, limit=limit)


@router.get(
    "/workouts/get_runs",
    response_model=List[WorkoutSchema],
    name="Get All Runs",
    description="Access All Run Workouts",
    summary="An easy way to analyse running data",
)
def list_runs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_runs(db, skip=skip, limit=limit)


@router.get(
    "/workouts/get_tennis",
    response_model=List[WorkoutSchema],
    name="Get All Tennis",
    description="Access All Tennis Workouts",
    summary="An easy way to analyse Tennis data",
)
def list_tennis(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_tennis(db, skip=skip, limit=limit)
