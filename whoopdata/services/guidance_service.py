"""Reusable orchestration service for daily guidance, scenarios, and reports."""

from __future__ import annotations

from sqlalchemy.orm import Session

from whoopdata.analytics.engine import InsightGenerator
from whoopdata.schemas.daily import (
    CompareResponse,
    DailyPlanResponse,
    ScenarioInput,
    ScenarioResponse,
)
from whoopdata.services.daily_engine import DailyEngine
from whoopdata.services.insight_context_service import DEFAULT_LOCATION, InsightContextService
from whoopdata.services.scenario_planner import ScenarioPlanner


class GuidanceService:
    """Compose the guidance-oriented insight flows outside the router layer."""

    def __init__(
        self,
        db: Session,
        context_service: InsightContextService | None = None,
    ):
        self.db = db
        self.context_service = context_service or InsightContextService()

    async def build_daily_plan(self, location: str = DEFAULT_LOCATION) -> DailyPlanResponse:
        """Build the daily action card with shared environmental context."""
        weather_data = None
        transport_data = None
        tide_data = None

        try:
            weather_data = self.context_service.get_weather_summary(location)
        except Exception:
            weather_data = None

        try:
            transport_data = self.context_service.get_transport_status()
        except Exception:
            transport_data = None

        try:
            tide_data = await self.context_service.get_tide_summary()
        except Exception:
            tide_data = None

        engine = DailyEngine(self.db)
        return engine.generate_daily_plan(
            weather_data=weather_data,
            transport_data=transport_data,
            tide_data=tide_data,
        )

    def predict_scenario(self, scenario: ScenarioInput) -> ScenarioResponse:
        """Predict a single hypothetical recovery scenario."""
        planner = ScenarioPlanner(self.db)
        return planner.predict_scenario(scenario)

    def compare_scenarios(self, scenarios: list[ScenarioInput]) -> CompareResponse:
        """Compare multiple hypothetical recovery scenarios."""
        planner = ScenarioPlanner(self.db)
        return planner.compare_scenarios(scenarios)

    def get_weekly_coaching_report(self, weeks: int = 1) -> dict:
        """Generate the structured weekly coaching report."""
        generator = InsightGenerator(self.db)
        return generator.generate_coaching_report(weeks=weeks)
