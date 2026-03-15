"""Daily dashboard API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from whoopdata.database.database import get_db
from whoopdata.services.dashboard_service import DashboardService
from whoopdata.services.insight_context_service import DEFAULT_LOCATION

insights_router = APIRouter(prefix="/api/v1/insights/dashboard", tags=["insights"])
legacy_insights_router = APIRouter(prefix="/dashboard", tags=["insights"])

@legacy_insights_router.get("/daily", deprecated=True)
@insights_router.get("/daily")
async def get_daily_dashboard(
    location: str = DEFAULT_LOCATION, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive daily dashboard with health metrics and contextual data.

    Aggregates:
    - Recovery scores (last 7 days + average)
    - Sleep metrics (hours slept, bedtime, time in bed - last 7 days + averages)
    - Strain scores (last 7 days + average)
    - Weight (latest + 7-day change)
    - Weather (current + forecast + air quality)
    - Transport status (TfL lines: Jubilee, DLR, Elizabeth, Northern)

    Args:
        location: Location for weather data (default: Canary Wharf)
        db: Database session

    Returns:
        Comprehensive dashboard data
    """
    try:
        return await DashboardService(db).build_daily_dashboard(location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving daily dashboard: {str(e)}")


@legacy_insights_router.get("/health-metrics", deprecated=True)
@insights_router.get("/health-metrics")
async def get_health_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get comprehensive health metrics with standardized 7-day and 28-day aggregations.

    Returns all key health metrics:
    - Recovery score (%, last 7 days, 7-day avg, 28-day avg)
    - Resting heart rate (bpm, last 7 days, 7-day avg, 28-day avg)
    - HRV (ms, last 7 days, 7-day avg, 28-day avg)
    - Sleep hours (hours, last 7 days, 7-day avg, 28-day avg)
    - REM sleep hours (hours, last 7 days, 7-day avg, 28-day avg)
    - REM sleep percentage (%, last 7 days, 7-day avg, 28-day avg)
    - Sleep efficiency (%, last 7 days, 7-day avg, 28-day avg)
    - Bedtime (HH:MM, last 7 days)
    - Wake time (HH:MM, last 7 days)
    - Strain (last 7 days, 7-day avg, 28-day avg)

    All numeric values rounded to 2 decimal places.

    Returns:
        Dict with all health metrics in standardized format
    """
    try:
        return DashboardService(db).get_health_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving health metrics: {str(e)}")


@legacy_insights_router.get("/weather-extended", deprecated=True)
@insights_router.get("/weather-extended")
async def get_weather_extended(location: str = DEFAULT_LOCATION) -> Dict[str, Any]:
    """Get extended weather data including sunrise/sunset and multi-day forecasts.

    Returns:
    - Current weather (temp, conditions, feels_like, wind_speed, AQI)
    - Sunrise and sunset times
    - 5-7 day forecast with daily summaries (temp high/low/avg, wind, conditions)
    - AQI forecast for upcoming days

    Args:
        location: Location for weather data (default: Canary Wharf)

    Returns:
        Extended weather data with forecasts
    """

    try:
        return DashboardService(db=None).get_extended_weather(location)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving extended weather data: {str(e)}"
        )
