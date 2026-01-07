"""Thames Tide Service for Environment Agency API."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from loguru import logger

from whoopdata.models.tide import TideForecast, TideReading, TideStation


class TideService:
    """Service for fetching Thames tide data from Environment Agency."""

    BASE_URL = "https://environment.data.gov.uk/flood-monitoring"
    
    # East London tidal stations
    STATIONS = {
        "silvertown": "0001",
        "charlton": "0003",
        "tower_pier": "0007",
    }
    
    # Default station for queries
    DEFAULT_STATION = "silvertown"

    def __init__(self, timeout: int = 10):
        """Initialize tide service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def get_station_data(self, station_id: str) -> Optional[TideStation]:
        """Get metadata for a tidal station.
        
        Args:
            station_id: Station ID (e.g. "0001" for Silvertown)
            
        Returns:
            TideStation object or None if request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.BASE_URL}/id/stations/{station_id}")
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", {})
                return TideStation(
                    station_id=items.get("notation"),
                    name=items.get("label"),
                    latitude=items.get("lat"),
                    longitude=items.get("long"),
                )
        except Exception as e:
            logger.error(f"Failed to get station data for {station_id}: {e}")
            return None

    async def get_latest_reading(self, station_id: str) -> Optional[TideReading]:
        """Get the latest tide reading for a station.
        
        Args:
            station_id: Station ID (e.g. "0001" for Silvertown)
            
        Returns:
            TideReading object or None if request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/id/stations/{station_id}/readings?latest"
                )
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                if not items:
                    return None
                    
                reading = items[0]
                return TideReading(
                    station_id=station_id,
                    timestamp=datetime.fromisoformat(
                        reading["dateTime"].replace("Z", "+00:00")
                    ),
                    value=reading["value"],
                    unit="mAOD",
                )
        except Exception as e:
            logger.error(f"Failed to get latest reading for {station_id}: {e}")
            return None

    async def get_readings_range(
        self, 
        station_id: str, 
        hours: int = 24
    ) -> list[TideReading]:
        """Get tide readings for the past N hours.
        
        Args:
            station_id: Station ID
            hours: Number of hours to look back
            
        Returns:
            List of TideReading objects
        """
        try:
            # 15-min intervals = 4 readings per hour
            limit = hours * 4
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/id/stations/{station_id}/readings",
                    params={"_sorted": "true", "_limit": limit}
                )
                response.raise_for_status()
                data = response.json()
                
                readings = []
                for item in data.get("items", []):
                    readings.append(TideReading(
                        station_id=station_id,
                        timestamp=datetime.fromisoformat(
                            item["dateTime"].replace("Z", "+00:00")
                        ),
                        value=item["value"],
                        unit="mAOD",
                    ))
                
                # Sort by timestamp ascending
                readings.sort(key=lambda r: r.timestamp)
                return readings
                
        except Exception as e:
            logger.error(f"Failed to get readings range for {station_id}: {e}")
            return []

    async def calculate_tidal_range(self, station_id: str) -> dict:
        """Calculate tidal range statistics for the past 24 hours.
        
        Args:
            station_id: Station ID
            
        Returns:
            Dict with min, max, range, and mean values
        """
        readings = await self.get_readings_range(station_id, hours=24)
        
        if not readings:
            return {
                "min": None,
                "max": None,
                "range": None,
                "mean": None,
            }
        
        values = [r.value for r in readings]
        min_val = min(values)
        max_val = max(values)
        
        return {
            "min": round(min_val, 3),
            "max": round(max_val, 3),
            "range": round(max_val - min_val, 3),
            "mean": round(sum(values) / len(values), 3),
        }

    async def get_tide_forecast(
        self, 
        station_id: str, 
        hours_ahead: int = 24
    ) -> TideForecast:
        """Generate tide forecast using tidal prediction.
        
        Uses simple harmonic analysis of past 24h data to predict
        high/low tides for the next N hours.
        
        Args:
            station_id: Station ID
            hours_ahead: Hours to forecast ahead (default 24)
            
        Returns:
            TideForecast object with predicted high/low tides
        """
        # Get past 24h of readings for pattern analysis
        readings = await self.get_readings_range(station_id, hours=24)
        
        if len(readings) < 48:  # Need at least 12 hours of data
            logger.warning(f"Insufficient data for forecast ({len(readings)} readings)")
            return TideForecast(
                station_id=station_id,
                forecast_start=datetime.now(timezone.utc),
                forecast_hours=hours_ahead,
                high_tides=[],
                low_tides=[],
            )
        
        # Find turning points (high/low tides)
        high_tides = []
        low_tides = []
        
        for i in range(1, len(readings) - 1):
            prev_val = readings[i - 1].value
            curr_val = readings[i].value
            next_val = readings[i + 1].value
            
            # High tide: local maximum
            if curr_val > prev_val and curr_val > next_val:
                high_tides.append({
                    "time": readings[i].timestamp,
                    "height": curr_val,
                })
            
            # Low tide: local minimum
            elif curr_val < prev_val and curr_val < next_val:
                low_tides.append({
                    "time": readings[i].timestamp,
                    "height": curr_val,
                })
        
        # Calculate average period between tides (Thames is semi-diurnal: ~12.4h)
        if len(high_tides) >= 2:
            high_periods = [
                (high_tides[i]["time"] - high_tides[i-1]["time"]).total_seconds() / 3600
                for i in range(1, len(high_tides))
            ]
            avg_period = sum(high_periods) / len(high_periods)
        else:
            avg_period = 12.4  # Thames typical semi-diurnal period
        
        # Extrapolate next tides
        predicted_high = []
        predicted_low = []
        
        now = datetime.now(timezone.utc)
        forecast_end = now + timedelta(hours=hours_ahead)
        
        if high_tides:
            last_high = high_tides[-1]
            next_high_time = last_high["time"] + timedelta(hours=avg_period)
            
            while next_high_time < forecast_end:
                predicted_high.append({
                    "time": next_high_time,
                    "height": last_high["height"],  # Use last observed height
                })
                next_high_time += timedelta(hours=avg_period)
        
        if low_tides:
            last_low = low_tides[-1]
            next_low_time = last_low["time"] + timedelta(hours=avg_period)
            
            while next_low_time < forecast_end:
                predicted_low.append({
                    "time": next_low_time,
                    "height": last_low["height"],
                })
                next_low_time += timedelta(hours=avg_period)
        
        return TideForecast(
            station_id=station_id,
            forecast_start=now,
            forecast_hours=hours_ahead,
            high_tides=predicted_high,
            low_tides=predicted_low,
        )

    async def calculate_perfect_walk_hotspots(
        self,
        weather_data: dict,
        station_id: str = None,
        days_ahead: int = 3,
        min_hour: int = 7,
        max_hour: int = 21,
    ) -> list[dict]:
        """Calculate perfect walk time hotspots.
        
        Scores times based on:
        - High tide during daylight hours (+3 points)
        - Clear skies <30% clouds (+2 points)
        - Low wind <10 mph (+1 point)
        - Comfortable temp 10-20°C (+1 point)
        - Additional points for sunset/sunrise timing
        
        Only considers times between min_hour and max_hour (default 7am-9pm).
        
        Args:
            weather_data: Weather forecast data with hourly conditions
            station_id: Station ID (defaults to Silvertown)
            days_ahead: Number of days to analyze (default 3)
            min_hour: Earliest hour to consider (default 7 for 7am)
            max_hour: Latest hour to consider (default 21 for 9pm)
            
        Returns:
            List of hotspot dicts with time, score, temperature, and conditions
        """
        if station_id is None:
            station_id = self.STATIONS[self.DEFAULT_STATION]
        
        # Get tide forecast
        forecast = await self.get_tide_forecast(station_id, hours_ahead=days_ahead * 24)
        
        # Get sunrise/sunset times from weather data
        sunrise_timestamp = weather_data.get("sunrise")
        sunset_timestamp = weather_data.get("sunset")
        
        hotspots = []
        
        # Check each high tide
        for high_tide in forecast.high_tides:
            tide_time = high_tide["time"]
            
            # Skip if outside practical hours (default: before 7am or after 9pm)
            local_hour = tide_time.hour  # Assuming UTC, adjust if needed
            if local_hour < min_hour or local_hour > max_hour:
                continue
            
            score = 0
            conditions = []
            temp_c = None
            
            # Base points for being during daylight/practical hours
            if sunrise_timestamp and sunset_timestamp:
                sunrise_dt = datetime.fromtimestamp(sunrise_timestamp, tz=timezone.utc)
                sunset_dt = datetime.fromtimestamp(sunset_timestamp, tz=timezone.utc)
                tide_date = tide_time.date()
                sunrise_on_tide_date = datetime.combine(tide_date, sunrise_dt.time(), tzinfo=timezone.utc)
                sunset_on_tide_date = datetime.combine(tide_date, sunset_dt.time(), tzinfo=timezone.utc)
                
                # Check if during daylight hours
                if sunrise_on_tide_date <= tide_time <= sunset_on_tide_date:
                    score += 2
                    conditions.append("Daylight hours")
            
            # Bonus points for being near sunset or sunrise (within 1 hour)
            is_sunset_time = False
            is_sunrise_time = False
            
            if sunset_timestamp:
                sunset_dt = datetime.fromtimestamp(sunset_timestamp, tz=timezone.utc)
                tide_date = tide_time.date()
                sunset_on_tide_date = datetime.combine(tide_date, sunset_dt.time(), tzinfo=timezone.utc)
                time_diff = abs((tide_time - sunset_on_tide_date).total_seconds() / 3600)
                if time_diff <= 1:  # Within 1 hour of sunset
                    score += 2
                    conditions.append("Near sunset")
                    is_sunset_time = True
            
            if not is_sunset_time and sunrise_timestamp:
                sunrise_dt = datetime.fromtimestamp(sunrise_timestamp, tz=timezone.utc)
                tide_date = tide_time.date()
                sunrise_on_tide_date = datetime.combine(tide_date, sunrise_dt.time(), tzinfo=timezone.utc)
                time_diff = abs((tide_time - sunrise_on_tide_date).total_seconds() / 3600)
                if time_diff <= 1 and local_hour >= min_hour:  # Within 1 hour of sunrise AND after min_hour
                    score += 2
                    conditions.append("Near sunrise")
                    is_sunrise_time = True
            
            # Find matching weather data for this time
            # Assumes weather_data has 'hourly' list with 'dt' timestamps
            if "hourly" in weather_data:
                matching_weather = None
                for hour_data in weather_data["hourly"]:
                    hour_dt = datetime.fromtimestamp(hour_data["dt"], tz=timezone.utc)
                    if abs((hour_dt - tide_time).total_seconds()) < 3600:  # Within 1 hour
                        matching_weather = hour_data
                        break
                
                if matching_weather:
                    # Check cloud cover
                    clouds = matching_weather.get("clouds", 100)
                    if clouds < 30:
                        score += 2
                        conditions.append(f"Clear skies ({clouds}% clouds)")
                    
                    # Check wind speed (convert m/s to mph: 1 m/s ≈ 2.237 mph)
                    wind_ms = matching_weather.get("wind_speed", 0)
                    wind_mph = wind_ms * 2.237
                    if wind_mph < 10:
                        score += 1
                        conditions.append(f"Low wind ({wind_mph:.1f} mph)")
                    
                    # Check temperature
                    temp_k = matching_weather.get("temp", 273)
                    temp_c = temp_k - 273.15
                    if 10 <= temp_c <= 20:
                        score += 1
                        conditions.append(f"Comfortable temp ({temp_c:.1f}°C)")
            
            hotspots.append({
                "time": tide_time,
                "score": score,
                "tide_height": high_tide["height"],
                "temperature": temp_c,
                "conditions": conditions,
            })
        
        # Sort by score (best first), then by time
        hotspots.sort(key=lambda x: (-x["score"], x["time"]))
        
        # Update max_score to reflect new scoring (2 base + 2 sunset/sunrise + 2 clouds + 1 wind + 1 temp = 8)
        for hotspot in hotspots:
            hotspot["max_score"] = 8
        
        return hotspots
