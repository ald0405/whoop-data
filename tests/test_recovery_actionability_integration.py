from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from whoopdata.api.app_factory import create_app
from whoopdata.schemas.daily import SleepTarget
from whoopdata.services.proactive_coach import ProactiveCoachPlanner


def test_recovery_actionability_endpoint_404_when_missing():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    with patch("whoopdata.api.analytics_routes.results_loader.load_result", return_value=None):
        resp = client.get("/api/v1/insights/analytics/recovery/actionability")

    assert resp.status_code == 404
    assert "not yet computed" in resp.json()["detail"].lower()


def test_recovery_actionability_endpoint_returns_payload():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    payload = {
        "version": 1,
        "computed_at": datetime.utcnow().isoformat(),
        "days_back": 365,
        "min_group_size": 25,
        "rules": [
            {
                "rule": "Bedtime at or before 23:00",
                "recommendation": "Aim to be asleep by about 23:00 or earlier",
                "feature": "bedtime_hour_extended",
                "threshold": 23.0,
                "direction": "le",
                "days_in_rule": 40,
                "days_outside_rule": 40,
                "avg_recovery_in_rule": 68.0,
                "avg_recovery_outside_rule": 60.0,
                "green_rate_in_rule": 0.55,
                "green_rate_outside_rule": 0.40,
                "recovery_delta": 8.0,
                "green_rate_delta": 0.15,
            }
        ],
        "best_thresholds": {"strain_3d_sum_max": 36.5, "bedtime_before": "23:00"},
        "notes": [],
    }

    with patch(
        "whoopdata.api.analytics_routes.RecoveryActionabilityService.build_snapshot",
        return_value=payload,
    ):
        resp = client.get("/api/v1/insights/analytics/recovery/actionability")

    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 1
    assert body["best_thresholds"]["bedtime_before"] == "23:00"
    assert body["rules"][0]["feature"] == "bedtime_hour_extended"


def test_recovery_actionability_endpoint_returns_contextual_snapshot_fields():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    payload = {
        "version": 1,
        "computed_at": datetime.utcnow().isoformat(),
        "days_back": 365,
        "min_group_size": 25,
        "rules": [],
        "best_thresholds": {},
        "notes": [],
        "current_state": {"sleep_hours": 7.2, "recovery_score": 64},
        "baseline_prediction": {
            "predicted_recovery": 66.0,
            "recovery_category": "yellow",
            "confidence_interval": [60.0, 72.0],
            "vs_baseline": "+0% vs your 28-day average (66%)",
            "verdict": "You'd likely wake up yellow — keep it easy tomorrow",
        },
        "scenario_prediction": {
            "predicted_recovery": 71.0,
            "recovery_category": "green",
            "confidence_interval": [65.0, 77.0],
            "vs_baseline": "+5% vs your 28-day average (66%)",
            "verdict": "You'd likely wake up green — a good day ahead",
        },
        "top_adjustments": [
            {
                "label": "3-day strain",
                "current": 36.0,
                "target": 34.0,
                "recommendation": "Aim to keep recent 3-day strain around 34.0 or lower.",
            }
        ],
        "reliability_summary": "This estimate is usually within about 8 recovery points.",
        "model_available": True,
    }

    with patch(
        "whoopdata.api.analytics_routes.RecoveryActionabilityService.build_snapshot",
        return_value=payload,
    ):
        resp = client.get("/api/v1/insights/analytics/recovery/actionability")

    assert resp.status_code == 200
    body = resp.json()
    assert body["model_available"] is True
    assert body["scenario_prediction"]["recovery_category"] == "green"
    assert body["top_adjustments"][0]["label"] == "3-day strain"


def test_recovery_actionability_post_returns_baseline_and_scenario_prediction():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    payload = {
        "version": 1,
        "computed_at": datetime.utcnow().isoformat(),
        "days_back": 365,
        "min_group_size": 25,
        "rules": [],
        "best_thresholds": {},
        "notes": [],
        "current_state": {"sleep_hours": 7.2, "recovery_score": 64},
        "baseline_prediction": {
            "predicted_recovery": 66.0,
            "recovery_category": "yellow",
            "confidence_interval": [60.0, 72.0],
            "vs_baseline": "+0% vs your 28-day average (66%)",
            "verdict": "You'd likely wake up yellow — keep it easy tomorrow",
        },
        "scenario_prediction": {
            "predicted_recovery": 73.0,
            "recovery_category": "green",
            "confidence_interval": [67.0, 79.0],
            "vs_baseline": "+7% vs your 28-day average (66%)",
            "verdict": "You'd likely wake up green — a good day ahead",
        },
        "top_adjustments": [],
        "reliability_summary": "This estimate is usually within about 8 recovery points.",
        "model_available": True,
    }

    with patch(
        "whoopdata.api.analytics_routes.RecoveryActionabilityService.build_snapshot",
        return_value=payload,
    ):
        resp = client.post(
            "/api/v1/insights/analytics/recovery/actionability",
            json={"sleep_hours": 8.0, "strain": 8.0, "sleep_efficiency": 90},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["baseline_prediction"]["predicted_recovery"] == 66.0
    assert body["scenario_prediction"]["predicted_recovery"] == 73.0


def test_daily_engine_injects_actionability_sentence():
    from whoopdata.services.daily_engine import DailyEngine

    engine = DailyEngine.__new__(DailyEngine)

    target = SleepTarget(target_bedtime="22:30", target_hours=8.0, reasoning="Base.")

    with patch(
        "whoopdata.services.daily_engine.results_loader.load_result",
        return_value={"best_thresholds": {"strain_3d_sum_max": 35.0, "bedtime_before": "23:00"}},
    ):
        injected = engine._inject_actionability_thresholds(target)

    assert "strain" in injected.reasoning.lower()
    assert "23:00" in injected.reasoning


def test_proactive_morning_briefing_includes_actionability_in_evidence():
    # ProactiveCoachPlanner doesn't require DB usage for morning briefing.
    planner = ProactiveCoachPlanner.__new__(ProactiveCoachPlanner)
    planner.now_fn = lambda: datetime(2026, 3, 23, 7, 30, 0)

    with patch(
        "whoopdata.analytics.results_loader.results_loader.load_result",
        return_value={"best_thresholds": {"strain_3d_sum_max": 34.5, "bedtime_before": "22:30"}},
    ):
        decision = planner._build_morning_briefing(now=planner.now_fn(), mode="morning")

    assert decision.intent == "morning_briefing"
    assert "recovery_actionability" in decision.evidence
    assert decision.evidence["recovery_actionability"]["bedtime_before"] == "22:30"
