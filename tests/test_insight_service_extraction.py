from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from whoopdata.api import daily_routes, dashboard_routes
from whoopdata.schemas.daily import CompareRequest, ScenarioInput, ScenarioRequest
from whoopdata.services.dashboard_service import DashboardService
from whoopdata.services.guidance_service import GuidanceService


def test_guidance_service_builds_daily_plan_from_shared_context():
    db = MagicMock()
    context_service = MagicMock()
    context_service.get_weather_summary.return_value = {"weather": "ok"}
    context_service.get_transport_status.return_value = {"transport": "ok"}
    context_service.get_tide_summary = AsyncMock(return_value={"tide": "ok"})

    engine = MagicMock()
    engine.generate_daily_plan.return_value = {"plan": "ok"}

    service = GuidanceService(db, context_service=context_service)

    with patch("whoopdata.services.guidance_service.DailyEngine", return_value=engine):
        result = asyncio.run(service.build_daily_plan())

    assert result == {"plan": "ok"}
    context_service.get_weather_summary.assert_called_once()
    context_service.get_transport_status.assert_called_once()
    context_service.get_tide_summary.assert_awaited_once()
    engine.generate_daily_plan.assert_called_once_with(
        weather_data={"weather": "ok"},
        transport_data={"transport": "ok"},
        tide_data={"tide": "ok"},
    )


def test_dashboard_service_composes_context_outside_router():
    db = MagicMock()
    context_service = MagicMock()
    context_service.get_weather_summary.return_value = {"weather": "ok"}
    context_service.get_transport_status.return_value = {"transport": "ok"}
    context_service.get_dashboard_tide_context = AsyncMock(return_value={"tide": "ok"})
    context_service.get_walk_hotspots = AsyncMock(return_value=[{"walk": "ok"}])

    service = DashboardService(db, context_service=context_service)
    service._build_dashboard_health_metrics = MagicMock(return_value={"health": "ok"})

    result = asyncio.run(service.build_daily_dashboard())

    assert result["health_metrics"] == {"health": "ok"}
    assert result["context"]["weather"] == {"weather": "ok"}
    assert result["context"]["transport"] == {"transport": "ok"}
    assert result["context"]["tide"] == {"tide": "ok"}
    assert result["context"]["walk_hotspots"] == [{"walk": "ok"}]


def test_dashboard_daily_route_delegates_to_dashboard_service(monkeypatch):
    db = MagicMock()
    expected = {"dashboard": "ok"}
    service = MagicMock()
    service.build_daily_dashboard = AsyncMock(return_value=expected)

    created: dict[str, object] = {}

    def fake_dashboard_service(passed_db):
        created["db"] = passed_db
        return service

    monkeypatch.setattr(dashboard_routes, "DashboardService", fake_dashboard_service)

    result = asyncio.run(dashboard_routes.get_daily_dashboard(location="Canary Wharf", db=db))

    assert result == expected
    assert created["db"] is db
    service.build_daily_dashboard.assert_awaited_once_with("Canary Wharf")


def test_dashboard_support_routes_delegate_to_dashboard_service(monkeypatch):
    db = MagicMock()
    service = MagicMock()
    service.get_health_metrics.return_value = {"metrics": "ok"}
    service.get_extended_weather.return_value = {"weather": "ok"}

    def fake_dashboard_service(passed_db=None, **kwargs):
        passed_db = kwargs.get("db", passed_db)
        assert passed_db is db or passed_db is None
        return service

    monkeypatch.setattr(dashboard_routes, "DashboardService", fake_dashboard_service)

    assert asyncio.run(dashboard_routes.get_health_metrics(db=db)) == {"metrics": "ok"}
    assert asyncio.run(dashboard_routes.get_weather_extended(location="Canary Wharf")) == {
        "weather": "ok"
    }
    service.get_health_metrics.assert_called_once_with()
    service.get_extended_weather.assert_called_once_with("Canary Wharf")


def test_daily_routes_delegate_to_guidance_service(monkeypatch):
    db = MagicMock()
    scenario = ScenarioInput(sleep_hours=8.0)
    scenario_request = ScenarioRequest(scenario=scenario)
    compare_request = CompareRequest(
        scenarios=[ScenarioInput(sleep_hours=7.0), ScenarioInput(sleep_hours=8.5)]
    )

    service = MagicMock()
    service.build_daily_plan = AsyncMock(return_value={"plan": "ok"})
    service.predict_scenario.return_value = {"scenario": "ok"}
    service.compare_scenarios.return_value = {"compare": "ok"}
    service.get_weekly_coaching_report.return_value = {"report": "ok"}

    created: dict[str, object] = {}

    def fake_guidance_service(passed_db):
        created["db"] = passed_db
        return service

    monkeypatch.setattr(daily_routes, "GuidanceService", fake_guidance_service)

    assert asyncio.run(daily_routes.get_daily_plan(db=db)) == {"plan": "ok"}
    assert asyncio.run(daily_routes.predict_scenario(scenario_request, db=db)) == {"scenario": "ok"}
    assert asyncio.run(daily_routes.compare_scenarios(compare_request, db=db)) == {
        "compare": "ok"
    }
    assert asyncio.run(daily_routes.get_weekly_coaching_report(weeks=2, db=db)) == {
        "report": "ok"
    }
    assert created["db"] is db
    service.build_daily_plan.assert_awaited_once_with()
    service.predict_scenario.assert_called_once_with(scenario)
    service.compare_scenarios.assert_called_once_with(compare_request.scenarios)
    service.get_weekly_coaching_report.assert_called_once_with(weeks=2)
