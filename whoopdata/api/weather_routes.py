"""Weather and air quality API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from whoopdata.services.weather_service import WeatherAPI

router = APIRouter(prefix="/weather", tags=["weather"])

# Initialize weather service
try:
    weather_service = WeatherAPI()
except ValueError as e:
    weather_service = None
    print(f"Warning: Weather service not initialized - {str(e)}")


@router.get("/current")
async def get_current_weather(
    location: str = Query(..., description="Location name (e.g., 'Canary Wharf', 'London')")
):
    """Get current weather conditions for a location.

    Args:
        location: City or area name

    Returns:
        Current weather with temperature, conditions, humidity, wind speed
    """
    if not weather_service:
        raise HTTPException(
            status_code=503,
            detail="Weather service not available - check OPENWEATHER_API_KEY configuration",
        )

    try:
        # Geocode location to coordinates
        coords = weather_service.get_coordinates(location)

        # Get current weather
        weather = weather_service.get_current_weather(coords["lat"], coords["lon"])

        return {
            "location": {
                "name": coords["name"],
                "country": coords["country"],
                "lat": coords["lat"],
                "lon": coords["lon"],
            },
            "weather": weather,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather: {str(e)}")


@router.get("/forecast")
async def get_weather_forecast(
    location: str = Query(..., description="Location name (e.g., 'Canary Wharf', 'London')"),
    days: Optional[int] = Query(3, description="Number of days to forecast (max 5)", ge=1, le=5),
):
    """Get weather forecast for a location.

    Args:
        location: City or area name
        days: Number of days to forecast (1-5)

    Returns:
        5-day forecast with 3-hour intervals (filtered to requested days)
    """
    if not weather_service:
        raise HTTPException(
            status_code=503,
            detail="Weather service not available - check OPENWEATHER_API_KEY configuration",
        )

    try:
        # Geocode location to coordinates
        coords = weather_service.get_coordinates(location)

        # Get forecast
        forecast_data = weather_service.get_forecast(coords["lat"], coords["lon"])

        # Filter to requested number of days (8 intervals per day at 3-hour spacing)
        max_intervals = days * 8
        filtered_forecast = forecast_data["forecast"][:max_intervals]

        return {
            "location": {
                "name": coords["name"],
                "country": coords["country"],
                "lat": coords["lat"],
                "lon": coords["lon"],
            },
            "forecast": filtered_forecast,
            "days_requested": days,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forecast: {str(e)}")


@router.get("/air-quality")
async def get_air_quality(
    location: str = Query(..., description="Location name (e.g., 'Canary Wharf', 'London')")
):
    """Get current air quality for a location.

    Args:
        location: City or area name

    Returns:
        Air quality index (AQI) and pollutant levels (PM2.5, PM10, CO, NO2, O3)
        AQI scale: 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
    """
    if not weather_service:
        raise HTTPException(
            status_code=503,
            detail="Weather service not available - check OPENWEATHER_API_KEY configuration",
        )

    try:
        # Geocode location to coordinates
        coords = weather_service.get_coordinates(location)

        # Get air quality
        air_quality = weather_service.get_air_quality(coords["lat"], coords["lon"])

        return {
            "location": {
                "name": coords["name"],
                "country": coords["country"],
                "lat": coords["lat"],
                "lon": coords["lon"],
            },
            "air_quality": air_quality,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch air quality: {str(e)}")
