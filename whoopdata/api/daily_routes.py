"""Daily decision engine API routes.

Provides endpoints for:
- Daily action card (GET /api/daily-plan)
- Scenario prediction (POST /api/scenarios/recovery)
- Scenario comparison (POST /api/scenarios/compare)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from whoopdata.database.database import get_db
from whoopdata.services.daily_engine import DailyEngine
from whoopdata.services.scenario_planner import ScenarioPlanner
from whoopdata.analytics.engine import InsightGenerator
from whoopdata.schemas.daily import (
    DailyPlanResponse,
    ScenarioRequest,
    ScenarioResponse,
    CompareRequest,
    CompareResponse,
)

# External services (same pattern as dashboard_routes.py)
from whoopdata.services.weather_service import WeatherAPI
from whoopdata.services.transport_service import TravelAPI
from whoopdata.services.tide_service import TideService

router = APIRouter(prefix="/api", tags=["daily"])

# Initialize external services
try:
    _weather_service = WeatherAPI()
except (ValueError, Exception):
    _weather_service = None

_transport_service = TravelAPI()
_tide_service = TideService()

DEFAULT_LOCATION = "Canary Wharf"


async def _fetch_weather() -> dict | None:
    """Fetch current weather data for the daily plan."""
    if not _weather_service:
        return None
    try:
        coords = _weather_service.get_coordinates(DEFAULT_LOCATION)
        current = _weather_service.get_current_weather(coords["lat"], coords["lon"])
        forecast = _weather_service.get_forecast(coords["lat"], coords["lon"])
        air_quality = _weather_service.get_air_quality(coords["lat"], coords["lon"])

        # Extract today's high/low from forecast
        today_forecast = forecast.get("forecast", [])[:8]
        temps = [f["temperature"] for f in today_forecast if "temperature" in f]
        forecast_str = (
            f"High {max(temps):.0f}°C, Low {min(temps):.0f}°C" if temps else None
        )

        return {
            "current": {
                "temp": round(current["temperature"]),
                "conditions": current["conditions"],
                "feels_like": round(current["feels_like"]),
                "sunrise": current.get("sunrise"),
                "sunset": current.get("sunset"),
            },
            "forecast_today": forecast_str,
            "air_quality": {
                "aqi": air_quality["aqi"],
                "description": air_quality["aqi_description"],
            },
        }
    except Exception:
        return None


async def _fetch_transport() -> dict | list | None:
    """Fetch transport status."""
    try:
        return _transport_service.get_line_status()
    except Exception:
        return None


async def _fetch_tide() -> dict | None:
    """Fetch tide data."""
    try:
        current = await _tide_service.get_latest_reading("0001")
        if current:
            return {
                "current_level": round(current.value, 2),
                "station": "Silvertown",
                "timestamp": current.timestamp.isoformat(),
            }
    except Exception:
        pass
    return None


# =================== Endpoints ===================


@router.get("/daily-plan", response_model=DailyPlanResponse)
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
        # Fetch external context in parallel-ish (sync weather/transport, async tide)
        weather_data = await _fetch_weather()
        transport_data = await _fetch_transport()
        tide_data = await _fetch_tide()

        engine = DailyEngine(db)
        plan = engine.generate_daily_plan(
            weather_data=weather_data,
            transport_data=transport_data,
            tide_data=tide_data,
        )
        return plan

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating daily plan: {str(e)}"
        )


@router.post("/scenarios/recovery", response_model=ScenarioResponse)
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
        planner = ScenarioPlanner(db)
        return planner.predict_scenario(request.scenario)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error predicting scenario: {str(e)}"
        )


@router.post("/scenarios/compare", response_model=CompareResponse)
async def compare_scenarios(request: CompareRequest, db: Session = Depends(get_db)):
    """Compare 2-5 scenarios side-by-side.

    Provide multiple sets of inputs (sleep hours, strain, etc.) and get:
    - Predicted recovery for each scenario
    - Best option highlighted
    - All results compared to your 28-day baseline

    Example: "8h sleep + tennis" vs "7h sleep + rest day"
    """
    try:
        planner = ScenarioPlanner(db)
        return planner.compare_scenarios(request.scenarios)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error comparing scenarios: {str(e)}"
        )


@router.get("/reports/weekly")
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
        generator = InsightGenerator(db)
        report = generator.generate_coaching_report(weeks=weeks)
        return report

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating coaching report: {str(e)}"
        )
