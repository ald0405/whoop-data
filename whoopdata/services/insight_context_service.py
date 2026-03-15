"""Reusable context composition helpers for insight-style services."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from whoopdata.services.tide_service import TideService
from whoopdata.services.transport_service import TravelAPI
from whoopdata.services.weather_service import WeatherAPI

DEFAULT_LOCATION = "Canary Wharf"
DEFAULT_TIDE_STATION_ID = "0001"
DEFAULT_TIDE_STATION_NAME = "Silvertown"

try:
    _DEFAULT_WEATHER_SERVICE = WeatherAPI()
except Exception:
    _DEFAULT_WEATHER_SERVICE = None

_DEFAULT_TRANSPORT_SERVICE = TravelAPI()
_DEFAULT_TIDE_SERVICE = TideService()


class InsightContextService:
    """Fetch reusable environmental context for insight and guidance flows."""

    def __init__(
        self,
        weather_service: WeatherAPI | None = None,
        transport_service: TravelAPI | None = None,
        tide_service: TideService | None = None,
    ):
        self.weather_service = (
            weather_service if weather_service is not None else _DEFAULT_WEATHER_SERVICE
        )
        self.transport_service = (
            transport_service if transport_service is not None else _DEFAULT_TRANSPORT_SERVICE
        )
        self.tide_service = tide_service if tide_service is not None else _DEFAULT_TIDE_SERVICE

    def _require_weather_service(self, detail: str) -> WeatherAPI:
        if not self.weather_service:
            raise ValueError(detail)
        return self.weather_service

    def get_weather_summary(self, location: str = DEFAULT_LOCATION) -> dict[str, Any]:
        """Return the normalized weather payload used by dashboard and daily-plan flows."""
        weather_service = self._require_weather_service("Weather service not configured")
        coords = weather_service.get_coordinates(location)
        current = weather_service.get_current_weather(coords["lat"], coords["lon"])
        forecast = weather_service.get_forecast(coords["lat"], coords["lon"])
        air_quality = weather_service.get_air_quality(coords["lat"], coords["lon"])

        today_forecast = forecast.get("forecast", [])[:8]
        temps = [item["temperature"] for item in today_forecast if "temperature" in item]
        forecast_summary = (
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
            "forecast_today": forecast_summary,
            "air_quality": {
                "aqi": air_quality["aqi"],
                "description": air_quality["aqi_description"],
            },
        }

    def get_transport_status(self) -> dict[str, Any] | list[Any]:
        """Return the normalized transport status payload."""
        return self.transport_service.get_line_status()

    async def get_tide_summary(
        self,
        station_id: str = DEFAULT_TIDE_STATION_ID,
        station_name: str = DEFAULT_TIDE_STATION_NAME,
    ) -> dict[str, Any]:
        """Return the lightweight tide payload used by the daily-plan flow."""
        current = await self.tide_service.get_latest_reading(station_id)
        if current is None:
            raise RuntimeError("Unable to fetch tide data")

        return {
            "current_level": round(current.value, 2),
            "station": station_name,
            "timestamp": current.timestamp.isoformat(),
        }

    async def get_dashboard_tide_context(
        self,
        station_id: str = DEFAULT_TIDE_STATION_ID,
        station_name: str = DEFAULT_TIDE_STATION_NAME,
        hours_ahead: int = 24,
    ) -> dict[str, Any]:
        """Return the richer tide payload used by the dashboard insight surface."""
        current_tide = await self.tide_service.get_latest_reading(station_id)
        tide_forecast = await self.tide_service.get_tide_forecast(
            station_id, hours_ahead=hours_ahead
        )

        if current_tide is None:
            raise RuntimeError("Unable to fetch tide data")

        return {
            "current": {
                "level": round(current_tide.value, 2),
                "unit": current_tide.unit,
                "station": station_name,
                "timestamp": current_tide.timestamp.isoformat(),
            },
            "next_high_tide": (
                {
                    "time": tide_forecast.high_tides[0]["time"].isoformat(),
                    "height": round(tide_forecast.high_tides[0]["height"], 2),
                }
                if tide_forecast.high_tides
                else None
            ),
            "next_low_tide": (
                {
                    "time": tide_forecast.low_tides[0]["time"].isoformat(),
                    "height": round(tide_forecast.low_tides[0]["height"], 2),
                }
                if tide_forecast.low_tides
                else None
            ),
        }

    async def get_walk_hotspots(
        self,
        station_id: str = DEFAULT_TIDE_STATION_ID,
        days: int = 5,
    ) -> list[dict[str, Any]]:
        """Return normalized perfect-walk hotspot recommendations."""
        weather_service = self._require_weather_service(
            "Weather service required for hotspot calculation"
        )
        coords = {"lat": 51.4975, "lon": 0.0526}
        forecast = weather_service.get_forecast(coords["lat"], coords["lon"])

        weather_data = {
            "hourly": [
                {
                    "dt": int(datetime.fromisoformat(item["timestamp"]).timestamp()),
                    "clouds": item.get("clouds", 100),
                    "wind_speed": item.get("wind_speed", 0),
                    "temp": item.get("temperature", 273) + 273.15,
                }
                for item in forecast.get("forecast", [])
            ],
            "sunrise": forecast.get("sunrise"),
            "sunset": forecast.get("sunset"),
        }

        hotspots = await self.tide_service.calculate_perfect_walk_hotspots(
            weather_data=weather_data,
            station_id=station_id,
            days_ahead=days,
        )

        return [
            {
                "time": spot["time"].isoformat(),
                "score": spot["score"],
                "max_score": 7,
                "tide_height": round(spot["tide_height"], 2),
                "temperature": (
                    round(spot["temperature"], 1)
                    if spot["temperature"] is not None
                    else None
                ),
                "conditions": spot["conditions"],
            }
            for spot in hotspots[:5]
        ]

    def get_extended_weather(self, location: str = DEFAULT_LOCATION) -> dict[str, Any]:
        """Return the richer multi-day weather payload used by dashboard insights."""
        weather_service = self._require_weather_service(
            "Weather service not configured - check OPENWEATHER_API_KEY"
        )
        coords = weather_service.get_coordinates(location)
        current = weather_service.get_current_weather(coords["lat"], coords["lon"])
        air_quality = weather_service.get_air_quality(coords["lat"], coords["lon"])
        daily_forecast = weather_service.get_daily_forecast_summary(
            coords["lat"], coords["lon"], days=5
        )
        time_of_day_forecast = weather_service.get_forecast_by_time_of_day(
            coords["lat"], coords["lon"], days=5
        )
        aqi_forecast = weather_service.get_air_pollution_forecast(coords["lat"], coords["lon"])

        aqi_daily: dict[str, dict[str, Any]] = {}
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
