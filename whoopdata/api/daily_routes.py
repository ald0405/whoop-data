"""Daily decision engine API routes.

Provides endpoints for:
- Daily action card (GET /api/daily-plan)
- Scenario prediction (POST /api/scenarios/recovery)
- Scenario comparison (POST /api/scenarios/compare)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from whoopdata.database.database import get_db
from whoopdata.schemas.daily import (
    DailyPlanResponse,
    ScenarioRequest,
    ScenarioResponse,
    CompareRequest,
    CompareResponse,
)
from whoopdata.services.guidance_service import GuidanceService

insights_router = APIRouter(prefix="/api/v1/insights", tags=["insights"])
legacy_insights_router = APIRouter(prefix="/api", tags=["insights"])


# =================== Endpoints ===================


@legacy_insights_router.get("/daily-plan", response_model=DailyPlanResponse, deprecated=True)
@insights_router.get("/daily-plan", response_model=DailyPlanResponse)
async def get_daily_plan(db: Session = Depends(get_db)):
    """Get your personalised daily action card.

    Returns:
    - Recovery status with key driver explanation
    - 3-5 prioritised actions (training, sleep, recovery, lifestyle)
    - Tonight's sleep target based on your best recovery patterns
    - Environmental context (weather, transport, air quality)

    Requires the analytics pipeline to have been run at least once
    for factor importance data. Recovery/sleep data must exist.
    """
    try:
        return await GuidanceService(db).build_daily_plan()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating daily plan: {str(e)}"
        )


@legacy_insights_router.post("/scenarios/recovery", response_model=ScenarioResponse, deprecated=True)
@insights_router.post("/scenarios/recovery", response_model=ScenarioResponse)
async def predict_scenario(request: ScenarioRequest, db: Session = Depends(get_db)):
    """Predict recovery for a hypothetical scenario.

    Provide planned sleep hours, expected strain, etc. and get:
    - Predicted recovery score with confidence interval
    - Recovery category (green/yellow/red)
    - Comparison to your 28-day baseline
    - Plain-English verdict

    Requires a trained recovery prediction model (run analytics pipeline first).
    """
    try:
        return GuidanceService(db).predict_scenario(request.scenario)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error predicting scenario: {str(e)}"
        )


@legacy_insights_router.post("/scenarios/compare", response_model=CompareResponse, deprecated=True)
@insights_router.post("/scenarios/compare", response_model=CompareResponse)
async def compare_scenarios(request: CompareRequest, db: Session = Depends(get_db)):
    """Compare 2-5 scenarios side-by-side.

    Provide multiple sets of inputs (sleep hours, strain, etc.) and get:
    - Predicted recovery for each scenario
    - Best option highlighted
    - All results compared to your 28-day baseline

    Example: "8h sleep + tennis" vs "7h sleep + rest day"
    """
    try:
        return GuidanceService(db).compare_scenarios(request.scenarios)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error comparing scenarios: {str(e)}"
        )


@legacy_insights_router.get("/reports/weekly", deprecated=True)
@insights_router.get("/reports/weekly")
async def get_weekly_coaching_report(
    weeks: int = 1,
    db: Session = Depends(get_db),
):
    """Get a structured coaching report for the past N weeks.

    Returns:
    - What happened: data-backed summary of the period
    - What worked: behaviours that correlated with best outcomes
    - What to change: 1-2 specific recommendations for next week
    - Progress: trend vs previous period
    """
    try:
        return GuidanceService(db).get_weekly_coaching_report(weeks=weeks)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating coaching report: {str(e)}"
        )
