"""Daily dashboard API routes aggregating health metrics and contextual data."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List, Optional
from statistics import mean

from whoopdata.database.database import get_db
from whoopdata.crud.recovery import get_recoveries
from whoopdata.crud.sleep import get_sleep
from whoopdata.crud.workout import get_recoveries as get_workouts  # Historical naming
from whoopdata.services.weather_service import WeatherAPI
from whoopdata.services.transport_service import TravelAPI
from whoopdata.services.health_metrics_service import get_all_health_metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize services
try:
    weather_service = WeatherAPI()
except ValueError:
    weather_service = None

transport_service = TravelAPI()

# Default location for weather (Canary Wharf / South Quay area)
DEFAULT_LOCATION = "Canary Wharf"


@router.get("/", include_in_schema=False)
async def dashboard_home(request: Request):
    """Serve the interactive dashboard HTML page.

    Displays:
    - Health metrics charts (Recovery, HRV, RHR, Strain, Sleep Efficiency, REM %)
    - Current weather with sunrise/sunset
    - TfL transport status

    All data is fetched dynamically via JavaScript from the API endpoints.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


def calculate_avg(values: List[float]) -> Optional[float]:
    """Calculate average, returning None if list is empty."""
    return round(mean(values), 2) if values else None


@router.get("/daily")
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
    dashboard_data = {
        "health_metrics": {},
        "context": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # ========== HEALTH METRICS ==========

    # Recovery data (last 7 days)
    try:
        recoveries = get_recoveries(db, skip=0, limit=7)
        if recoveries:
            recovery_scores = [r.recovery_score for r in recoveries if r.recovery_score is not None]
            dashboard_data["health_metrics"]["recovery"] = {
                "last_7_days": recovery_scores,
                "avg_7_days": calculate_avg(recovery_scores),
                "latest": recovery_scores[0] if recovery_scores else None,
            }
        else:
            dashboard_data["health_metrics"]["recovery"] = {
                "last_7_days": [],
                "avg_7_days": None,
                "latest": None,
            }
    except Exception as e:
        dashboard_data["health_metrics"]["recovery"] = {"error": str(e)}

    # Sleep data (last 7 days)
    try:
        sleeps = get_sleep(db, skip=0, limit=7)
        if sleeps:
            hours_slept = [
                round((s.total_time_in_bed_time_milli - s.total_awake_time_milli) / 3600000, 2)
                for s in sleeps
                if s.total_time_in_bed_time_milli is not None
                and s.total_awake_time_milli is not None
            ]

            time_in_bed = [
                round(s.total_time_in_bed_time_milli / 3600000, 2)
                for s in sleeps
                if s.total_time_in_bed_time_milli is not None
            ]

            # Get latest bedtime
            latest_bedtime = None
            if sleeps[0].start:
                latest_bedtime = sleeps[0].start.strftime("%H:%M")

            dashboard_data["health_metrics"]["sleep"] = {
                "hours_slept_last_7_days": hours_slept,
                "avg_hours_7_days": calculate_avg(hours_slept),
                "latest_bedtime": latest_bedtime,
                "time_in_bed_last_7_days": time_in_bed,
                "avg_time_in_bed_7_days": calculate_avg(time_in_bed),
            }
        else:
            dashboard_data["health_metrics"]["sleep"] = {
                "hours_slept_last_7_days": [],
                "avg_hours_7_days": None,
                "latest_bedtime": None,
                "time_in_bed_last_7_days": [],
                "avg_time_in_bed_7_days": None,
            }
    except Exception as e:
        dashboard_data["health_metrics"]["sleep"] = {"error": str(e)}

    # Workout/Strain data (last 7 days)
    try:
        workouts = get_workouts(db, skip=0, limit=7)
        if workouts:
            strain_scores = [w.strain for w in workouts if w.strain is not None]
            dashboard_data["health_metrics"]["strain"] = {
                "last_7_days": strain_scores,
                "avg_7_days": calculate_avg(strain_scores),
            }
        else:
            dashboard_data["health_metrics"]["strain"] = {"last_7_days": [], "avg_7_days": None}
    except Exception as e:
        dashboard_data["health_metrics"]["strain"] = {"error": str(e)}

    # Weight data (latest and 7-day change)
    try:
        # Query Withings weight data directly from models
        from whoopdata.models.models import WithingsWeight

        weights = db.query(WithingsWeight).order_by(WithingsWeight.datetime.desc()).limit(8).all()
        if weights:
            latest_weight = weights[0].weight_kg

            # Calculate 7-day change if we have enough data
            weight_change = None
            if len(weights) >= 8:
                week_ago_weight = weights[7].weight_kg
                weight_change = round(latest_weight - week_ago_weight, 1)

            dashboard_data["health_metrics"]["weight"] = {
                "latest": round(latest_weight, 1) if latest_weight else None,
                "change_7_days": weight_change,
            }
        else:
            dashboard_data["health_metrics"]["weight"] = {"latest": None, "change_7_days": None}
    except Exception as e:
        dashboard_data["health_metrics"]["weight"] = {"error": str(e)}

    # ========== CONTEXTUAL DATA ==========

    # Weather data
    if weather_service:
        try:
            # Get coordinates for location
            coords = weather_service.get_coordinates(location)

            # Current weather
            current_weather = weather_service.get_current_weather(coords["lat"], coords["lon"])

            # Get forecast for today
            forecast = weather_service.get_forecast(coords["lat"], coords["lon"])
            today_forecast = forecast["forecast"][:8]  # First 8 intervals (24 hours)

            # Extract high/low temps from today's forecast
            temps = [f["temperature"] for f in today_forecast]
            high_temp = round(max(temps)) if temps else None
            low_temp = round(min(temps)) if temps else None

            # Air quality
            air_quality = weather_service.get_air_quality(coords["lat"], coords["lon"])

            dashboard_data["context"]["weather"] = {
                "current": {
                    "temp": round(current_weather["temperature"]),
                    "conditions": current_weather["conditions"],
                    "feels_like": round(current_weather["feels_like"]),
                },
                "forecast_today": (
                    f"High {high_temp}°C, Low {low_temp}°C" if high_temp and low_temp else "N/A"
                ),
                "air_quality": {
                    "aqi": air_quality["aqi"],
                    "description": air_quality["aqi_description"],
                },
            }
        except Exception as e:
            dashboard_data["context"]["weather"] = {"error": str(e)}
    else:
        dashboard_data["context"]["weather"] = {"error": "Weather service not configured"}

    # Transport status
    try:
        transport_status = transport_service.get_line_status()
        dashboard_data["context"]["transport"] = transport_status
    except Exception as e:
        dashboard_data["context"]["transport"] = {"error": str(e)}

    return dashboard_data


@router.get("/health-metrics")
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
        return get_all_health_metrics(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving health metrics: {str(e)}")


@router.get("/weather-extended")
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
    if not weather_service:
        raise HTTPException(
            status_code=503, detail="Weather service not configured - check OPENWEATHER_API_KEY"
        )

    try:
        # Get coordinates
        coords = weather_service.get_coordinates(location)

        # Current weather (includes sunrise/sunset)
        current = weather_service.get_current_weather(coords["lat"], coords["lon"])

        # Current AQI
        air_quality = weather_service.get_air_quality(coords["lat"], coords["lon"])

        # Daily forecast summary (5 days)
        daily_forecast = weather_service.get_daily_forecast_summary(
            coords["lat"], coords["lon"], days=5
        )

        # Time-of-day forecast (morning/afternoon/evening)
        time_of_day_forecast = weather_service.get_forecast_by_time_of_day(
            coords["lat"], coords["lon"], days=5
        )

        # AQI forecast
        aqi_forecast = weather_service.get_air_pollution_forecast(coords["lat"], coords["lon"])

        # Summarize AQI forecast by day (take first reading per day)
        aqi_daily = {}
        for item in aqi_forecast["forecast"]:
            date = datetime.fromisoformat(item["timestamp"]).date().isoformat()
            if date not in aqi_daily:
                aqi_daily[date] = {
                    "date": date,
                    "aqi": item["aqi"],
                    "aqi_description": item["aqi_description"],
                    "pm2_5": round(item["pm2_5"], 2),
                    "pm10": round(item["pm10"], 2),
                }

        return {
            "location": {"name": coords["name"], "country": coords["country"]},
            "current": {
                "temperature": round(current["temperature"], 2),
                "feels_like": round(current["feels_like"], 2),
                "conditions": current["conditions"],
                "wind_speed": round(current["wind_speed"], 2),
                "humidity": current["humidity"],
                "sunrise": current["sunrise"],
                "sunset": current["sunset"],
            },
            "air_quality": {
                "current": {
                    "aqi": air_quality["aqi"],
                    "description": air_quality["aqi_description"],
                    "pm2_5": round(air_quality["components"]["pm2_5"], 2),
                    "pm10": round(air_quality["components"]["pm10"], 2),
                },
                "forecast": list(aqi_daily.values())[:5],
            },
            "forecast": daily_forecast["daily_forecast"],
            "forecast_by_time": time_of_day_forecast["forecast_by_time"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving extended weather data: {str(e)}"
        )
