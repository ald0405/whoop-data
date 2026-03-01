"""Agent registry for specialist subagent configuration.

Each entry defines a specialist that will be wrapped as a tool
for the supervisor agent to delegate to.
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"


def _load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


# ---------------------------------------------------------------------------
# Specialist registry
# ---------------------------------------------------------------------------
# Each entry maps a specialist name to its configuration.
# - description: shown to the supervisor as the tool description (routing signal)
# - system_prompt: inline prompt or loaded from file
# - tools: list of tool names from AVAILABLE_TOOLS to give this specialist
# - model: optional model override (defaults to settings.SPECIALIST_MODEL)
# ---------------------------------------------------------------------------

AGENT_REGISTRY: dict[str, dict] = {
    "health_data": {
        "name": "health_data",
        "description": (
            "Retrieve and summarise WHOOP and Withings health data. "
            "Covers recovery scores, sleep stages/efficiency, workout strain/zones, "
            "running TRIMP scores, tennis performance, weight/body composition, "
            "heart rate, blood pressure, and overall Withings summaries. "
            "Use this for any question about the user's recorded health metrics."
        ),
        "system_prompt": (
            "You are a health data retrieval specialist. Your job is to fetch the user's "
            "WHOOP and Withings data efficiently.\n\n"
            "When asked for comprehensive or long-term data:\n"
            "1. Call multiple tools in parallel when they're independent (recovery, sleep, weight, workouts)\n"
            "2. Use appropriate limits: latest=False, limit=90-365 for trends, limit=10 for recent snapshots\n"
            "3. Pull get_recovery_trends for multi-week recovery patterns\n"
            "4. Pull get_weight_stats for weight trends over time\n\n"
            "Present data clearly:\n"
            "- Key numbers with dates\n"
            "- Note obvious patterns (trending up/down, high variability, etc)\n"
            "- Be precise with units\n"
            "- Keep it factual - the supervisor will add interpretation\n\n"
            "Examples of good multi-tool calls:\n"
            "- Long-term overview → recovery_trends + weight_stats + workout_data(limit=30)\n"
            "- Recent snapshot → recovery(latest), sleep(latest), weight(latest)\n"
            "- Training analysis → workouts(limit=50) + recovery_data(limit=50)"
        ),
        "tools": [
            "get_recovery_data",
            "get_sleep_data",
            "get_workout_data",
            "get_running_workouts",
            "get_tennis_workouts",
            "get_weight_data",
            "get_weight_stats",
            "get_heart_rate_data",
            "get_withings_summary",
            "get_recovery_trends",
            "get_protein_recommendation",
        ],
    },
    "analytics": {
        "name": "analytics",
        "description": (
            "Run statistical analysis, ML predictions, and pattern detection on health data. "
            "Covers recovery factor importance, metric correlations, recovery/sleep predictions, "
            "weekly automated insights, and trend detection (recovery, HRV, RHR, sleep). "
            "Use this when the user wants analysis, predictions, or deeper insights beyond raw data."
        ),
        "system_prompt": (
            "You are a health analytics specialist. Your job is to run statistical "
            "and ML-powered analyses on the user's health data. "
            "Present results clearly: ranked factors with percentages, correlation strengths, "
            "prediction intervals, trend directions. Include actionable thresholds where the "
            "data supports them. Be precise and evidence-based."
        ),
        "tools": [
            "analyze_recovery_factors",
            "analyze_correlations",
            "predict_recovery",
            "predict_sleep_performance",
            "get_weekly_insights",
            "detect_patterns",
        ],
    },
    "environment": {
        "name": "environment",
        "description": (
            "Get current weather, air quality, forecasts, London transport status, "
            "Thames tide times, and optimal riverside walk times. "
            "Use this for any question about weather, commute, or outdoor conditions."
        ),
        "system_prompt": (
            "You are an environment and local conditions specialist. "
            "Fetch weather, air quality, transport status, and tide information. "
            "Present conditions clearly and note anything relevant for outdoor activities "
            "(e.g. poor air quality for running, transport disruptions, high tide timing)."
        ),
        "tools": [
            "get_weather",
            "get_air_quality",
            "get_weather_forecast",
            "get_transport_status",
            "get_tide_times",
            "get_perfect_walk_times",
        ],
    },
    "exercise": {
        "name": "exercise",
        "description": (
            "Create exercise plans and training programmes. "
            "Covers progressive overload, periodisation, sport-specific training, "
            "FITT-VP prescriptions, and modifications for all fitness levels. "
            "Use this when the user asks for workout plans, training advice, "
            "or exercise programming."
        ),
        "system_prompt": _load_prompt("exercise_sub_agent.md"),
        "tools": [
            "get_weight_data",
            "get_workout_data",
            "get_recovery_data",
        ],
    },
    "behaviour_change": {
        "name": "behaviour_change",
        "description": (
            "Behaviour change coaching using COM-B framework and Behaviour Change Techniques. "
            "Covers goal setting, action planning, barrier analysis, habit formation, "
            "motivation support, and relapse prevention. "
            "Use this when the user is struggling with adherence, motivation, or forming habits."
        ),
        "system_prompt": _load_prompt("behaviour_change_sub_agent.md"),
        "tools": [
            "get_recovery_data",
            "get_weight_data",
            "get_workout_data",
        ],
    },
    "nutrition": {
        "name": "nutrition",
        "description": (
            "Nutrition guidance and protein intake recommendations. "
            "Calculates personalized protein targets based on current weight and activity level. "
            "Use this when the user asks about protein intake, nutrition advice, or dietary recommendations."
        ),
        "system_prompt": (
            "You are a nutrition specialist focused on evidence-based recommendations. \n\n"
            "IMPORTANT: The get_protein_recommendation tool AUTOMATICALLY fetches the user's current "
            "weight from Withings. NEVER ask the user for their weight - the tool handles this. \n\n"
            "Your workflow:\n"
            "1. If user asks for protein recommendation and provides activity level → call tool immediately\n"
            "2. If user asks but doesn't specify activity level → ask ONLY for activity level\n"
            "3. Call get_protein_recommendation_tool with the activity level\n"
            "4. Provide the result with any relevant context\n\n"
            "Protein recommendations follow standard guidelines:\n"
            "- Normal activity: 1.2-1.4g per kg bodyweight\n"
            "- Endurance training: 1.2-1.4g per kg bodyweight\n"
            "- Resistance/strength training: 1.6-2.2g per kg bodyweight\n\n"
            "Valid activity levels: 'normal', 'endurance training', 'resistance/strength training'"
        ),
        "tools": [
            "get_protein_recommendation",
            "get_weight_data",
            "get_workout_data",
        ],
    },
}
