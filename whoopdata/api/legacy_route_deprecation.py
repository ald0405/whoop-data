from __future__ import annotations

from datetime import datetime, time, timezone
from email.utils import format_datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from whoopdata.api.public_surface_contract import (
    LEGACY_COMPATIBILITY_REMOVAL_DATE,
    LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO,
    build_legacy_route_guidance,
)
from whoopdata.api.public_surface_inventory import (
    ROUTE_MIGRATION_MATRIX,
    RouteMigrationEntry,
    is_temporary_adapter_route,
)

SUCCESSOR_VERSION_REL = "successor-version"
LEGACY_ROUTE_SUNSET_HTTP_DATE = format_datetime(
    datetime.combine(
        LEGACY_COMPATIBILITY_REMOVAL_DATE,
        time(23, 59, 59),
        tzinfo=timezone.utc,
    ),
    usegmt=True,
)
LEGACY_ROUTE_RESPONSE_HEADERS: dict[str, dict[str, Any]] = {
    "Deprecation": {
        "description": "Boolean-style deprecation signal for temporary compatibility routes.",
        "schema": {"type": "string", "enum": ["true"]},
    },
    "Sunset": {
        "description": f"HTTP-date for the planned compatibility sunset ({LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}).",
        "schema": {"type": "string"},
    },
    "Link": {
        "description": f"Canonical replacement route advertised with rel=\"{SUCCESSOR_VERSION_REL}\".",
        "schema": {"type": "string"},
    },
    "X-Canonical-Route": {
        "description": "Canonical replacement path for this compatibility route.",
        "schema": {"type": "string"},
    },
    "X-Deprecated-Route-Removal-Date": {
        "description": f"ISO date for planned removal of this compatibility route ({LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}).",
        "schema": {"type": "string", "format": "date"},
    },
}


def iter_legacy_route_entries(
    route_entries: tuple[RouteMigrationEntry, ...] = ROUTE_MIGRATION_MATRIX,
) -> tuple[RouteMigrationEntry, ...]:
    return tuple(entry for entry in route_entries if is_temporary_adapter_route(entry))


def build_legacy_route_index(
    route_entries: tuple[RouteMigrationEntry, ...] = ROUTE_MIGRATION_MATRIX,
) -> dict[tuple[str, str], RouteMigrationEntry]:
    index: dict[tuple[str, str], RouteMigrationEntry] = {}

    for entry in iter_legacy_route_entries(route_entries):
        for method in entry["methods"]:
            index[(method, entry["current_path"])] = entry

    return index


def _annotate_legacy_routes_openapi(
    schema: dict[str, Any],
    route_entries: tuple[RouteMigrationEntry, ...],
) -> None:
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return

    for entry in iter_legacy_route_entries(route_entries):
        path_item = paths.get(entry["current_path"])
        if not isinstance(path_item, dict):
            continue

        guidance = entry["notes"] or build_legacy_route_guidance(entry["target_path"])

        for method in entry["methods"]:
            operation = path_item.get(method.lower())
            if not isinstance(operation, dict):
                continue

            description = operation.get("description", "")
            if guidance not in description:
                operation["description"] = f"{description}\n\n{guidance}".strip()

            operation["x-canonical-path"] = entry["target_path"]
            operation["x-deprecation-removal-date"] = LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO
            operation["x-migration-action"] = entry["migration_action"]

            responses = operation.setdefault("responses", {})
            success_status = next(
                (
                    status
                    for status in responses
                    if isinstance(status, str) and status.startswith("2")
                ),
                "200",
            )
            response = responses.setdefault(success_status, {"description": "Successful Response"})
            headers = response.setdefault("headers", {})
            for header_name, header_definition in LEGACY_ROUTE_RESPONSE_HEADERS.items():
                headers.setdefault(header_name, header_definition)


def configure_legacy_route_deprecation(
    app: FastAPI,
    route_entries: tuple[RouteMigrationEntry, ...] = ROUTE_MIGRATION_MATRIX,
) -> None:
    legacy_route_index = build_legacy_route_index(route_entries)

    @app.middleware("http")
    async def add_legacy_route_headers(request: Request, call_next):
        response = await call_next(request)
        route = request.scope.get("route")
        if not isinstance(route, APIRoute):
            return response

        entry = legacy_route_index.get((request.method, route.path))
        if entry is None:
            return response

        response.headers.setdefault("Deprecation", "true")
        response.headers.setdefault("Sunset", LEGACY_ROUTE_SUNSET_HTTP_DATE)
        response.headers.setdefault(
            "Link",
            f"<{entry['target_path']}>; rel=\"{SUCCESSOR_VERSION_REL}\"",
        )
        response.headers.setdefault("X-Canonical-Route", entry["target_path"])
        response.headers.setdefault(
            "X-Deprecated-Route-Removal-Date",
            LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO,
        )
        return response

    def custom_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        _annotate_legacy_routes_openapi(schema, route_entries)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
