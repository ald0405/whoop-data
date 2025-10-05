from fastapi import APIRouter, Depends
from whoop_data.schemas.workout import Workouts as WorkoutSchema
from db.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from whoop_data.crud.workout import get_recoveries, get_runs, get_tennis
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


def calculate_trimp_from_run(run) -> float:
    weights = {0: 0.5, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0}
    time_in_zones = {
        0: run.zone_zero_minutes,
        1: run.zone_one_minutes,
        2: run.zone_two_minutes,
        3: run.zone_three_minutes,
        4: run.zone_four_minutes,
        5: run.zone_five_minutes,
    }
    trimp = round(sum(minutes * weights[zone] for zone, minutes in time_in_zones.items() if minutes is not None), 2)
    return trimp

@router.get("/workouts/get_run_trimp", response_model=List[WorkoutSchema])
def list_trimp_scores(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    runs_list = get_runs(db, skip=skip, limit=limit)
    
    # Add TRIMP to each run
    for run in runs_list:
        run.trimp_score = calculate_trimp_from_run(run)
    
    return runs_list



@router.get(
    "/workouts/get_tennis",
    response_model=List[WorkoutSchema],
    name="Get All Tennis",
    description="Access All Tennis Workouts",
    summary="An easy way to analyse Tennis data",
)
def list_tennis(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_tennis(db, skip=skip, limit=limit)
