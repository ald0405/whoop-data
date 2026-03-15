from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from whoopdata.api.legacy_route_deprecation import (
    LEGACY_ROUTE_RESPONSE_HEADERS,
    LEGACY_ROUTE_SUNSET_HTTP_DATE,
)
from whoopdata.api.public_surface_contract import LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
from whoopdata.api.public_surface_inventory import ROUTE_MIGRATION_MATRIX


WORKOUTS_LATEST_TARGET = next(
    entry["target_path"]
    for entry in ROUTE_MIGRATION_MATRIX
    if entry["current_path"] == "/workouts/latest" and entry["methods"] == ("GET",)
)


def test_legacy_route_openapi_includes_replacement_and_removal_metadata():
    schema = app.openapi()
    operation = schema["paths"]["/workouts/latest"]["get"]

    assert operation["deprecated"] is True
    assert operation["x-canonical-path"] == WORKOUTS_LATEST_TARGET
    assert operation["x-deprecation-removal-date"] == LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
    assert operation["x-migration-action"] == "keep_temporary_adapter"
    assert WORKOUTS_LATEST_TARGET in operation["description"]
    assert LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO in operation["description"]

    response_headers = operation["responses"]["200"]["headers"]
    assert response_headers == LEGACY_ROUTE_RESPONSE_HEADERS


def test_legacy_route_responses_emit_deprecation_headers():
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/workouts/latest")

    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == LEGACY_ROUTE_SUNSET_HTTP_DATE
    assert response.headers["Link"] == f'<{WORKOUTS_LATEST_TARGET}>; rel="successor-version"'
    assert response.headers["X-Canonical-Route"] == WORKOUTS_LATEST_TARGET
    assert (
        response.headers["X-Deprecated-Route-Removal-Date"]
        == LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
    )
