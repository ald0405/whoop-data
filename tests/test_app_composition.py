from __future__ import annotations

from pathlib import Path

from main import app
from whoopdata.api.app_factory import ROUTER_GROUPS, ROUTER_REGISTRATION_ORDER


ROOT = Path(__file__).resolve().parents[1]


def _get_route_module(path: str, method: str = "GET") -> str:
    for route in app.routes:
        if getattr(route, "path", None) == path and method in (getattr(route, "methods", ()) or ()):
            return route.endpoint.__module__

    raise AssertionError(f"Route not found: {method} {path}")


def test_main_module_is_composition_only():
    main_text = (ROOT / "main.py").read_text()

    assert "@app." not in main_text
    assert "WithingsClient" not in main_text
    assert "create_app()" in main_text


def test_router_groups_are_declared_by_surface():
    assert ROUTER_REGISTRATION_ORDER == ("web", "data", "insights", "agent")
    assert set(ROUTER_GROUPS.keys()) == set(ROUTER_REGISTRATION_ORDER)


def test_page_routes_are_owned_by_dedicated_web_modules():
    assert _get_route_module("/") == "whoopdata.api.web_routes"
    assert _get_route_module("/analytics") == "whoopdata.api.web_routes"
    assert _get_route_module("/report") == "whoopdata.api.web_routes"
    assert _get_route_module("/dashboard/") == "whoopdata.api.dashboard_page_routes"


def test_withings_status_route_is_owned_by_dedicated_router():
    assert _get_route_module("/auth/withings/status") == "whoopdata.api.withings_status_routes"


def test_agent_routes_are_owned_by_dedicated_agent_router():
    assert _get_route_module("/api/v1/agent/conversations", "POST") == "whoopdata.api.agent_routes"
    assert _get_route_module("/api/v1/agent/messages", "POST") == "whoopdata.api.agent_routes"
