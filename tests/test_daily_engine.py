"""Tests for the daily decision engine and related services.

Uses mock data (no live DB required) to verify:
- Schema validation
- Action generation logic
- Scenario planner UX framing
- Coaching persona configuration
- Lifecycle segment detection
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from whoopdata.schemas.daily import (
    RecoveryStatus,
    DailyAction,
    SleepTarget,
    ContextSummary,
    DailyPlanResponse,
    ScenarioInput,
    ScenarioResult,
    ScenarioResponse,
    CompareRequest,
    CompareResponse,
)
from whoopdata.services.personas import (
    get_persona,
    get_system_prompt,
    get_action_text,
    list_personas,
    PERSONAS,
    DEFAULT_PERSONA,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestDailySchemas:
    def test_recovery_status_green(self):
        rs = RecoveryStatus(
            score=75.0,
            category="green",
            key_driver="Sleep Duration is your top recovery driver (32% importance)",
        )
        assert rs.category == "green"
        assert rs.score == 75.0

    def test_recovery_status_red(self):
        rs = RecoveryStatus(
            score=20.0,
            category="red",
            key_driver="No data",
            vs_baseline="-30% vs your 28-day average",
        )
        assert rs.category == "red"
        assert rs.vs_baseline is not None

    def test_daily_action_fields(self):
        action = DailyAction(
            action="Push your training today",
            reasoning="Recovery is 85% (green)",
            category="training",
            priority=1,
        )
        assert action.category == "training"
        assert action.priority == 1

    def test_sleep_target(self):
        st = SleepTarget(
            target_bedtime="22:30",
            target_hours=8.0,
            reasoning="Your best recoveries come with 8.0+ hours.",
        )
        assert st.target_hours == 8.0

    def test_context_summary_optional(self):
        ctx = ContextSummary()
        assert ctx.weather is None
        assert ctx.transport is None

    def test_daily_plan_response(self):
        plan = DailyPlanResponse(
            recovery_status=RecoveryStatus(
                score=60.0, category="yellow", key_driver="HRV"
            ),
            actions=[
                DailyAction(
                    action="Moderate training",
                    reasoning="Yellow day",
                    category="training",
                    priority=1,
                )
            ],
            sleep_target=SleepTarget(
                target_hours=7.5, reasoning="Based on your patterns."
            ),
            context=ContextSummary(),
            generated_at=datetime.utcnow(),
        )
        assert len(plan.actions) == 1
        assert plan.recovery_status.category == "yellow"


class TestScenarioSchemas:
    def test_scenario_input_validation(self):
        si = ScenarioInput(sleep_hours=8.0, strain=12.0)
        assert si.sleep_hours == 8.0
        assert si.label is None

    def test_scenario_input_with_label(self):
        si = ScenarioInput(label="Early night", sleep_hours=9.0)
        assert si.label == "Early night"

    def test_scenario_result(self):
        result = ScenarioResult(
            label="Test",
            predicted_recovery=72.5,
            confidence_interval=(65.0, 80.0),
            recovery_category="green",
            vs_baseline="+8% above your average",
            verdict="You'd likely wake up green",
            contributing_factors={"sleep_hours": 32.0, "hrv": 24.0},
        )
        assert result.recovery_category == "green"
        assert result.predicted_recovery == 72.5

    def test_compare_request_min_scenarios(self):
        req = CompareRequest(
            scenarios=[
                ScenarioInput(sleep_hours=7.0),
                ScenarioInput(sleep_hours=9.0),
            ]
        )
        assert len(req.scenarios) == 2


# ---------------------------------------------------------------------------
# Persona tests
# ---------------------------------------------------------------------------


class TestPersonas:
    def test_default_persona_exists(self):
        persona = get_persona()
        assert persona["name"] is not None
        assert "system_prompt" in persona

    def test_all_personas_have_required_keys(self):
        for pid, p in PERSONAS.items():
            assert "name" in p, f"Persona {pid} missing name"
            assert "system_prompt" in p, f"Persona {pid} missing system_prompt"
            assert "action_style" in p, f"Persona {pid} missing action_style"
            for cat in ["green", "yellow", "red"]:
                assert cat in p["action_style"], f"Persona {pid} missing {cat} action"

    def test_get_system_prompt_returns_string(self):
        prompt = get_system_prompt("direct_coach")
        assert isinstance(prompt, str)
        assert len(prompt) > 20

    def test_get_action_text(self):
        text = get_action_text("gentle_guide", "red")
        assert "easy" in text.lower() or "rest" in text.lower()

    def test_unknown_persona_falls_back_to_default(self):
        persona = get_persona("nonexistent_persona")
        default = get_persona(DEFAULT_PERSONA)
        assert persona["name"] == default["name"]

    def test_list_personas(self):
        personas = list_personas()
        assert len(personas) == len(PERSONAS)
        assert all("id" in p for p in personas)
        assert all("name" in p for p in personas)


# ---------------------------------------------------------------------------
# Action generation logic tests (unit testing _training_action etc.)
# ---------------------------------------------------------------------------


class TestActionGeneration:
    """Test the action generation methods from DailyEngine without DB."""

    def test_green_recovery_produces_training_action(self):
        from whoopdata.services.daily_engine import DailyEngine

        # We can't instantiate DailyEngine without DB, but we can test
        # the static-like methods by calling them on an instance with mocked db
        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=80.0, category="green", key_driver="Sleep"
        )
        action = engine._training_action(recovery, {}, 1)
        assert action is not None
        assert action.category == "training"
        assert "push" in action.action.lower() or "ready" in action.action.lower()

    def test_red_recovery_produces_rest_action(self):
        from whoopdata.services.daily_engine import DailyEngine

        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=20.0, category="red", key_driver="HRV"
        )
        action = engine._training_action(recovery, {}, 1)
        assert action is not None
        assert action.category == "recovery"
        assert "rest" in action.action.lower() or "recovery" in action.action.lower()

    def test_hrv_high_produces_positive_action(self):
        from whoopdata.services.daily_engine import DailyEngine

        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=70.0, category="green", hrv=80.0, key_driver="HRV"
        )
        baselines = {"hrv_7d": 60.0}  # 33% above average
        action = engine._hrv_action(recovery, baselines, 1)
        assert action is not None
        assert "primed" in action.action.lower() or "challenge" in action.action.lower()

    def test_hrv_low_produces_easy_action(self):
        from whoopdata.services.daily_engine import DailyEngine

        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=45.0, category="yellow", hrv=40.0, key_driver="HRV"
        )
        baselines = {"hrv_7d": 60.0}  # 33% below average
        action = engine._hrv_action(recovery, baselines, 1)
        assert action is not None
        assert "easy" in action.action.lower() or "fatigue" in action.action.lower()

    def test_sleep_deficit_produces_sleep_action(self):
        from whoopdata.services.daily_engine import DailyEngine

        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=50.0, category="yellow", key_driver="Sleep"
        )
        baselines = {"sleep_hours_7d": 6.5}
        sleep_patterns = {"optimal_sleep_hours": 8.0}
        action = engine._sleep_action(recovery, baselines, sleep_patterns, 1)
        assert action is not None
        assert action.category == "sleep"

    def test_weather_aqi_warning(self):
        from whoopdata.services.daily_engine import DailyEngine

        engine = DailyEngine.__new__(DailyEngine)

        recovery = RecoveryStatus(
            score=80.0, category="green", key_driver="Sleep"
        )
        weather = {
            "current": {"conditions": "clear", "temp": 18},
            "air_quality": {"aqi": 5, "description": "Very Poor"},
        }
        action = engine._weather_action(weather, recovery, 1)
        assert action is not None
        assert "indoor" in action.action.lower()
