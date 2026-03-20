"""Agent registry for specialist subagent configuration.

Each entry defines an internal stateless specialist that will be wrapped as a
tool for the supervisor agent to delegate to. The registry is the source of
truth for specialist ownership boundaries alongside the typed specialist
handoff/result contracts.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PROMPTS_DIR = Path(__file__).parent.parent.parent / "data" / "prompts" / "agents"


def _load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text()
    return ""


SpecialistKind = Literal["retrieval", "analysis", "context", "coaching"]


@dataclass(frozen=True)
class SpecialistBoundary:
    """Ownership and routing contract for an internal specialist."""

    kind: SpecialistKind
    delegate_when: tuple[str, ...]
    owns: tuple[str, ...]
    excludes: tuple[str, ...]


@dataclass(frozen=True)
class DeterministicWorkflowBoundary:
    """Workflow that should stay outside specialist delegation."""

    name: str
    reason: str


@dataclass(frozen=True)
class SpecialistArchitecture:
    """Top-level routing rules for the coaching specialist architecture."""

    public_interface: str
    public_interface_owner: str
    internal_runtime: str
    final_response_owner: str
    chaining_rule: str
    deterministic_workflows: tuple[DeterministicWorkflowBoundary, ...]


SPECIALIST_ARCHITECTURE = SpecialistArchitecture(
    public_interface="health_coach",
    public_interface_owner="single user-facing supervisor",
    internal_runtime="internal stateless specialists wrapped as supervisor tools",
    final_response_owner="supervisor",
    chaining_rule=(
        "Specialists do not call each other directly; they surface follow-up "
        "needs and the supervisor decides whether to chain."
    ),
    deterministic_workflows=(
        DeterministicWorkflowBoundary(
            name="daily_plan",
            reason="Daily planning is a deterministic guidance workflow, not conversational delegation.",
        ),
        DeterministicWorkflowBoundary(
            name="scenario_prediction",
            reason="What-if scenario prediction is owned by the scenario planner service.",
        ),
        DeterministicWorkflowBoundary(
            name="scenario_comparison",
            reason="Side-by-side scenario comparison is owned by the scenario planner service.",
        ),
        DeterministicWorkflowBoundary(
            name="weekly_coaching_report",
            reason="Weekly coaching reports are generated as structured insight flows.",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Specialist registry
# ---------------------------------------------------------------------------
# Each entry maps a specialist name to its configuration.
# - description: shown to the supervisor as the tool description (routing signal)
# - system_prompt: inline prompt or loaded from file
# - boundary: ownership and exclusion rules used for delegation design
# - tools: list of tool names from AVAILABLE_TOOLS to give this specialist
# - model: optional model override (defaults to settings.SPECIALIST_MODEL)
# ---------------------------------------------------------------------------
AGENT_REGISTRY: dict[str, dict[str, object]] = {
    "health_data": {
        "name": "health_data",
        "description": (
            "Retrieve and summarise WHOOP and Withings health data. "
            "Covers recovery scores, sleep stages/efficiency, workout strain/zones, "
            "running TRIMP scores, tennis performance, weight/body composition, "
            "heart rate, blood pressure, and overall Withings summaries. "
            "Use this when the supervisor needs recorded metrics, source facts, "
            "or historical context before analysis or coaching."
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
            "- Keep it factual - the supervisor will add interpretation and coaching\n\n"
            "Examples of good multi-tool calls:\n"
            "- Long-term overview → recovery_trends + weight_stats + workout_data(limit=30)\n"
            "- Recent snapshot → recovery(latest), sleep(latest), weight(latest)\n"
            "- Training analysis → workouts(limit=50) + recovery_data(limit=50)"
        ),
        "boundary": SpecialistBoundary(
            kind="retrieval",
            delegate_when=(
                "The user wants recorded values, dates, recent snapshots, or source-grounded history.",
                "The supervisor needs facts before analysis, prediction, or coaching synthesis.",
            ),
            owns=(
                "WHOOP and Withings record retrieval.",
                "Source-grounded summaries of recorded health metrics.",
            ),
            excludes=(
                "Statistical interpretation, prediction, and factor analysis.",
                "Nutrition, exercise, or behaviour-change recommendations.",
            ),
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
        "boundary": SpecialistBoundary(
            kind="analysis",
            delegate_when=(
                "The user asks why a metric changed, what predicts an outcome, or how metrics relate.",
                "The supervisor needs pattern detection, ranking, or forecasting beyond factual summaries.",
            ),
            owns=(
                "Trend detection, correlations, factor analysis, and prediction.",
                "Evidence-based interpretation of retrieved health data.",
            ),
            excludes=(
                "Primary raw-data retrieval as the main task.",
                "Final multi-domain coaching synthesis or action-plan authorship.",
            ),
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
            "Use this for questions about weather, commute, or outdoor conditions that "
            "should inform another plan."
        ),
        "system_prompt": (
            "You are an environment and local conditions specialist. "
            "Fetch weather, air quality, transport status, and tide information. "
            "Present conditions clearly and note anything relevant for outdoor activities "
            "(e.g. poor air quality for running, transport disruptions, high tide timing)."
        ),
        "boundary": SpecialistBoundary(
            kind="context",
            delegate_when=(
                "The user asks about environmental conditions directly.",
                "The supervisor needs weather, air quality, transport, or tide context before advising.",
            ),
            owns=(
                "Local condition retrieval and concise environmental context.",
                "Constraint signals for outdoor activities and commuting.",
            ),
            excludes=(
                "Exercise prescription, behavioural coaching, or nutrition guidance.",
                "Final plan synthesis across multiple domains.",
            ),
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
        "boundary": SpecialistBoundary(
            kind="coaching",
            delegate_when=(
                "The main question is workout design, progression, or training modification.",
                "The supervisor needs exercise-specific reasoning after reviewing data or constraints.",
            ),
            owns=(
                "Training prescription, progression, and programme structure.",
                "Exercise-specific modifications within normal coaching safety boundaries.",
            ),
            excludes=(
                "Medical diagnosis, rehab, or injury treatment.",
                "Behaviour-change orchestration or multi-specialist routing.",
            ),
        ),
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
            "Use this when adherence, motivation, barriers, or habit formation is the main problem."
        ),
        "system_prompt": _load_prompt("behaviour_change_sub_agent.md"),
        "boundary": SpecialistBoundary(
            kind="coaching",
            delegate_when=(
                "The main problem is adherence, motivation, consistency, or behavioural barriers.",
                "The supervisor needs COM-B or BCT reasoning rather than domain programming.",
            ),
            owns=(
                "Barrier analysis, action planning, habit formation, and relapse prevention.",
                "Behaviour strategy for following through on an existing health goal.",
            ),
            excludes=(
                "Exercise programming or training-periodisation decisions.",
                "Direct nutrition prescription beyond behaviour support.",
            ),
        ),
        "tools": [
            "get_recovery_data",
            "get_weight_data",
            "get_workout_data",
        ],
    },
    "nutrition": {
        "name": "nutrition",
        "description": (
            "Nutrition guidance grounded in current weight and activity context. "
            "The current runtime is strongest on protein intake recommendations and weight/training context. "
            "Use this when the user asks about protein intake, nutrition advice, or dietary recommendations."
        ),
        "system_prompt": (
            "You are a nutrition specialist focused on evidence-based recommendations. \n\n"
            "IMPORTANT: The get_protein_recommendation tool AUTOMATICALLY fetches the user's current "
            "weight from Withings. NEVER ask the user for their weight - the tool handles this. \n\n"
            "Your workflow:\n"
            "1. If user asks for protein recommendation and provides activity level → call tool immediately\n"
            "2. If user asks but doesn't specify activity level → return a clarification need requesting ONLY activity level\n"
            "3. Call get_protein_recommendation with the activity level\n"
            "4. Put the recommendation, caveats, and next-step framing into the structured result fields\n\n"
            "Protein recommendations follow standard guidelines:\n"
            "- Normal activity: 1.2-1.4g per kg bodyweight\n"
            "- Endurance training: 1.2-1.4g per kg bodyweight\n"
            "- Resistance/strength training: 1.6-2.2g per kg bodyweight\n\n"
            "Valid activity levels: 'normal', 'endurance training', 'resistance/strength training'"
        ),
        "boundary": SpecialistBoundary(
            kind="coaching",
            delegate_when=(
                "The main question is about diet, nutrition strategy, or protein targets.",
                "The supervisor needs nutrition-specific reasoning rather than exercise or behaviour design.",
            ),
            owns=(
                "Nutrition recommendations grounded in weight and training context.",
                "Protein-target guidance with the current toolset.",
            ),
            excludes=(
                "Exercise programming or training-plan design.",
                "Broader habit-system design that belongs to behaviour-change coaching.",
            ),
        ),
        "tools": [
            "get_protein_recommendation",
            "get_weight_data",
            "get_workout_data",
        ],
    },
}
