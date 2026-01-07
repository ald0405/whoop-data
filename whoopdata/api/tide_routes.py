"""Thames tide API routes."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from whoopdata.models.tide import TideForecast, TideReading, TideStation
from whoopdata.services.tide_service import TideService

router = APIRouter(prefix="/tides", tags=["tides"])

# Initialize service
tide_service = TideService()


@router.get("/stations")
async def list_stations() -> dict:
    """List available tidal monitoring stations in East London.
    
    Returns:
        Dictionary of station names and IDs
    """
    return {
        "stations": [
            {
                "name": "Silvertown",
                "id": "0001",
                "description": "Primary East London tide gauge near Royal Docks",
            },
            {
                "name": "Charlton",
                "id": "0003",
                "description": "Thames Barrier area monitoring station",
            },
            {
                "name": "Tower Pier",
                "id": "0007",
                "description": "Central London monitoring near Tower Bridge",
            },
        ],
        "default": "silvertown",
    }


@router.get("/current", response_model=TideReading)
async def get_current_tide(station: str = "0001") -> TideReading:
    """Get the current tide level for a station.
    
    Args:
        station: Station ID (default: 0001 = Silvertown)
        
    Returns:
        Current tide reading
        
    Raises:
        HTTPException: If station data unavailable
    """
    reading = await tide_service.get_latest_reading(station)
    
    if reading is None:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to retrieve tide data for station {station}",
        )
    
    return reading


@router.get("/forecast", response_model=TideForecast)
async def get_tide_forecast(
    station: str = "0001",
    hours: int = 24,
) -> TideForecast:
    """Get tide forecast with predicted high/low tides.
    
    Uses harmonic analysis of past 24h data to predict
    tides for the next N hours.
    
    Args:
        station: Station ID (default: 0001 = Silvertown)
        hours: Hours to forecast ahead (default: 24, max: 72)
        
    Returns:
        Tide forecast with high/low tide predictions
        
    Raises:
        HTTPException: If forecast generation fails
    """
    if hours > 72:
        raise HTTPException(
            status_code=400,
            detail="Forecast hours cannot exceed 72",
        )
    
    forecast = await tide_service.get_tide_forecast(station, hours_ahead=hours)
    
    if not forecast.high_tides and not forecast.low_tides:
        raise HTTPException(
            status_code=503,
            detail="Insufficient data to generate forecast",
        )
    
    return forecast


@router.get("/stats")
async def get_tidal_statistics(station: str = "0001") -> dict:
    """Get tidal range statistics for the past 24 hours.
    
    Args:
        station: Station ID (default: 0001 = Silvertown)
        
    Returns:
        Dictionary with min, max, range, and mean values
    """
    stats = await tide_service.calculate_tidal_range(station)
    
    if stats["min"] is None:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to calculate statistics for station {station}",
        )
    
    return {
        "station_id": station,
        "period_hours": 24,
        **stats,
    }


@router.get("/optimal-walk")
async def get_optimal_walk_times(
    station: str = "0001",
    days: int = 3,
) -> dict:
    """Get 'perfect walk hotspots' - optimal times for Thames walks.
    
    Scores times based on:
    - High tide at sunset/sunrise (+3 points)
    - Clear skies <25% clouds (+2 points)
    - Low wind <10 mph (+1 point)
    - Comfortable temp 10-20°C (+1 point)
    
    Args:
        station: Station ID (default: 0001 = Silvertown)
        days: Days to analyze (default: 3, max: 5)
        
    Returns:
        List of optimal walk times with scores and conditions
        
    Raises:
        HTTPException: If hotspot calculation fails
    """
    if days > 5:
        raise HTTPException(
            status_code=400,
            detail="Days cannot exceed 5",
        )
    
    # Get weather forecast for hotspot calculation
    try:
        from whoopdata.services.weather_service import WeatherAPI
        
        weather_service = WeatherAPI()
        
        # Get Silvertown coordinates (approximate)
        coords = {"lat": 51.4975, "lon": 0.0526}
        
        # Get hourly forecast
        forecast = weather_service.get_forecast(coords["lat"], coords["lon"])
        
        # Convert to expected format for hotspot calculation
        weather_data = {
            "hourly": [
                {
                    "dt": f["timestamp"],
                    "clouds": f.get("clouds", 100),
                    "wind_speed": f.get("wind_speed", 0),
                    "temp": f.get("temperature", 273) + 273.15,  # Convert C to K
                }
                for f in forecast.get("forecast", [])
            ]
        }
        
        hotspots = await tide_service.calculate_perfect_walk_hotspots(
            weather_data=weather_data,
            station_id=station,
            days_ahead=days,
        )
        
        return {
            "station_id": station,
            "days_analyzed": days,
            "hotspots": [
                {
                    "time": spot["time"].isoformat(),
                    "score": spot["score"],
                    "max_score": 7,
                    "tide_height": round(spot["tide_height"], 2),
                    "conditions": spot["conditions"],
                }
                for spot in hotspots
            ],
        }
        
    except ValueError as e:
        # WeatherAPI init failed (missing API key)
        raise HTTPException(
            status_code=503,
            detail="Weather service unavailable - cannot calculate optimal walk times",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate optimal walk times: {str(e)}",
        )


@router.get("/station/{station_id}", response_model=TideStation)
async def get_station_info(station_id: str) -> TideStation:
    """Get metadata for a tidal monitoring station.
    
    Args:
        station_id: Station ID (e.g. "0001" for Silvertown)
        
    Returns:
        Station metadata
        
    Raises:
        HTTPException: If station not found
    """
    station = await tide_service.get_station_data(station_id)
    
    if station is None:
        raise HTTPException(
            status_code=404,
            detail=f"Station {station_id} not found",
        )
    
    return station
