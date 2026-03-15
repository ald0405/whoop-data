from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from whoopdata.api.legacy_route_deprecation import (
    LEGACY_ROUTE_RESPONSE_HEADERS,
    LEGACY_ROUTE_SUNSET_HTTP_DATE,
)
from whoopdata.api.public_surface_contract import LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
from whoopdata.api.public_surface_inventory import ROUTE_MIGRATION_MATRIX


REPRESENTATIVE_LEGACY_ROUTES = (
    ("/recovery/latest", "GET"),
    ("/workouts/latest", "GET"),
    ("/dashboard/daily", "GET"),
    ("/api/daily-plan", "GET"),
)


def _target_path_for(path: str, method: str) -> str:
    return next(
        entry["target_path"]
        for entry in ROUTE_MIGRATION_MATRIX
        if entry["current_path"] == path and entry["methods"] == (method,)
    )


@pytest.mark.parametrize(("path", "method"), REPRESENTATIVE_LEGACY_ROUTES)
def test_legacy_route_openapi_includes_replacement_and_removal_metadata(path: str, method: str):
    schema = app.openapi()
    operation = schema["paths"][path][method.lower()]
    target_path = _target_path_for(path, method)

    assert operation["deprecated"] is True
    assert operation["x-canonical-path"] == target_path
    assert operation["x-deprecation-removal-date"] == LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
    assert operation["x-migration-action"] == "keep_temporary_adapter"
    assert target_path in operation["description"]
    assert LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO in operation["description"]

    response_headers = operation["responses"]["200"]["headers"]
    assert response_headers == LEGACY_ROUTE_RESPONSE_HEADERS


@pytest.mark.parametrize(("path", "method"), REPRESENTATIVE_LEGACY_ROUTES)
def test_legacy_route_responses_emit_deprecation_headers(path: str, method: str):
    client = TestClient(app, raise_server_exceptions=False)
    target_path = _target_path_for(path, method)

    response = client.request(method, path)

    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == LEGACY_ROUTE_SUNSET_HTTP_DATE
    assert response.headers["Link"] == f'<{target_path}>; rel="successor-version"'
    assert response.headers["X-Canonical-Route"] == target_path
    assert (
        response.headers["X-Deprecated-Route-Removal-Date"]
        == LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
    )
