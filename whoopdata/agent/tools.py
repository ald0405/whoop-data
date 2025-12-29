"""Agent tools for health data retrieval."""

import httpx
import json
from langchain_core.tools import tool
from langchain_experimental.tools import PythonREPLTool
from langchain_experimental.utilities import PythonREPL
from . import settings


# WHOOP Recovery Tools
@tool("get_recovery_data", description="Get WHOOP recovery data with flexible filtering - supports latest, historical ranges, and comprehensive analysis")
async def get_recovery_data_tool(latest: bool = True, limit: int = 100, skip: int = 0, start_date: str = None, end_date: str = None, top: bool = False) -> str:
    """Get WHOOP recovery data with flexible filtering options.
    
    Args:
        latest: Get only the latest recovery record (default: True)
        limit: Maximum number of records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip for pagination (default: 0)
        start_date: Start date filter in YYYY-MM-DD format (optional)
        end_date: End date filter in YYYY-MM-DD format (optional)  
        top: Get top recoveries by score instead of latest (default: False)
    
    Returns:
        JSON string containing recovery data with scores, HRV, resting heart rate, and other metrics
        
    Examples:
        - get_recovery_data_tool() - Latest recovery only
        - get_recovery_data_tool(latest=False, limit=365) - Full year of data
        - get_recovery_data_tool(start_date="2024-01-01", end_date="2024-12-31", latest=False) - 2024 data
        - get_recovery_data_tool(top=True, limit=10, latest=False) - Top 10 recovery scores
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/recovery"
            params = {}
            
            if latest:
                params["latest"] = "true"
            if top:
                params["top"] = "true" 
            if not latest and not top:
                params["limit"] = limit
                params["skip"] = skip
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
                
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving recovery data: HTTP {response.status_code} - {response.text}"
                
    except httpx.TimeoutException:
        return "Error: Request timed out while retrieving recovery data"
    except httpx.RequestError as e:
        return f"Error: Network error while retrieving recovery data - {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error while retrieving recovery data - {str(e)}"


@tool("get_top_recoveries", description="Get the highest WHOOP recovery scores to see your best recovery days")
async def get_top_recoveries_tool(limit: int = 10) -> str:
    """Get the top recovery scores to identify patterns in your best recovery days.
    
    Args:
        limit: Number of top recovery records to retrieve (default: 10)
    
    Returns:
        JSON string containing the highest recovery scores and their dates
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/recoveries/top"
            params = {"limit": limit}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving top recoveries: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving top recoveries: {str(e)}"


# WHOOP Sleep Tools
@tool("get_sleep_data", description="Get WHOOP sleep data with flexible filtering - supports latest, historical ranges, and comprehensive analysis")
async def get_sleep_data_tool(latest: bool = True, limit: int = 100, skip: int = 0, start_date: str = None, end_date: str = None) -> str:
    """Get WHOOP sleep data with flexible filtering options.
    
    Args:
        latest: Get only the latest sleep record (default: True)
        limit: Maximum number of records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip for pagination (default: 0)
        start_date: Start date filter in YYYY-MM-DD format (optional)
        end_date: End date filter in YYYY-MM-DD format (optional)
    
    Returns:
        JSON string containing sleep stages, efficiency, duration, and sleep quality metrics
        
    Examples:
        - get_sleep_data_tool() - Latest sleep only
        - get_sleep_data_tool(latest=False, limit=365) - Full year of sleep data
        - get_sleep_data_tool(start_date="2024-01-01", end_date="2024-12-31", latest=False) - 2024 sleep data
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/sleep"
            params = {}
            
            if latest:
                params["latest"] = "true"
            else:
                params["limit"] = limit
                params["skip"] = skip
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
                
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving sleep data: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving sleep data: {str(e)}"


# WHOOP Workout Tools
@tool("get_workout_data", description="Get WHOOP workout data with flexible filtering - supports latest, historical ranges, and comprehensive analysis")
async def get_workout_data_tool(latest: bool = True, limit: int = 100, skip: int = 0, start_date: str = None, end_date: str = None) -> str:
    """Get WHOOP workout data with flexible filtering options.
    
    Args:
        latest: Get only the latest workout record (default: True)
        limit: Maximum number of records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip for pagination (default: 0) 
        start_date: Start date filter in YYYY-MM-DD format (optional)
        end_date: End date filter in YYYY-MM-DD format (optional)
    
    Returns:
        JSON string containing workout data with strain, calories, heart rate zones, and workout type
        
    Examples:
        - get_workout_data_tool() - Latest workout only
        - get_workout_data_tool(latest=False, limit=200) - Comprehensive workout history
        - get_workout_data_tool(start_date="2024-01-01", end_date="2024-12-31", latest=False) - 2024 workouts
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/workouts"
            params = {}
            
            if latest:
                params["latest"] = "true"
            else:
                params["limit"] = limit
                params["skip"] = skip
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
                
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving workout data: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving workout data: {str(e)}"


@tool("get_running_workouts", description="Get running workouts with TRIMP scores - supports large datasets for comprehensive analysis")
async def get_running_workouts_tool(limit: int = 10) -> str:
    """Get recent running workouts with calculated TRIMP (Training Impulse) scores.
    
    Args:
        limit: Number of recent running workouts to retrieve (default: 10, can be set much higher for full analysis)
    
    Returns:
        JSON string containing running workouts with heart rate zones, pace, distance, and TRIMP scores
        
    Note: This tool can retrieve large datasets - use limit=100+ to analyze entire training history.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/workouts/analytics/trimp"
            params = {"limit": limit, "skip": 0}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving running workouts: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving running workouts: {str(e)}"


@tool("get_tennis_workouts", description="Get tennis workouts and performance data - supports comprehensive historical analysis")
async def get_tennis_workouts_tool(limit: int = 10) -> str:
    """Get recent tennis workouts with performance metrics.
    
    Args:
        limit: Number of recent tennis workouts to retrieve (default: 10, can be set higher for full analysis)
    
    Returns:
        JSON string containing tennis workout data with strain, duration, and heart rate metrics
        
    Note: This tool can retrieve extensive historical data - use limit=50+ for comprehensive analysis.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/workouts/types/tennis"
            params = {"limit": limit, "skip": 0}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving tennis workouts: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving tennis workouts: {str(e)}"


# Withings Weight Tools
@tool("get_weight_data", description="Get Withings weight data with flexible filtering - supports latest, historical ranges, and comprehensive analysis")
async def get_weight_data_tool(latest: bool = True, limit: int = 100, skip: int = 0, start_date: str = None, end_date: str = None) -> str:
    """Get Withings weight and body composition data with flexible filtering options.
    
    Args:
        latest: Get only the latest weight record (default: True)
        limit: Maximum number of records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip for pagination (default: 0)
        start_date: Start date filter in YYYY-MM-DD format (optional)
        end_date: End date filter in YYYY-MM-DD format (optional)
    
    Returns:
        JSON string containing weight, BMI, body fat percentage, muscle mass, and weight category data
        
    Examples:
        - get_weight_data_tool() - Latest weight only
        - get_weight_data_tool(latest=False, limit=365) - Full year of weight data
        - get_weight_data_tool(start_date="2024-01-01", end_date="2024-12-31", latest=False) - 2024 weight data
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/withings/weight"
            params = {}
            
            if latest:
                params["latest"] = "true"
            else:
                params["limit"] = limit
                params["skip"] = skip
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
                
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving weight data: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving weight data: {str(e)}"


@tool("get_weight_stats", description="Get weight statistics and trends over a specified time period")
async def get_weight_stats_tool(days: int = 30) -> str:
    """Get weight statistics including trends, changes, and averages over a time period.
    
    Args:
        days: Number of days to analyze for weight statistics (default: 30)
    
    Returns:
        JSON string containing weight trends, min/max values, average, and total change
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/withings/weight/analytics"
            params = {"days": days}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving weight stats: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving weight stats: {str(e)}"


# Withings Heart Rate Tools
@tool("get_heart_rate_data", description="Get Withings heart rate data with flexible filtering - supports latest, historical ranges, and comprehensive analysis")
async def get_heart_rate_data_tool(latest: bool = True, limit: int = 100, skip: int = 0, start_date: str = None, end_date: str = None) -> str:
    """Get Withings heart rate and blood pressure data with flexible filtering options.
    
    Args:
        latest: Get only the latest heart rate record (default: True)
        limit: Maximum number of records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip for pagination (default: 0)
        start_date: Start date filter in YYYY-MM-DD format (optional)
        end_date: End date filter in YYYY-MM-DD format (optional)
    
    Returns:
        JSON string containing heart rate, systolic/diastolic blood pressure, and BP category data
        
    Examples:
        - get_heart_rate_data_tool() - Latest heart rate only
        - get_heart_rate_data_tool(latest=False, limit=365) - Full year of heart rate data
        - get_heart_rate_data_tool(start_date="2024-01-01", end_date="2024-12-31", latest=False) - 2024 heart rate data
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/withings/heart-rate"
            params = {}
            
            if latest:
                params["latest"] = "true"
            else:
                params["limit"] = limit
                params["skip"] = skip
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
                
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving heart rate data: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving heart rate data: {str(e)}"


# Combined Summary Tools
@tool("get_withings_summary", description="Get a comprehensive summary of all Withings health data including weight and cardiovascular metrics")
async def get_withings_summary_tool() -> str:
    """Get a complete summary of Withings health data including latest measurements and record counts.
    
    Returns:
        JSON string containing latest weight, heart rate, blood pressure, and total record counts
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/withings/summary"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving Withings summary: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving Withings summary: {str(e)}"


@tool("get_all_recovery_data", description="Get comprehensive recovery data with flexible filtering - supports large date ranges")
async def get_all_recovery_data_tool(limit: int = 100, skip: int = 0) -> str:
    """Get comprehensive recovery data from the database with flexible filtering.
    
    Args:
        limit: Maximum number of recovery records to retrieve (default: 100, can be much higher)
        skip: Number of records to skip (for pagination, default: 0)
    
    Returns:
        JSON string containing recovery records with scores, HRV, dates, and other metrics
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/recoveries/"
            params = {"limit": limit, "skip": skip}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving recovery data: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving recovery data: {str(e)}"


@tool("get_recovery_trends", description="Get weekly average recovery scores and trends - supports flexible time ranges")
async def get_recovery_trends_tool(weeks: int = 4) -> str:
    """Get weekly average recovery scores to analyze recovery trends over time.
    
    Args:
        weeks: Number of weeks to analyze for recovery trends (default: 4, but can be set to 52+ for full year data)
    
    Returns:
        JSON string containing weekly average recovery scores and resting heart rate trends
        
    Note: This tool supports analyzing data for the entire year 2025 or any extended time period.
    For example: use weeks=52 for a full year of data.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/recovery/analytics/weekly"
            params = {"weeks": weeks}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving recovery trends: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving recovery trends: {str(e)}"


# Weather and Transport Tools
@tool("get_weather", description="Get current weather conditions for a location - useful for planning workouts and outdoor activities")
async def get_weather_tool(location: str = settings.DEFAULT_LOCATION) -> str:
    """Get current weather conditions for a location.
    
    Args:
        location: Location name (e.g., "Canary Wharf", "London", "New York")
        
    Returns:
        JSON string containing current weather with temperature, conditions, humidity, wind speed
        
    Examples:
        - get_weather_tool() - Weather for default location (Canary Wharf)
        - get_weather_tool("Central London") - Weather for Central London
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/weather/current"
            params = {"location": location}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving weather: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving weather: {str(e)}"


@tool("get_air_quality", description="Get current air quality index (AQI) for a location - important for outdoor workout planning")
async def get_air_quality_tool(location: str = settings.DEFAULT_LOCATION) -> str:
    """Get current air quality index and pollutant levels for a location.
    
    Args:
        location: Location name (e.g., "Canary Wharf", "London")
        
    Returns:
        JSON string containing AQI (1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor) and pollutant levels
        
    Use case: Determine if outdoor running or cycling is safe based on air quality
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/weather/air-quality"
            params = {"location": location}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving air quality: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving air quality: {str(e)}"


@tool("get_weather_forecast", description="Get multi-day weather forecast for a location - useful for planning training schedules")
async def get_weather_forecast_tool(location: str = settings.DEFAULT_LOCATION, days: int = 3) -> str:
    """Get weather forecast for upcoming days.
    
    Args:
        location: Location name (e.g., "Canary Wharf", "London")
        days: Number of days to forecast (1-5, default: 3)
        
    Returns:
        JSON string containing weather forecast with 3-hour intervals
        
    Examples:
        - get_weather_forecast_tool() - 3-day forecast for default location
        - get_weather_forecast_tool("London", 5) - 5-day forecast for London
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/weather/forecast"
            params = {"location": location, "days": days}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving forecast: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving forecast: {str(e)}"


@tool("get_transport_status", description="Get current TfL transport status for key lines (Jubilee, DLR, Elizabeth, Northern) - relevant for workout timing and stress levels")
async def get_transport_status_tool() -> str:
    """Get current status of key London transport lines.
    
    Returns:
        JSON string containing status for Jubilee Line, DLR, Elizabeth Line, and Northern Line
        Status is either "Good Service" or describes disruptions
        
    Use case: Check for transport disruptions that might affect workout timing or increase daily stress
    """
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/transport/status"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error retrieving transport status: HTTP {response.status_code} - {response.text}"
                
    except Exception as e:
        return f"Error retrieving transport status: {str(e)}"


# Analytics Tools
@tool("analyze_recovery_factors", description="Analyze what factors influence your recovery most - shows ranked importance with actionable thresholds")
async def analyze_recovery_factors_tool(days_back: int = 365) -> str:
    """Analyze what factors drive recovery with ML-powered feature importance.
    
    Args:
        days_back: Days of historical data to analyze (default: 365)
        
    Returns:
        JSON with ranked factors, importance %, plain English explanations, and actionable thresholds
        
    Example: "Sleep duration accounts for 32% of your recovery - aim for 8+ hours"
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:  # Longer timeout for ML training
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/recovery/factors"
            params = {"days_back": days_back}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error analyzing recovery factors: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error analyzing recovery factors: {str(e)}"


@tool("analyze_correlations", description="Analyze how health metrics correlate with each other - reveals relationships between sleep, recovery, HRV, strain")
async def analyze_correlations_tool(days_back: int = 365) -> str:
    """Analyze correlations between health metrics with statistical significance.
    
    Args:
        days_back: Days of historical data (default: 365)
        
    Returns:
        JSON with significant correlations (p<0.05), strength ratings, and real examples from your data
        
    Example: "Strong correlation (0.72) between sleep quality and recovery"
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/correlations"
            params = {"days_back": days_back}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error analyzing correlations: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error analyzing correlations: {str(e)}"


@tool("predict_recovery", description="Predict recovery score from sleep/HRV/strain inputs - get expected recovery with confidence interval")
async def predict_recovery_tool(
    sleep_hours: float,
    sleep_efficiency: float = None,
    strain: float = None,
    hrv: float = None,
    rhr: float = None
) -> str:
    """Predict recovery score from input health metrics.
    
    Args:
        sleep_hours: Hours of sleep (required)
        sleep_efficiency: Sleep efficiency % (optional)
        strain: Strain score (optional)
        hrv: HRV in milliseconds (optional)
        rhr: Resting heart rate (optional)
        
    Returns:
        JSON with predicted recovery, confidence interval, category (Green/Yellow/Red), and explanation
        
    Example: "Based on 8 hours sleep, expect 68% recovery (±5%) - Green category"
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/predict/recovery"
            payload = {"sleep_hours": sleep_hours}
            if sleep_efficiency is not None:
                payload["sleep_efficiency"] = sleep_efficiency
            if strain is not None:
                payload["strain"] = strain
            if hrv is not None:
                payload["hrv"] = hrv
            if rhr is not None:
                payload["rhr"] = rhr
            
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error predicting recovery: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error predicting recovery: {str(e)}"


@tool("predict_sleep_performance", description="Predict sleep performance score from sleep metrics - see expected sleep score")
async def predict_sleep_performance_tool(
    total_sleep_hours: float,
    rem_sleep_hours: float,
    awake_time_hours: float
) -> str:
    """Predict sleep performance score from sleep metrics.
    
    Args:
        total_sleep_hours: Total sleep time in hours
        rem_sleep_hours: REM sleep time in hours
        awake_time_hours: Time awake in hours
        
    Returns:
        JSON with predicted sleep performance %, confidence interval, and explanation
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/predict/sleep"
            payload = {
                "total_sleep_hours": total_sleep_hours,
                "rem_sleep_hours": rem_sleep_hours,
                "awake_time_hours": awake_time_hours
            }
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error predicting sleep: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error predicting sleep: {str(e)}"


@tool("get_weekly_insights", description="Get automated weekly health insights - actionable recommendations and trends")
async def get_weekly_insights_tool(weeks: int = 1) -> str:
    """Get automated weekly insights with priority-ranked recommendations.
    
    Args:
        weeks: Number of weeks to analyze (1-12, default: 1)
        
    Returns:
        JSON with 3-5 actionable insights, categories (success/alert/opportunity), and weekly summary
        
    Example insights:
    - "📈 Recovery up 12% - keep it up!"
    - "💤 Your best recoveries: 8+ hours sleep with 87%+ efficiency"
    - "⚠️ High strain week - schedule recovery days"
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/insights/weekly"
            params = {"weeks": weeks}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error getting insights: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error getting insights: {str(e)}"


@tool("detect_patterns", description="Detect trends and patterns in a specific metric - shows if recovery/HRV/RHR/sleep is trending up/down")
async def detect_patterns_tool(metric: str, days: int = 30) -> str:
    """Analyze trends for a specific health metric.
    
    Args:
        metric: Metric to analyze - 'recovery', 'hrv', 'rhr', or 'sleep'
        days: Days to analyze (7-365, default: 30)
        
    Returns:
        JSON with trend direction, trend %, data points, anomalies, and plain English description
        
    Example: "HRV trending up 8% over past 30 days - sign of improving fitness"
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{settings.HEALTH_API_BASE_URL}/analytics/patterns/{metric}"
            params = {"days": days}
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data, indent=2)
            else:
                return f"Error detecting patterns: HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error detecting patterns: {str(e)}"


# Configure matplotlib globally before creating the tool
import matplotlib
matplotlib.use('Agg', force=True)

# Standard Python REPL tool with matplotlib pre-configured
python_repl_tool = PythonREPLTool(
    name="python_interpreter", 
    description="""Execute Python code to perform data analysis, create visualizations, and statistical computations.
    
    Use this tool to:
    - Analyze health data with pandas and numpy
    - Create charts and visualizations with matplotlib/seaborn
    - Perform statistical analysis and calculations  
    - Process JSON data from health APIs
    - Calculate correlations, trends, and insights
    
    IMPORTANT: Matplotlib is configured for headless operation to prevent crashes.
    
    ALWAYS start your plotting code with these imports:
    ```python
    import matplotlib
    matplotlib.use('Agg', force=True)
    import matplotlib.pyplot as plt
    plt.ioff()
    import pandas as pd
    import numpy as np
    import seaborn as sns
    ```
    
    For plotting:
    - Create your plot as normal with plt.figure(), plt.plot(), etc.
    - Use plt.savefig('filename.png') to save plots
    - Or return plot data as needed
    
    Example:
    ```python
    import matplotlib
    matplotlib.use('Agg', force=True) 
    import matplotlib.pyplot as plt
    plt.ioff()
    import numpy as np
    
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    plt.figure(figsize=(8, 6))
    plt.plot(x, y)
    plt.title('Sin Wave')
    plt.savefig('sin_plot.png', dpi=150, bbox_inches='tight')
    plt.close()
    print('Plot saved as sin_plot.png')
    ```
    """
)


# List of all available tools for easy import
AVAILABLE_TOOLS = [
    # WHOOP Recovery Tools  
    get_recovery_data_tool,
    get_recovery_trends_tool,
    
    # WHOOP Sleep Tools
    get_sleep_data_tool,
    
    # WHOOP Workout Tools
    get_workout_data_tool,
    get_running_workouts_tool,
    get_tennis_workouts_tool,
    
    # Withings Weight Tools
    get_weight_data_tool,
    get_weight_stats_tool,
    
    # Withings Heart Rate Tools
    get_heart_rate_data_tool,
    
    # Summary Tools
    get_withings_summary_tool,
    
    # Analytics Tools
    analyze_recovery_factors_tool,
    analyze_correlations_tool,
    predict_recovery_tool,
    predict_sleep_performance_tool,
    get_weekly_insights_tool,
    detect_patterns_tool,
    
    # Weather Tools
    get_weather_tool,
    get_air_quality_tool,
    get_weather_forecast_tool,
    
    # Transport Tools
    get_transport_status_tool,
    
    # Code Execution Tools
    python_repl_tool,
]
