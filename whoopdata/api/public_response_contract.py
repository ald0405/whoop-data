"""Canonical response contract definitions by public surface."""

from __future__ import annotations

from dataclasses import dataclass

from whoopdata.api.public_surface_contract import CanonicalSurface


@dataclass(frozen=True)
class SurfaceResponseContract:
    surface: CanonicalSurface
    summary: str
    primary_shapes: tuple[str, ...]
    invariants: tuple[str, ...]
    examples: tuple[str, ...]


PUBLIC_RESPONSE_CONTRACT: dict[CanonicalSurface, SurfaceResponseContract] = {
    "data": SurfaceResponseContract(
        surface="data",
        summary="Record-oriented responses that expose raw resources without interpreted recommendations.",
        primary_shapes=(
            "single resource record",
            "collection of resource records",
            "integration status object",
        ),
        invariants=(
            "Canonical data routes return raw domain records or provider-status objects rather than interpreted narratives.",
            "List-style queries may return record collections, while latest/top/status-style queries may return a single object.",
            "The contract is expressed through domain schemas in whoopdata.schemas.* and legacy-deprecation headers rather than a new JSON envelope.",
        ),
        examples=(
            "Recovery",
            "Workouts",
            "SleepSchema",
        ),
    ),
    "insights": SurfaceResponseContract(
        surface="insights",
        summary="Interpreted, aggregate, predictive, or workflow-produced responses.",
        primary_shapes=(
            "analytics summary",
            "factor analysis or correlation payload",
            "daily planning / scenario / report result",
        ),
        invariants=(
            "Insight routes return derived outputs, not raw ORM-style record collections.",
            "Responses should use explicit aggregate/prediction schemas when available and keep narrative explanations inside the payload.",
            "The contract is keyed to interpreted outputs such as analytics, dashboards JSON, plans, scenarios, and reports.",
        ),
        examples=(
            "AnalyticsSummaryResponse",
            "DailyPlanResponse",
            "ScenarioResponse",
        ),
    ),
    "agent": SurfaceResponseContract(
        surface="agent",
        summary="Stable conversational payloads that hide raw LangGraph state and preserve thread continuity.",
        primary_shapes=(
            "conversation turn response",
            "assistant message with artifacts",
        ),
        invariants=(
            "Public agent responses expose assistant-facing message content instead of raw graph state dictionaries.",
            "Thread continuity is represented by thread_id, with optional session_id when a client needs higher-level session grouping.",
            "Artifacts such as generated code or images are attached as typed outputs rather than leaked tool-call internals.",
        ),
        examples=(
            "AgentConversationResponse",
            "AgentArtifact",
        ),
    ),
    "web": SurfaceResponseContract(
        surface="web",
        summary="HTML page shells that consume the API surfaces rather than defining an API response contract of their own.",
        primary_shapes=(
            "server-rendered HTML page",
        ),
        invariants=(
            "Web routes remain page shells and should not become parallel JSON product surfaces.",
            "Page code may compose multiple data and insight contracts, but the page itself is not part of the API response surface.",
        ),
        examples=(
            "/dashboard",
            "/analytics",
            "/report",
        ),
    ),
}


def get_response_contract(surface: CanonicalSurface) -> SurfaceResponseContract:
    return PUBLIC_RESPONSE_CONTRACT[surface]
