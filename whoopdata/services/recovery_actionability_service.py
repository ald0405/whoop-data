from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from whoopdata.analytics.model_manager import model_manager
from whoopdata.analytics.results_loader import results_loader
from whoopdata.analytics.data_prep import get_recovery_with_features
from whoopdata.crud.recovery import get_recoveries
from whoopdata.crud.sleep import get_sleep
from whoopdata.schemas.daily import ScenarioInput
from whoopdata.services.scenario_planner import ScenarioPlanner


def _category_from_score(score: float) -> str:
    """Map a numeric recovery score to the standard traffic-light category.

    Args:
        score: Recovery score on a 0-100 scale.

    Returns:
        ``"green"`` for scores >= 67, ``"yellow"`` for scores >= 34, otherwise ``"red"``.

    Example:
        category = _category_from_score(72.0)
        assert category == "green"
    """
    if score >= 67:
        return "green"
    if score >= 34:
        return "yellow"
    return "red"


def _format_prediction(result: Any) -> dict[str, Any]:
    """Normalize a model prediction object into a serializable response shape.

    Args:
        result: Prediction output object returned by ``ScenarioPlanner._run_prediction``.

    Returns:
        A dictionary containing predicted recovery details used by API responses.

    Example:
        payload = _format_prediction(prediction_result)
        score = payload["predicted_recovery"]
    """
    return {
        "predicted_recovery": float(result.predicted_recovery),
        "recovery_category": str(result.recovery_category).lower(),
        "confidence_interval": tuple(result.confidence_interval),
        "vs_baseline": str(result.vs_baseline),
        "verdict": str(result.verdict),
    }


class RecoveryActionabilityService:
    """Compose recovery actionability snapshots from stored analytics and runtime state."""
    def __init__(self, db: Session):
        """Initialize service dependencies.

        Args:
            db: Active SQLAlchemy session used for recovery/sleep data access.
        """
        self.db = db

    def build_snapshot(self, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a canonical recovery actionability snapshot for UI/chat consumption.

        The snapshot includes current state, baseline prediction, optional
        scenario-adjusted prediction, top recommended adjustment levers, and
        reliability metadata.

        Args:
            scenario: Optional scenario override values for prediction inputs.
                Keys with ``None`` values are ignored.

        Returns:
            A dictionary with recovery actionability fields, including baseline
            and optional scenario predictions.

        Example:
            service = RecoveryActionabilityService(db)
            snapshot = service.build_snapshot({"sleep_hours": 8.5, "strain": 12.0})
            baseline = snapshot["baseline_prediction"]
        """
        stored = results_loader.load_result("recovery_actionability", days_back=365) or {}
        notes = list(stored.get("notes") or [])
        planner = ScenarioPlanner(self.db)

        state = self._current_state()
        baseline_input = {
            "sleep_hours": float(state.get("sleep_hours") or 8.0),
            "sleep_efficiency": self._to_float_or_none(state.get("sleep_efficiency")),
            "strain": self._to_float_or_none(state.get("strain")),
            "hrv": self._to_float_or_none(state.get("hrv")),
            "rhr": self._to_float_or_none(state.get("rhr")),
        }

        model = model_manager.recovery_predictor
        model_available = model is not None
        baseline_prediction = None
        scenario_prediction = None
        reliability_summary = None

        if model_available:
            baseline_prediction = _format_prediction(
                planner._run_prediction(model, ScenarioInput(**baseline_input))
            )
            if scenario:
                merged = {**baseline_input, **{k: v for k, v in scenario.items() if v is not None}}
                scenario_prediction = _format_prediction(
                    planner._run_prediction(model, ScenarioInput(**merged))
                )
            mae = float(getattr(model, "mae", 0.0))
            reliability_summary = f"This estimate is usually within about {mae:.0f} recovery points."
        else:
            notes.append(
                "Prediction model unavailable. Run analytics pipeline to enable scenario forecasts."
            )

        return {
            "version": int(stored.get("version", 1)),
            "computed_at": stored.get("computed_at", datetime.utcnow().isoformat()),
            "days_back": int(stored.get("days_back", 365)),
            "min_group_size": int(stored.get("min_group_size", 25)),
            "rules": stored.get("rules", []),
            "best_thresholds": stored.get("best_thresholds", {}),
            "notes": notes,
            "current_state": state,
            "baseline_prediction": baseline_prediction,
            "scenario_prediction": scenario_prediction,
            "top_adjustments": self._top_adjustments(state, stored.get("best_thresholds") or {}),
            "reliability_summary": reliability_summary,
            "model_available": model_available,
        }

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        """Safely coerce a value to ``float``.

        Args:
            value: Input value that may be numeric, string-like numeric, or ``None``.

        Returns:
            Parsed float value, or ``None`` when coercion fails.
        """
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _current_state(self) -> dict[str, Any]:
        """Collect the latest recovery/sleep-derived state used for actionability.

        Returns:
            Dictionary with normalized current-state features (recovery, sleep,
            strain, HRV, RHR, and bedtime) used by prediction and recommendations.

        Example:
            state = service._current_state()
            print(state["sleep_hours"])
        """
        recoveries = get_recoveries(self.db, skip=0, limit=1)
        sleeps = get_sleep(self.db, skip=0, limit=1)
        recovery_features = get_recovery_with_features(self.db, days_back=30)

        latest_recovery = recoveries[0] if recoveries else None
        latest_sleep = sleeps[0] if sleeps else None
        latest_features = (
            recovery_features.sort_values("created_at").iloc[-1] if len(recovery_features) else None
        )

        sleep_hours = None
        sleep_efficiency = None
        bedtime = None
        if latest_sleep is not None:
            if (
                latest_sleep.total_time_in_bed_time_milli is not None
                and latest_sleep.total_awake_time_milli is not None
            ):
                sleep_hours = (
                    latest_sleep.total_time_in_bed_time_milli - latest_sleep.total_awake_time_milli
                ) / 3_600_000
            sleep_efficiency = latest_sleep.sleep_efficiency_percentage
            if latest_sleep.start:
                bedtime = latest_sleep.start.strftime("%H:%M")

        strain = None
        strain_3d_sum = None
        if latest_features is not None:
            strain = self._to_float_or_none(latest_features.get("strain"))
            strain_3d_sum = self._to_float_or_none(latest_features.get("strain_3d_sum"))

        recovery_score = self._to_float_or_none(
            getattr(latest_recovery, "recovery_score", None) if latest_recovery else None
        )
        return {
            "recovery_score": recovery_score,
            "recovery_category": (
                _category_from_score(recovery_score) if recovery_score is not None else None
            ),
            "sleep_hours": self._to_float_or_none(sleep_hours),
            "sleep_efficiency": self._to_float_or_none(sleep_efficiency),
            "strain": strain,
            "strain_3d_sum": strain_3d_sum,
            "hrv": self._to_float_or_none(
                getattr(latest_recovery, "hrv_rmssd_milli", None) if latest_recovery else None
            ),
            "rhr": self._to_float_or_none(
                getattr(latest_recovery, "resting_heart_rate", None) if latest_recovery else None
            ),
            "bedtime": bedtime,
        }

    def _top_adjustments(self, state: dict[str, Any], best_thresholds: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate ranked, personalized adjustment levers from state and thresholds.

        Args:
            state: Current-state feature values.
            best_thresholds: Stored threshold metadata from analytics artifacts.

        Returns:
            Up to five recommendation dictionaries with current value, target,
            and user-facing recommendation text.
        """
        adjustments: list[dict[str, Any]] = []
        strain_max = self._to_float_or_none(best_thresholds.get("strain_3d_sum_max"))
        if strain_max is not None and state.get("strain_3d_sum") is not None:
            current = float(state["strain_3d_sum"])
            if current > strain_max:
                adjustments.append(
                    {
                        "label": "3-day strain",
                        "current": round(current, 1),
                        "target": round(strain_max, 1),
                        "recommendation": f"Aim to keep recent 3-day strain around {strain_max:.1f} or lower.",
                    }
                )
        sleep_target = self._to_float_or_none(self._best_sleep_hours_threshold())
        if sleep_target is not None and state.get("sleep_hours") is not None:
            current_sleep = float(state["sleep_hours"])
            if current_sleep < sleep_target:
                adjustments.append(
                    {
                        "label": "Sleep opportunity",
                        "current": round(current_sleep, 1),
                        "target": round(sleep_target, 1),
                        "recommendation": f"Add about {max(0.0, sleep_target - current_sleep):.1f}h tonight to reach your typical green-zone target (~{sleep_target:.1f}h).",
                    }
                )

        bedtime_window = self._personalized_bedtime_window()
        if bedtime_window and state.get("bedtime"):
            bedtime_target = f"{bedtime_window['start']}-{bedtime_window['end']}"
            adjustments.append(
                {
                    "label": "Bedtime",
                    "current": state["bedtime"],
                    "target": bedtime_target,
                    "recommendation": f"For you, most green recoveries cluster around {bedtime_target}.",
                }
            )
        if not adjustments:
            adjustments.append(
                {
                    "label": "Consistency",
                    "current": "steady",
                    "target": "steady",
                    "recommendation": "Keep sleep timing and strain load consistent to support green recoveries.",
                }
            )
        return adjustments[:5]

    def _best_sleep_hours_threshold(self) -> float | None:
        """Read the learned sleep-hours threshold from stored actionability rules.

        Returns:
            Best sleep-hours threshold if present in rules, otherwise ``None``.
        """
        stored = results_loader.load_result("recovery_actionability", days_back=365) or {}
        rules = stored.get("rules") or []
        for rule in rules:
            if rule.get("feature") == "sleep_hours":
                return self._to_float_or_none(rule.get("threshold"))
        return None

    def _personalized_bedtime_window(self) -> dict[str, str] | None:
        """Estimate a narrow bedtime window centered on the user's median bedtime.

        Uses recent sleep starts (up to 21 sleeps) and returns a ±15 minute
        window around the median when enough history is available.

        Returns:
            Dictionary with ``start`` and ``end`` times in ``HH:MM`` format, or
            ``None`` when insufficient sleep history exists.
        """
        sleeps = get_sleep(self.db, skip=0, limit=21)
        bedtimes: list[int] = []
        for sleep in sleeps:
            if not getattr(sleep, "start", None):
                continue
            dt = sleep.start
            minute = dt.hour * 60 + dt.minute
            if minute < 12 * 60:
                minute += 24 * 60
            bedtimes.append(minute)
        if len(bedtimes) < 7:
            return None
        bedtimes_sorted = sorted(bedtimes)
        median = bedtimes_sorted[len(bedtimes_sorted) // 2]
        start = median - 15
        end = median + 15
        return {"start": self._format_extended_clock_min(start), "end": self._format_extended_clock_min(end)}

    @staticmethod
    def _format_extended_clock_min(value: int) -> str:
        """Format minute offsets (including >24h values) onto a 24h clock string.

        Args:
            value: Minute offset where values may exceed one day.

        Returns:
            Time formatted as ``HH:MM`` after modulo 24 hours.

        Example:
            assert RecoveryActionabilityService._format_extended_clock_min(1500) == "01:00"
        """
        minute = value % (24 * 60)
        hh = minute // 60
        mm = minute % 60
        return f"{hh:02d}:{mm:02d}"
