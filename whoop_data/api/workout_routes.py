from fastapi import APIRouter, Depends, Query, HTTPException
from whoop_data.schemas.workout import Workouts as WorkoutSchema
from db.database import get_db
from sqlalchemy.orm import Session
from whoop_data.crud.workout import get_recoveries, get_runs, get_tennis
from whoop_data.utils.date_filters import standardize_date_params
from typing import List, Optional, Union

router = APIRouter()


def calculate_trimp_from_run(run) -> float:
    """Calculate TRIMP (Training Impulse) score from heart rate zones."""
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


@router.get("/workouts", response_model=Union[List[WorkoutSchema], WorkoutSchema])
def get_workout_data(
    latest: bool = Query(False, description="Get only the latest record"),
    limit: int = Query(100, description="Maximum number of records"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Unified workout endpoint with flexible filtering.
    
    Examples:
    - GET /workouts - All workout data
    - GET /workouts?latest=true - Latest workout only
    - GET /workouts?start_date=2024-01-01&end_date=2024-12-31 - Year 2024 data
    - GET /workouts?limit=50&skip=100 - Pagination (records 101-150)
    """
    try:
        # Validate date parameters
        date_validation = standardize_date_params(start_date, end_date)
        if not date_validation['valid_range']:
            raise HTTPException(status_code=400, detail=date_validation['error_message'])
        
        if latest:
            # Get latest single record
            workouts = get_recoveries(db, skip=0, limit=1)  # Note: get_recoveries is used for workouts
            if not workouts:
                raise HTTPException(status_code=404, detail="No workout data found")
            return workouts[0]
        
        else:
            # Get all workouts with optional date filtering
            start_dt, end_dt = None, None
            if date_validation['start_datetime']:
                start_dt = date_validation['start_datetime']
            if date_validation['end_datetime']:  
                end_dt = date_validation['end_datetime']
            
            return get_recoveries(db, skip=skip, limit=limit, start_date=start_dt, end_date=end_dt)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving workout data: {str(e)}")


@router.get("/workouts/types/running", response_model=List[WorkoutSchema])
def get_running_workouts(
    limit: int = Query(100, description="Maximum number of records (can be set higher for comprehensive analysis)"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get running workouts (sport_id=0).
    
    Examples:
    - GET /workouts/types/running - Recent running workouts
    - GET /workouts/types/running?limit=200 - Get more comprehensive data
    """
    try:
        date_validation = standardize_date_params(start_date, end_date)
        if not date_validation['valid_range']:
            raise HTTPException(status_code=400, detail=date_validation['error_message'])
        
        # Apply date filtering 
        start_dt, end_dt = None, None
        if date_validation['start_datetime']:
            start_dt = date_validation['start_datetime']
        if date_validation['end_datetime']:
            end_dt = date_validation['end_datetime']
        
        return get_runs(db, skip=skip, limit=limit, start_date=start_dt, end_date=end_dt)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving running workouts: {str(e)}")


@router.get("/workouts/types/tennis", response_model=List[WorkoutSchema])
def get_tennis_workouts(
    limit: int = Query(100, description="Maximum number of records (can be set higher for comprehensive analysis)"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get tennis workouts (sport_id=34).
    
    Examples:
    - GET /workouts/types/tennis - Recent tennis workouts
    - GET /workouts/types/tennis?limit=100 - Get comprehensive tennis history
    """
    try:
        date_validation = standardize_date_params(start_date, end_date)
        if not date_validation['valid_range']:
            raise HTTPException(status_code=400, detail=date_validation['error_message'])
        
        # Apply date filtering
        start_dt, end_dt = None, None
        if date_validation['start_datetime']:
            start_dt = date_validation['start_datetime']
        if date_validation['end_datetime']:
            end_dt = date_validation['end_datetime']
        
        return get_tennis(db, skip=skip, limit=limit, start_date=start_dt, end_date=end_dt)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tennis workouts: {str(e)}")


@router.get("/workouts/analytics/trimp", response_model=List[WorkoutSchema])
def get_running_workouts_with_trimp(
    limit: int = Query(100, description="Maximum number of records"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get running workouts with calculated TRIMP (Training Impulse) scores.
    
    Examples:
    - GET /workouts/analytics/trimp - Running workouts with TRIMP calculations
    - GET /workouts/analytics/trimp?limit=200 - Get comprehensive TRIMP analysis
    """
    try:
        # Note: TRIMP endpoint doesn't currently support date filtering, 
        # but uses the basic get_runs function which now has proper ordering
        runs_list = get_runs(db, skip=skip, limit=limit)
        
        # Add TRIMP score to each run
        for run in runs_list:
            run.trimp_score = calculate_trimp_from_run(run)
        
        return runs_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating TRIMP scores: {str(e)}")


# ============================================================================
# BACKWARD COMPATIBILITY ROUTES (for website)
# ============================================================================

@router.get("/workouts/", response_model=List[WorkoutSchema])
def list_workouts_compat(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified workout endpoint."""
    return get_recoveries(db, skip=skip, limit=limit)  # Note: get_recoveries is used for workouts


@router.get("/workouts/latest", response_model=WorkoutSchema)
def latest_workout_compat(db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified workout endpoint."""
    workouts = get_recoveries(db, skip=0, limit=1)
    if not workouts:
        raise HTTPException(status_code=404, detail="No workout data found")
    return workouts[0]


@router.get("/workouts/get_runs", response_model=List[WorkoutSchema])
def list_runs_compat(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to type-specific endpoint."""
    return get_runs(db, skip=skip, limit=limit)


@router.get("/workouts/get_run_trimp", response_model=List[WorkoutSchema])
def list_trimp_scores_compat(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to analytics endpoint."""
    runs_list = get_runs(db, skip=skip, limit=limit)
    
    # Add TRIMP score to each run
    for run in runs_list:
        run.trimp_score = calculate_trimp_from_run(run)
    
    return runs_list


@router.get("/workouts/get_tennis", response_model=List[WorkoutSchema])
def list_tennis_compat(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to type-specific endpoint."""
    return get_tennis(db, skip=skip, limit=limit)
