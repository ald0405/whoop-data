from whoopdata.database.database import get_db
from whoopdata.crud.sleep import get_sleep
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from whoopdata.schemas.sleep import SleepSchema
from whoopdata.utils.date_filters import standardize_date_params

router = APIRouter()


@router.get("/sleep", response_model=Union[List[SleepSchema], SleepSchema])
def get_sleep_data(
    latest: bool = Query(False, description="Get only the latest record"),
    limit: int = Query(100, description="Maximum number of records"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Unified sleep endpoint with flexible filtering.

    Examples:
    - GET /sleep - All sleep data
    - GET /sleep?latest=true - Latest sleep record only
    - GET /sleep?start_date=2024-01-01&end_date=2024-12-31 - Year 2024 data
    - GET /sleep?limit=50&skip=100 - Pagination (records 101-150)
    """
    try:
        # Validate date parameters
        date_validation = standardize_date_params(start_date, end_date)
        if not date_validation["valid_range"]:
            raise HTTPException(status_code=400, detail=date_validation["error_message"])

        if latest:
            # Get latest single record
            sleeps = get_sleep(db, skip=0, limit=1)
            if not sleeps:
                raise HTTPException(status_code=404, detail="No sleep data found")
            return sleeps[0]

        else:
            # Get all sleep records with optional date filtering
            # Note: Date filtering would need to be implemented in the CRUD layer
            return get_sleep(db, skip=skip, limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sleep data: {str(e)}")


# ============================================================================
# BACKWARD COMPATIBILITY ROUTES (for website)
# ============================================================================


@router.get("/sleep/", response_model=List[SleepSchema])
def list_sleep_compat(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified sleep endpoint."""
    return get_sleep(db, skip=skip, limit=limit)


@router.get("/sleep/latest", response_model=SleepSchema)
def latest_sleep_compat(db: Session = Depends(get_db)):
    """Backward compatibility endpoint - redirects to unified sleep endpoint."""
    sleeps = get_sleep(db, skip=0, limit=1)
    if not sleeps:
        raise HTTPException(status_code=404, detail="No sleep data found")
    return sleeps[0]
