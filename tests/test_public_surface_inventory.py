from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from fastapi.routing import APIRoute

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from main import app
from whoopdata.api.public_surface_contract import LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
from whoopdata.api.public_surface_inventory import (
    ENTRYPOINT_MIGRATION_MATRIX,
    FRAMEWORK_MANAGED_ROUTE_PREFIXES,
    ROUTE_MIGRATION_MATRIX,
    is_temporary_adapter_route,
)


ROOT = Path(__file__).resolve().parents[1]


def _actual_public_routes() -> dict[tuple[tuple[str, ...], str], tuple[str, ...]]:
    actual: dict[tuple[tuple[str, ...], str], list[str]] = defaultdict(list)

    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or path.startswith(FRAMEWORK_MANAGED_ROUTE_PREFIXES):
            continue

        methods = tuple(sorted(getattr(route, "methods", ()) or ()))
        actual[(methods, path)].append(route.name)

    return {key: tuple(value) for key, value in actual.items()}


def _expected_public_routes() -> dict[tuple[tuple[str, ...], str], tuple[str, ...]]:
    expected: dict[tuple[tuple[str, ...], str], tuple[str, ...]] = {}

    for entry in ROUTE_MIGRATION_MATRIX:
        key = (entry["methods"], entry["current_path"])
        assert key not in expected, f"Duplicate route key in inventory: {key}"
        expected[key] = entry["handler_names"]

    return expected

def _get_api_route(path: str, method: str = "GET") -> APIRoute:
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == path
            and method in (getattr(route, "methods", ()) or ())
        ):
            return route

    raise AssertionError(f"Route not found: {method} {path}")


def test_route_inventory_matches_fastapi_public_surface():
    assert _actual_public_routes() == _expected_public_routes()


def test_route_targets_match_surface_prefix_rules():
    for entry in ROUTE_MIGRATION_MATRIX:
        target = entry["target_path"]
        surface = entry["canonical_surface"]

        if surface == "web":
            assert not target.startswith("/api/v1/")
        elif surface == "data":
            assert target.startswith("/api/v1/data/")
        elif surface == "insights":
            assert target.startswith("/api/v1/insights/")
        elif surface == "agent":
            assert target.startswith("/api/v1/agent/")

def test_canonical_data_routes_are_not_deprecated():
    for entry in ROUTE_MIGRATION_MATRIX:
        if entry["canonical_surface"] != "data" or not entry["current_path"].startswith("/api/v1/data/"):
            continue

        route = _get_api_route(entry["current_path"], entry["methods"][0])
        assert not route.deprecated


def test_legacy_raw_data_routes_are_explicitly_deprecated():
    for entry in ROUTE_MIGRATION_MATRIX:
        if entry["canonical_surface"] != "data":
            continue
        if entry["current_path"].startswith("/api/v1/data/"):
            continue
        if entry["migration_action"] != "keep_temporary_adapter":
            continue

        route = _get_api_route(entry["current_path"], entry["methods"][0])
        assert route.deprecated is True


def test_canonical_insight_routes_are_not_deprecated():
    for entry in ROUTE_MIGRATION_MATRIX:
        if entry["canonical_surface"] != "insights" or not entry["current_path"].startswith("/api/v1/insights/"):
            continue

        route = _get_api_route(entry["current_path"], entry["methods"][0])
        assert not route.deprecated

def test_canonical_agent_routes_are_not_deprecated():
    for entry in ROUTE_MIGRATION_MATRIX:
        if entry["canonical_surface"] != "agent" or not entry["current_path"].startswith("/api/v1/agent/"):
            continue

        route = _get_api_route(entry["current_path"], entry["methods"][0])
        assert not route.deprecated


def test_legacy_insight_routes_are_explicitly_deprecated():
    for entry in ROUTE_MIGRATION_MATRIX:
        if entry["canonical_surface"] != "insights":
            continue
        if entry["current_path"].startswith("/api/v1/insights/"):
            continue
        if entry["migration_action"] != "keep_temporary_adapter":
            continue

        route = _get_api_route(entry["current_path"], entry["methods"][0])
        assert route.deprecated is True


def test_temporary_legacy_adapters_include_migration_guidance():
    for entry in ROUTE_MIGRATION_MATRIX:
        if not is_temporary_adapter_route(entry):
            continue

        assert entry["notes"]
        assert entry["target_path"] in entry["notes"]
        assert LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO in entry["notes"]

def test_project_script_inventory_matches_pyproject_scripts():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    actual_scripts = set(pyproject["project"]["scripts"].keys())
    inventory_scripts = {
        entry["current_identifier"]
        for entry in ENTRYPOINT_MIGRATION_MATRIX
        if entry["kind"] == "project_script"
    }

    assert inventory_scripts == actual_scripts


def test_runtime_entrypoints_reference_existing_files_and_targets():
    makefile_text = (ROOT / "Makefile").read_text()
    actual_make_targets = {
        match.group(1) for match in re.finditer(r"^([A-Za-z0-9_-]+):", makefile_text, flags=re.MULTILINE)
    }
    inventory_make_targets = {
        entry["current_identifier"]
        for entry in ENTRYPOINT_MIGRATION_MATRIX
        if entry["kind"] == "make_target"
    }

    assert inventory_make_targets.issubset(actual_make_targets)

    inventory_python_scripts = {
        entry["current_identifier"]
        for entry in ENTRYPOINT_MIGRATION_MATRIX
        if entry["kind"] == "python_script"
    }

    for script in inventory_python_scripts:
        assert (ROOT / script).exists()

    langgraph_config = json.loads((ROOT / "langgraph.json").read_text())
    inventory_graphs = {
        entry["current_identifier"]
        for entry in ENTRYPOINT_MIGRATION_MATRIX
        if entry["kind"] == "langgraph_graph"
    }

    assert inventory_graphs == set(langgraph_config["graphs"].keys())
