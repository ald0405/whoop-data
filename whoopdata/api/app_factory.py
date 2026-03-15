from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from whoopdata.__version__ import __version__
from whoopdata.api.legacy_route_deprecation import configure_legacy_route_deprecation
from whoopdata.api.analytics_routes import (
    insights_router as analytics_insights_router,
    legacy_insights_router as analytics_legacy_insights_router,
)
from whoopdata.api.agent_routes import router as agent_router
from whoopdata.api.daily_routes import (
    insights_router as daily_insights_router,
    legacy_insights_router as daily_legacy_insights_router,
)
from whoopdata.api.dashboard_page_routes import router as dashboard_page_router
from whoopdata.api.dashboard_routes import (
    insights_router as dashboard_insights_router,
    legacy_insights_router as dashboard_legacy_insights_router,
)
from whoopdata.api.public_surface_contract import (
    CanonicalSurface,
    PUBLIC_SURFACE_CONTRACT,
    SURFACE_ORDER,
)
from whoopdata.api.recovery_routes import (
    data_router as recovery_data_router,
    insights_router as recovery_insights_router,
    legacy_data_router as recovery_legacy_data_router,
    legacy_insights_router as recovery_legacy_insights_router,
)
from whoopdata.api.sleep_routes import (
    data_router as sleep_data_router,
    legacy_data_router as sleep_legacy_data_router,
)
from whoopdata.api.tide_routes import (
    data_router as tide_data_router,
    insights_router as tide_insights_router,
    legacy_data_router as tide_legacy_data_router,
    legacy_insights_router as tide_legacy_insights_router,
)
from whoopdata.api.transport_routes import (
    data_router as transport_data_router,
    legacy_data_router as transport_legacy_data_router,
)
from whoopdata.api.weather_routes import (
    data_router as weather_data_router,
    legacy_data_router as weather_legacy_data_router,
)
from whoopdata.api.web_routes import router as web_router
from whoopdata.api.withings_routes import (
    data_router as withings_data_router,
    insights_router as withings_insights_router,
    legacy_data_router as withings_legacy_data_router,
    legacy_insights_router as withings_legacy_insights_router,
)
from whoopdata.api.withings_status_routes import (
    data_router as withings_status_data_router,
    legacy_data_router as withings_status_legacy_data_router,
)
from whoopdata.api.workout_routes import (
    data_router as workout_data_router,
    insights_router as workout_insights_router,
    legacy_data_router as workout_legacy_data_router,
    legacy_insights_router as workout_legacy_insights_router,
)


WEB_ROUTERS: tuple[APIRouter, ...] = (
    web_router,
    dashboard_page_router,
)

CANONICAL_DATA_ROUTERS: tuple[APIRouter, ...] = (
    recovery_data_router,
    workout_data_router,
    sleep_data_router,
    withings_data_router,
    withings_status_data_router,
    weather_data_router,
    transport_data_router,
    tide_data_router,
)

LEGACY_DATA_ROUTERS: tuple[APIRouter, ...] = (
    recovery_legacy_data_router,
    workout_legacy_data_router,
    sleep_legacy_data_router,
    withings_legacy_data_router,
    withings_status_legacy_data_router,
    weather_legacy_data_router,
    transport_legacy_data_router,
    tide_legacy_data_router,
)

DATA_ROUTERS: tuple[APIRouter, ...] = CANONICAL_DATA_ROUTERS + LEGACY_DATA_ROUTERS

CANONICAL_INSIGHT_ROUTERS: tuple[APIRouter, ...] = (
    recovery_insights_router,
    workout_insights_router,
    withings_insights_router,
    dashboard_insights_router,
    analytics_insights_router,
    tide_insights_router,
    daily_insights_router,
)

LEGACY_INSIGHT_ROUTERS: tuple[APIRouter, ...] = (
    recovery_legacy_insights_router,
    workout_legacy_insights_router,
    withings_legacy_insights_router,
    dashboard_legacy_insights_router,
    analytics_legacy_insights_router,
    tide_legacy_insights_router,
    daily_legacy_insights_router,
)

INSIGHT_ROUTERS: tuple[APIRouter, ...] = CANONICAL_INSIGHT_ROUTERS + LEGACY_INSIGHT_ROUTERS

AGENT_ROUTERS: tuple[APIRouter, ...] = (agent_router,)
ROUTER_REGISTRATION_ORDER: tuple[CanonicalSurface, ...] = ("web", "data", "insights", "agent")

ROUTER_GROUPS: dict[CanonicalSurface, tuple[APIRouter, ...]] = {
    "data": DATA_ROUTERS,
    "insights": INSIGHT_ROUTERS,
    "agent": AGENT_ROUTERS,
    "web": WEB_ROUTERS,
}

def _build_openapi_tag_metadata() -> list[dict[str, str]]:
    tag_metadata: list[dict[str, str]] = []

    for surface in SURFACE_ORDER:
        definition = PUBLIC_SURFACE_CONTRACT[surface]
        if definition.openapi_tag is None:
            continue

        description_lines = [
            definition.summary,
            "",
            "Ownership rules:",
            *(f"- {rule}" for rule in definition.ownership_rules),
            "",
            "Examples:",
            *(f"- `{example}`" for example in definition.examples),
        ]
        tag_metadata.append(
            {
                "name": definition.openapi_tag,
                "description": "\n".join(description_lines),
            }
        )

    return tag_metadata


OPENAPI_TAG_METADATA = _build_openapi_tag_metadata()


def _configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # <-- for dev, allow everything
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _mount_static_files(app: FastAPI) -> None:
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        # Directory doesn't exist yet, we'll create it
        pass


def _include_surface_routers(app: FastAPI) -> None:
    for surface in ROUTER_REGISTRATION_ORDER:
        for router in ROUTER_GROUPS[surface]:
            app.include_router(router)


def create_app() -> FastAPI:
    app = FastAPI(
        title="WHOOP Health Data Platform",
        description=(
            "A health data platform with canonical public surfaces for raw data "
            "(`/api/v1/data/*`), interpreted outputs (`/api/v1/insights/*`), and "
            "conversational requests (`/api/v1/agent/*`). Top-level web pages remain "
            "outside the API namespaces."
        ),
        version=__version__,
        openapi_tags=OPENAPI_TAG_METADATA,
    )

    _configure_cors(app)
    _mount_static_files(app)
    _include_surface_routers(app)
    configure_legacy_route_deprecation(app)
    return app
