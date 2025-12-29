from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from whoopdata.schemas.recovery import Recovery as RecoverySchema, AvgRecovery
from whoopdata.crud.recovery import get_recoveries, get_top_recoveries, get_avg_recovery_by_week
from whoopdata.utils.date_filters import standardize_date_params, apply_recovery_date_filter
from whoopdata.database.database import get_db

router = APIRouter()


@router.get("/recovery", response_model=Union[List[RecoverySchema], RecoverySchema])
def get_recovery_data(
    latest: bool = Query(False, description="Get only the latest record"),
    top: bool = Query(False, description="Get top recoveries by score"),
    limit: int = Query(100, description="Maximum number of records"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Unified recovery endpoint with flexible filtering.

    Examples:
    - GET /recovery - All recovery data
    - GET /recovery?latest=true - Latest recovery only
    - GET /recovery?top=true&limit=10 - Top 10 recoveries by score
    - GET /recovery?start_date=2024-01-01&end_date=2024-12-31 - Year 2024 data
    - GET /recovery?limit=50&skip=100 - Pagination (records 101-150)
    """
    try:
        # Validate date parameters
        date_validation = standardize_date_params(start_date, end_date)
        if not date_validation["valid_range"]:
            raise HTTPException(status_code=400, detail=date_validation["error_message"])

        if latest:
            # Get latest single record
            recoveries = get_recoveries(db, skip=0, limit=1)
            if not recoveries:
                raise HTTPException(status_code=404, detail="No recovery data found")
            return recoveries[0]

        elif top:
            # Get top recoveries by score (date filtering not applicable for top)
            return get_top_recoveries(db, limit=limit)

        else:
            # Get all recoveries with optional date filtering
            # Note: Date filtering would need to be implemented in the CRUD layer
            # For now, returning standard pagination
            return get_recoveries(db, skip=skip, limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recovery data: {str(e)}")


@router.get("/recovery/analytics/weekly", response_model=List[AvgRecovery])
def get_recovery_weekly_analytics(
    weeks: int = Query(4, description="Number of weeks to analyze (can be 52+ for full year)"),
    db: Session = Depends(get_db),
):
    """
    Get weekly recovery analytics and trends.

    Examples:
    - GET /recovery/analytics/weekly - Last 4 weeks
    - GET /recovery/analytics/weekly?weeks=52 - Full year analysis

    Returns aggregated recovery scores and resting heart rate by week.
    """
    try:
        return get_avg_recovery_by_week(db, weeks=weeks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating weekly analytics: {str(e)}")


# ============================================================================
# BACKWARD COMPATIBILITY ROUTES (for website)
# ============================================================================


@router.get("/recoveries/", response_model=List[RecoverySchema])
def list_recoveries_compat(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified recovery endpoint."""
    return get_recoveries(db, skip=skip, limit=limit)


@router.get("/recovery/latest", response_model=RecoverySchema)
def latest_recovery_compat(db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified recovery endpoint."""
    recoveries = get_recoveries(db, skip=0, limit=1)
    if not recoveries:
        raise HTTPException(status_code=404, detail="No recovery data found")
    return recoveries[0]


@router.get("/recoveries/top", response_model=List[RecoverySchema])
def top_recoveries_compat(limit: int = 10, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified recovery endpoint."""
    return get_top_recoveries(db, limit=limit)


@router.get("/recoveries/avg_recoveries/", response_model=List[AvgRecovery])
def avg_recovery_compat(week: int = 4, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to analytics endpoint."""
    return get_avg_recovery_by_week(db, weeks=week)
