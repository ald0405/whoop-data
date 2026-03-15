"""Canonical public surface contract for API, agent, and web ownership."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


CanonicalSurface = Literal["data", "insights", "agent", "web"]
RouteKind = Literal["api", "page"]
RouteRole = Literal[
    "resource",
    "derived_output",
    "legacy_alias",
    "integration_status",
    "web_page",
    "conversation",
]
EntrypointSurface = Literal["agent", "data", "insights", "mixed", "web"]
EntrypointRole = Literal[
    "api_server",
    "analytics_job",
    "chat_ui",
    "combined_launcher",
    "etl",
    "graph_dev",
    "provider_auth",
]


LEGACY_COMPATIBILITY_REMOVAL_DATE = date(2026, 9, 30)
LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO = LEGACY_COMPATIBILITY_REMOVAL_DATE.isoformat()


def build_legacy_route_guidance(target_path: str) -> str:
    return (
        "Deprecated compatibility route. "
        f"Use `{target_path}` instead. "
        f"Temporary compatibility window ends on {LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}; "
        f"planned removal after {LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}."
    )


@dataclass(frozen=True)
class PublicSurfaceDefinition:
    surface: CanonicalSurface
    namespace_prefix: str | None
    openapi_tag: str | None
    route_kind: RouteKind
    summary: str
    ownership_rules: tuple[str, ...]
    examples: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityPlacementRule:
    capability: str
    surface: CanonicalSurface
    rule: str
    examples: tuple[str, ...]


SURFACE_ORDER: tuple[CanonicalSurface, ...] = ("data", "insights", "agent", "web")


PUBLIC_SURFACE_CONTRACT: dict[CanonicalSurface, PublicSurfaceDefinition] = {
    "data": PublicSurfaceDefinition(
        surface="data",
        namespace_prefix="/api/v1/data",
        openapi_tag="data",
        route_kind="api",
        summary="Raw health records, context resources, and provider/integration status.",
        ownership_rules=(
            "Expose direct resources and provider state without interpreted recommendations.",
            "Use this surface for fetch/filter/latest/top style access patterns over stored or proxied records.",
            f"Compatibility aliases may exist temporarily during migration, but the canonical namespace remains /api/v1/data/* and legacy adapters are scheduled for removal after {LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}.",
        ),
        examples=(
            "/api/v1/data/recovery",
            "/api/v1/data/withings/weight",
            "/api/v1/data/weather/current",
        ),
    ),
    "insights": PublicSurfaceDefinition(
        surface="insights",
        namespace_prefix="/api/v1/insights",
        openapi_tag="insights",
        route_kind="api",
        summary="Derived, aggregated, predictive, or workflow-produced outputs.",
        ownership_rules=(
            "Use this surface for analytics, dashboards JSON, daily plans, scenarios, reports, and other interpreted outputs.",
            "Deterministic workflows stay here rather than being routed through the conversational supervisor.",
            f"The canonical namespace for interpreted outputs is /api/v1/insights/*, and temporary legacy adapters are scheduled for removal after {LEGACY_COMPATIBILITY_REMOVAL_DATE_ISO}.",
        ),
        examples=(
            "/api/v1/insights/dashboard/daily",
            "/api/v1/insights/analytics/summary",
            "/api/v1/insights/reports/weekly",
        ),
    ),
    "agent": PublicSurfaceDefinition(
        surface="agent",
        namespace_prefix="/api/v1/agent",
        openapi_tag="agent",
        route_kind="api",
        summary="Stable product API for conversational and coaching requests.",
        ownership_rules=(
            "Expose one public assistant persona rather than specialist-specific public endpoints.",
            "Own thread/session IDs, checkpoint-backed short-term memory, and response shaping at this boundary.",
            "Treat specialist agents and raw LangGraph concepts as internal implementation details by default.",
        ),
        examples=(
            "/api/v1/agent/conversations",
            "/api/v1/agent/messages",
        ),
    ),
    "web": PublicSurfaceDefinition(
        surface="web",
        namespace_prefix=None,
        openapi_tag=None,
        route_kind="page",
        summary="Human-facing page routes that consume the API surfaces above.",
        ownership_rules=(
            "Keep web routes as page shells only; data and behavior should come from data, insights, or agent APIs.",
            "Do not create new JSON product surfaces under web page paths.",
            "Keep dashboard, analytics, and report as web routes, not mixed API namespaces.",
        ),
        examples=(
            "/dashboard",
            "/analytics",
            "/report",
        ),
    ),
}


SURFACE_ROUTE_ROLE_RULES: dict[CanonicalSurface, frozenset[RouteRole]] = {
    "data": frozenset({"resource", "legacy_alias", "integration_status"}),
    "insights": frozenset({"derived_output", "legacy_alias"}),
    "agent": frozenset({"conversation"}),
    "web": frozenset({"web_page"}),
}


ENTRYPOINT_SURFACE_RULES: dict[EntrypointRole, frozenset[EntrypointSurface]] = {
    "api_server": frozenset({"mixed"}),
    "analytics_job": frozenset({"insights"}),
    "chat_ui": frozenset({"agent"}),
    "combined_launcher": frozenset({"mixed"}),
    "etl": frozenset({"data"}),
    "graph_dev": frozenset({"agent"}),
    "provider_auth": frozenset({"data"}),
}


CAPABILITY_PLACEMENT_RULES: tuple[CapabilityPlacementRule, ...] = (
    CapabilityPlacementRule(
        capability="Raw health and context resources",
        surface="data",
        rule="Place fetchable record/resource endpoints under /api/v1/data/*.",
        examples=(
            "/api/v1/data/recovery",
            "/api/v1/data/workouts",
            "/api/v1/data/transport/status",
        ),
    ),
    CapabilityPlacementRule(
        capability="Derived analytics and workflow outputs",
        surface="insights",
        rule="Place interpreted aggregates, predictions, plans, reports, and similar outputs under /api/v1/insights/*.",
        examples=(
            "/api/v1/insights/dashboard/daily",
            "/api/v1/insights/scenarios/recovery",
            "/api/v1/insights/analytics/recovery/factors",
        ),
    ),
    CapabilityPlacementRule(
        capability="Conversational/coaching requests",
        surface="agent",
        rule="Place assistant-facing conversation APIs under /api/v1/agent/* and keep specialist delegation internal.",
        examples=(
            "/api/v1/agent/conversations",
            "/api/v1/agent/messages",
        ),
    ),
    CapabilityPlacementRule(
        capability="Human-facing page shells",
        surface="web",
        rule="Keep HTML routes outside /api/v1/* and back them with API surfaces instead of embedded business logic.",
        examples=(
            "/dashboard",
            "/analytics",
            "/report",
        ),
    ),
)


AGENT_SURFACE_GUARDRAILS: tuple[str, ...] = (
    "One public assistant persona is the only conversational entrypoint.",
    "Specialists remain internal sub-agents wrapped as tools by default.",
    "The conversation boundary owns thread/session IDs and checkpoint-backed short-term memory.",
    "Deterministic dashboard, daily plan, scenario, and report flows stay outside the conversational supervisor unless explicit graph state or review is needed.",
    "The public agent API is a product surface, not a thin wrapper over raw LangGraph server concepts.",
)


def get_surface_definition(surface: CanonicalSurface) -> PublicSurfaceDefinition:
    return PUBLIC_SURFACE_CONTRACT[surface]


def surface_accepts_target(surface: CanonicalSurface, target_path: str) -> bool:
    definition = get_surface_definition(surface)

    if definition.namespace_prefix is None:
        return target_path.startswith("/") and not target_path.startswith("/api/v1/")

    prefix = definition.namespace_prefix
    return target_path == prefix or target_path.startswith(f"{prefix}/")


def surface_allows_route_kind(surface: CanonicalSurface, route_kind: RouteKind) -> bool:
    return get_surface_definition(surface).route_kind == route_kind


def surface_allows_route_role(surface: CanonicalSurface, route_role: RouteRole) -> bool:
    return route_role in SURFACE_ROUTE_ROLE_RULES[surface]


def surface_allows_entrypoint_role(
    primary_surface: EntrypointSurface,
    entrypoint_role: EntrypointRole,
) -> bool:
    return primary_surface in ENTRYPOINT_SURFACE_RULES[entrypoint_role]
