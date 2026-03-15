"""Reusable dashboard insight composition service."""

from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from whoopdata.crud.recovery import get_recoveries
from whoopdata.crud.sleep import get_sleep
from whoopdata.crud.workout import get_recoveries as get_workouts
from whoopdata.models.models import WithingsWeight
from whoopdata.services.health_metrics_service import get_all_health_metrics
from whoopdata.services.insight_context_service import DEFAULT_LOCATION, InsightContextService


def calculate_avg(values: list[float]) -> float | None:
    """Calculate average, returning None if the list is empty."""
    return round(mean(values), 2) if values else None


class DashboardService:
    """Compose dashboard-oriented insight payloads outside the router layer."""

    def __init__(
        self,
        db: Session | None,
        context_service: InsightContextService | None = None,
    ):
        self.db = db
        self.context_service = context_service or InsightContextService()

    async def build_daily_dashboard(self, location: str = DEFAULT_LOCATION) -> dict[str, Any]:
        """Build the daily dashboard insight response."""
        dashboard_data: dict[str, Any] = {
            "health_metrics": self._build_dashboard_health_metrics(),
            "context": {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        try:
            dashboard_data["context"]["weather"] = self.context_service.get_weather_summary(location)
        except Exception as e:
            dashboard_data["context"]["weather"] = {"error": str(e)}

        try:
            dashboard_data["context"]["transport"] = self.context_service.get_transport_status()
        except Exception as e:
            dashboard_data["context"]["transport"] = {"error": str(e)}

        try:
            dashboard_data["context"]["tide"] = await self.context_service.get_dashboard_tide_context()
        except Exception as e:
            dashboard_data["context"]["tide"] = {"error": str(e)}

        try:
            dashboard_data["context"]["walk_hotspots"] = await self.context_service.get_walk_hotspots(
                days=5
            )
        except Exception as e:
            dashboard_data["context"]["walk_hotspots"] = {"error": str(e)}

        return dashboard_data

    def get_health_metrics(self) -> dict[str, Any]:
        """Return the standardized health metrics insight payload."""
        return get_all_health_metrics(self.db)

    def get_extended_weather(self, location: str = DEFAULT_LOCATION) -> dict[str, Any]:
        """Return the extended weather insight payload."""
        return self.context_service.get_extended_weather(location)

    def _build_dashboard_health_metrics(self) -> dict[str, Any]:
        return {
            "recovery": self._build_recovery_metrics(),
            "sleep": self._build_sleep_metrics(),
            "strain": self._build_strain_metrics(),
            "weight": self._build_weight_metrics(),
        }

    def _build_recovery_metrics(self) -> dict[str, Any]:
        try:
            recoveries = get_recoveries(self.db, skip=0, limit=7)
            if not recoveries:
                return {
                    "last_7_days": [],
                    "avg_7_days": None,
                    "latest": None,
                }

            recovery_scores = [
                recovery.recovery_score
                for recovery in recoveries
                if recovery.recovery_score is not None
            ]
            return {
                "last_7_days": recovery_scores,
                "avg_7_days": calculate_avg(recovery_scores),
                "latest": recovery_scores[0] if recovery_scores else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_sleep_metrics(self) -> dict[str, Any]:
        try:
            sleeps = get_sleep(self.db, skip=0, limit=7)
            if not sleeps:
                return {
                    "hours_slept_last_7_days": [],
                    "avg_hours_7_days": None,
                    "latest_bedtime": None,
                    "time_in_bed_last_7_days": [],
                    "avg_time_in_bed_7_days": None,
                }

            hours_slept = [
                round((sleep.total_time_in_bed_time_milli - sleep.total_awake_time_milli) / 3600000, 2)
                for sleep in sleeps
                if sleep.total_time_in_bed_time_milli is not None
                and sleep.total_awake_time_milli is not None
            ]
            time_in_bed = [
                round(sleep.total_time_in_bed_time_milli / 3600000, 2)
                for sleep in sleeps
                if sleep.total_time_in_bed_time_milli is not None
            ]
            latest_bedtime = sleeps[0].start.strftime("%H:%M") if sleeps[0].start else None

            return {
                "hours_slept_last_7_days": hours_slept,
                "avg_hours_7_days": calculate_avg(hours_slept),
                "latest_bedtime": latest_bedtime,
                "time_in_bed_last_7_days": time_in_bed,
                "avg_time_in_bed_7_days": calculate_avg(time_in_bed),
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_strain_metrics(self) -> dict[str, Any]:
        try:
            workouts = get_workouts(self.db, skip=0, limit=7)
            if not workouts:
                return {"last_7_days": [], "avg_7_days": None}

            strain_scores = [workout.strain for workout in workouts if workout.strain is not None]
            return {
                "last_7_days": strain_scores,
                "avg_7_days": calculate_avg(strain_scores),
            }
        except Exception as e:
            return {"error": str(e)}

    def _build_weight_metrics(self) -> dict[str, Any]:
        try:
            weights = (
                self.db.query(WithingsWeight)
                .order_by(WithingsWeight.datetime.desc())
                .limit(8)
                .all()
            )
            if not weights:
                return {"latest": None, "change_7_days": None}

            latest_weight = weights[0].weight_kg
            weight_change = None
            if len(weights) >= 8:
                week_ago_weight = weights[7].weight_kg
                weight_change = round(latest_weight - week_ago_weight, 1)

            return {
                "latest": round(latest_weight, 1) if latest_weight else None,
                "change_7_days": weight_change,
            }
        except Exception as e:
            return {"error": str(e)}
