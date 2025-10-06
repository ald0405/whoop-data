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
    
    # Code Execution Tools
    python_repl_tool,
]
