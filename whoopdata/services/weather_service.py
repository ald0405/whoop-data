"""Weather and air quality service using OpenWeatherMap API."""

import os
from typing import Dict, Any, Optional
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class WeatherAPI:
    """Client for OpenWeatherMap API providing weather and air quality data."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize WeatherAPI client.
        
        Args:
            api_key: OpenWeatherMap API key. If not provided, reads from OPENWEATHER_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("Missing OPENWEATHER_API_KEY in environment variables")
        
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.geo_url = "http://api.openweathermap.org/geo/1.0"
    
    def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch current weather conditions for given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with temperature, conditions, feels_like, humidity, wind_speed
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch weather data: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        return {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "conditions": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M") if "sys" in data and "sunrise" in data["sys"] else None,
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M") if "sys" in data and "sunset" in data["sys"] else None,
            "timestamp": datetime.fromtimestamp(data["dt"]).isoformat()
        }
    
    def get_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch 5-day weather forecast with 3-hour intervals.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with forecast list containing temperature, conditions, timestamp
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch forecast data: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        forecasts = []
        
        for item in data["list"]:
            forecasts.append({
                "timestamp": datetime.fromtimestamp(item["dt"]).isoformat(),
                "temperature": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "conditions": item["weather"][0]["description"],
                "humidity": item["main"]["humidity"],
                "wind_speed": item["wind"]["speed"]
            })
        
        return {
            "location": data["city"]["name"],
            "forecast": forecasts
        }
    
    def get_air_quality(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch current air quality data for given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with AQI and pollutant levels (PM2.5, PM10, CO, NO2, O3)
            AQI scale: 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/air_pollution?lat={lat}&lon={lon}&appid={self.api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch air quality data: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        aqi_data = data["list"][0]
        
        aqi_descriptions = {
            1: "Good",
            2: "Fair", 
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }
        
        return {
            "aqi": aqi_data["main"]["aqi"],
            "aqi_description": aqi_descriptions.get(aqi_data["main"]["aqi"], "Unknown"),
            "components": {
                "pm2_5": aqi_data["components"]["pm2_5"],
                "pm10": aqi_data["components"]["pm10"],
                "co": aqi_data["components"]["co"],
                "no2": aqi_data["components"]["no2"],
                "o3": aqi_data["components"]["o3"]
            },
            "timestamp": datetime.fromtimestamp(aqi_data["dt"]).isoformat()
        }
    
    def get_air_pollution_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch air quality forecast data.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dict with forecast list of AQI and pollutant levels
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/air_pollution/forecast?lat={lat}&lon={lon}&appid={self.api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch air pollution forecast: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        forecasts = []
        
        aqi_descriptions = {
            1: "Good",
            2: "Fair",
            3: "Moderate", 
            4: "Poor",
            5: "Very Poor"
        }
        
        for item in data["list"]:
            forecasts.append({
                "timestamp": datetime.fromtimestamp(item["dt"]).isoformat(),
                "aqi": item["main"]["aqi"],
                "aqi_description": aqi_descriptions.get(item["main"]["aqi"], "Unknown"),
                "pm2_5": item["components"]["pm2_5"],
                "pm10": item["components"]["pm10"]
            })
        
        return {"forecast": forecasts}
    
    def get_coordinates(self, location: str) -> Dict[str, Any]:
        """Get coordinates for a location name using geocoding.
        
        Args:
            location: Location name (e.g., "Canary Wharf", "London", "New York")
            
        Returns:
            Dict with lat, lon, name, country
            
        Raises:
            Exception: If location not found or API request fails
        """
        url = f"{self.geo_url}/direct?q={location}&limit=1&appid={self.api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to geocode location: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        
        if not data:
            raise Exception(f"Location '{location}' not found")
        
        return {
            "lat": data[0]["lat"],
            "lon": data[0]["lon"],
            "name": data[0]["name"],
            "country": data[0].get("country", "")
        }
    
    def get_daily_forecast_summary(self, lat: float, lon: float, days: int = 5) -> Dict[str, Any]:
        """Get weather forecast summarized by day.
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days (1-5)
            
        Returns:
            Dict with daily summaries including temp, conditions, wind
            
        Raises:
            Exception: If API request fails
        """
        forecast_data = self.get_forecast(lat, lon)
        forecasts = forecast_data["forecast"]
        
        # Group by date
        from collections import defaultdict
        daily_data = defaultdict(list)
        
        for item in forecasts[:days * 8]:  # 8 intervals per day
            date = datetime.fromisoformat(item["timestamp"]).date().isoformat()
            daily_data[date].append(item)
        
        # Summarize each day
        daily_summaries = []
        for date in sorted(daily_data.keys())[:days]:
            day_items = daily_data[date]
            temps = [i["temperature"] for i in day_items]
            winds = [i["wind_speed"] for i in day_items]
            conditions = [i["conditions"] for i in day_items]
            
            # Get most common condition
            from collections import Counter
            most_common_condition = Counter(conditions).most_common(1)[0][0]
            
            daily_summaries.append({
                "date": date,
                "temp_high": round(max(temps), 2),
                "temp_low": round(min(temps), 2),
                "temp_avg": round(sum(temps) / len(temps), 2),
                "wind_avg": round(sum(winds) / len(winds), 2),
                "wind_max": round(max(winds), 2),
                "conditions": most_common_condition
            })
        
        return {
            "location": forecast_data["location"],
            "daily_forecast": daily_summaries
        }
    
    def get_forecast_by_time_of_day(self, lat: float, lon: float, days: int = 5) -> Dict[str, Any]:
        """Get weather forecast grouped by time of day.
        
        Groups forecast into Morning (6am-12pm), Afternoon (12pm-6pm), Evening (6pm-12am).
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days to forecast (1-5)
            
        Returns:
            Dict with forecasts grouped by date and time period
            
        Raises:
            Exception: If API request fails
        """
        forecast_data = self.get_forecast(lat, lon)
        forecasts = forecast_data["forecast"]
        
        # Group by date and time of day
        from collections import defaultdict
        grouped_data = defaultdict(lambda: {"morning": [], "afternoon": [], "evening": []})
        
        for item in forecasts:
            dt = datetime.fromisoformat(item["timestamp"])
            date = dt.date().isoformat()
            hour = dt.hour
            
            # Categorize by time of day
            if 6 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 18:
                period = "afternoon"
            elif 18 <= hour < 24:
                period = "evening"
            else:
                continue  # Skip late night/early morning hours
            
            grouped_data[date][period].append(item)
        
        # Summarize each period
        result = []
        for date in sorted(grouped_data.keys())[:days]:
            day_data = grouped_data[date]
            
            for period in ["morning", "afternoon", "evening"]:
                items = day_data[period]
                if not items:
                    continue
                
                temps = [i["temperature"] for i in items]
                conditions = [i["conditions"] for i in items]
                winds = [i["wind_speed"] for i in items]
                
                # Get most common condition
                from collections import Counter
                most_common_condition = Counter(conditions).most_common(1)[0][0] if conditions else "N/A"
                
                result.append({
                    "date": date,
                    "period": period.capitalize(),
                    "temp_avg": round(sum(temps) / len(temps), 1) if temps else None,
                    "conditions": most_common_condition,
                    "wind_speed": round(sum(winds) / len(winds), 1) if winds else None
                })
        
        return {
            "location": forecast_data["location"],
            "forecast_by_time": result
        }
