"""Daily decision engine.

Produces personalised daily action cards by combining:
- Latest recovery/sleep/HRV data
- ML predictions and factor importance
- Weather and transport context
- Historical patterns and baselines
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
from statistics import mean

from sqlalchemy.orm import Session

from whoopdata.crud.recovery import get_recoveries
from whoopdata.crud.sleep import get_sleep
from whoopdata.analytics.model_manager import model_manager
from whoopdata.analytics.data_prep import get_recovery_with_features
from whoopdata.analytics.results_loader import results_loader
from whoopdata.schemas.daily import (
    DailyPlanResponse,
    RecoveryStatus,
    DailyAction,
    SleepTarget,
    ContextSummary,
)

logger = logging.getLogger(__name__)


class DailyEngine:
    """Generates personalised daily action cards."""

    def __init__(self, db: Session):
        self.db = db

    def generate_daily_plan(
        self,
        weather_data: Optional[Dict] = None,
        transport_data: Optional[Dict] = None,
        tide_data: Optional[Dict] = None,
    ) -> DailyPlanResponse:
        """Generate a complete daily action card.

        Args:
            weather_data: Pre-fetched weather data (optional)
            transport_data: Pre-fetched transport data (optional)
            tide_data: Pre-fetched tide data (optional)

        Returns:
            DailyPlanResponse with recovery status, actions, sleep target, context
        """
        # Gather all data
        recovery_status = self._build_recovery_status()
        baselines = self._compute_baselines()
        factor_insights = self._get_top_recovery_drivers()
        sleep_patterns = self._analyze_sleep_patterns()

        # Generate actions based on current state
        actions = self._generate_actions(
            recovery_status, baselines, factor_insights, sleep_patterns, weather_data
        )

        # Build sleep target from historical patterns
        sleep_target = self._build_sleep_target(sleep_patterns, baselines)

        # Build context summary
        context = self._build_context(weather_data, transport_data, tide_data)

        return DailyPlanResponse(
            recovery_status=recovery_status,
            actions=actions,
            sleep_target=sleep_target,
            context=context,
            generated_at=datetime.utcnow(),
        )

    # =================== Recovery Status ===================

    def _build_recovery_status(self) -> RecoveryStatus:
        """Build current recovery status from latest data."""
        recoveries = get_recoveries(self.db, skip=0, limit=1)

        if not recoveries:
            return RecoveryStatus(
                score=0,
                category="red",
                key_driver="No recovery data available",
            )

        latest = recoveries[0]
        score = latest.recovery_score or 0

        # Category
        if score >= 67:
            category = "green"
        elif score >= 34:
            category = "yellow"
        else:
            category = "red"

        # Compare to baseline
        baselines = self._compute_baselines()
        vs_baseline = None
        if baselines.get("recovery_28d"):
            diff = score - baselines["recovery_28d"]
            if abs(diff) >= 1:
                sign = "+" if diff > 0 else ""
                vs_baseline = f"{sign}{diff:.0f}% vs your 28-day average"

        # Top recovery driver
        key_driver = self._get_key_driver_text()

        return RecoveryStatus(
            score=score,
            category=category,
            hrv=latest.hrv_rmssd_milli,
            resting_heart_rate=latest.resting_heart_rate,
            key_driver=key_driver,
            vs_baseline=vs_baseline,
        )

    def _get_key_driver_text(self) -> str:
        """Get plain-English text about the user's top recovery driver."""
        result = results_loader.load_result("factor_importance", days_back=365)
        if not result or "factors" not in result:
            return "Run the analytics pipeline to identify your recovery drivers"

        factors = result["factors"]
        if not factors:
            return "Recovery drivers not yet computed"

        top = factors[0]
        name = top.get("factor_name", "Unknown factor")
        pct = top.get("importance_percentage", 0)
        return f"{name} is your top recovery driver ({pct:.0f}% importance)"

    # =================== Baselines ===================

    def _compute_baselines(self) -> Dict:
        """Compute 7d and 28d baselines for key metrics."""
        recoveries_7d = get_recoveries(self.db, skip=0, limit=7)
        recoveries_28d = get_recoveries(self.db, skip=0, limit=28)
        sleeps_7d = get_sleep(self.db, skip=0, limit=7)
        sleeps_28d = get_sleep(self.db, skip=0, limit=28)

        baselines = {}

        # Recovery baselines
        scores_7d = [r.recovery_score for r in recoveries_7d if r.recovery_score is not None]
        scores_28d = [r.recovery_score for r in recoveries_28d if r.recovery_score is not None]
        baselines["recovery_7d"] = mean(scores_7d) if scores_7d else None
        baselines["recovery_28d"] = mean(scores_28d) if scores_28d else None

        # HRV baselines
        hrv_7d = [r.hrv_rmssd_milli for r in recoveries_7d if r.hrv_rmssd_milli is not None]
        hrv_28d = [r.hrv_rmssd_milli for r in recoveries_28d if r.hrv_rmssd_milli is not None]
        baselines["hrv_7d"] = mean(hrv_7d) if hrv_7d else None
        baselines["hrv_28d"] = mean(hrv_28d) if hrv_28d else None

        # Sleep baselines
        def sleep_hours(s):
            if s.total_time_in_bed_time_milli and s.total_awake_time_milli:
                return (s.total_time_in_bed_time_milli - s.total_awake_time_milli) / 3600000
            return None

        hours_7d = [h for h in (sleep_hours(s) for s in sleeps_7d) if h is not None]
        hours_28d = [h for h in (sleep_hours(s) for s in sleeps_28d) if h is not None]
        baselines["sleep_hours_7d"] = mean(hours_7d) if hours_7d else None
        baselines["sleep_hours_28d"] = mean(hours_28d) if hours_28d else None

        # Sleep efficiency baselines
        eff_7d = [s.sleep_efficiency_percentage for s in sleeps_7d if s.sleep_efficiency_percentage]
        baselines["sleep_efficiency_7d"] = mean(eff_7d) if eff_7d else None

        return baselines

    # =================== Factor Analysis ===================

    def _get_top_recovery_drivers(self) -> List[Dict]:
        """Get top 3 recovery factors from pre-computed analytics."""
        result = results_loader.load_result("factor_importance", days_back=365)
        if not result or "factors" not in result:
            return []
        return result["factors"][:3]

    # =================== Sleep Patterns ===================

    def _analyze_sleep_patterns(self) -> Dict:
        """Analyse historical sleep patterns to find optimal targets."""
        df = get_recovery_with_features(self.db, days_back=90)

        if len(df) < 14:
            return {
                "optimal_sleep_hours": 8.0,
                "optimal_bedtime_hour": 22,
                "optimal_efficiency": 85.0,
            }

        # Find sleep hours that produce best recoveries
        top_quartile = df.nlargest(int(len(df) * 0.25), "recovery_score")

        optimal_hours = top_quartile["sleep_hours"].median()
        optimal_efficiency = top_quartile["sleep_efficiency_percentage"].median()

        # Optimal bedtime from top recoveries
        optimal_bedtime = None
        if "bedtime_hour" in top_quartile.columns:
            bedtime_vals = top_quartile["bedtime_hour"].dropna()
            if len(bedtime_vals) > 0:
                optimal_bedtime = int(bedtime_vals.median())

        # Latest bedtime for comparison
        latest_bedtime = None
        sleeps = get_sleep(self.db, skip=0, limit=1)
        if sleeps and sleeps[0].start:
            latest_bedtime = sleeps[0].start.strftime("%H:%M")

        return {
            "optimal_sleep_hours": round(optimal_hours, 1) if optimal_hours else 8.0,
            "optimal_bedtime_hour": optimal_bedtime or 22,
            "optimal_efficiency": round(optimal_efficiency, 1) if optimal_efficiency else 85.0,
            "latest_bedtime": latest_bedtime,
        }

    # =================== Action Generation ===================

    def _generate_actions(
        self,
        recovery: RecoveryStatus,
        baselines: Dict,
        factors: List[Dict],
        sleep_patterns: Dict,
        weather_data: Optional[Dict] = None,
    ) -> List[DailyAction]:
        """Generate prioritised daily actions based on current state."""
        actions = []
        priority = 1

        # Training action based on recovery category
        training_action = self._training_action(recovery, baselines, priority)
        if training_action:
            actions.append(training_action)
            priority += 1

        # Sleep action if recent sleep was suboptimal
        sleep_action = self._sleep_action(recovery, baselines, sleep_patterns, priority)
        if sleep_action:
            actions.append(sleep_action)
            priority += 1

        # HRV-based recovery action
        hrv_action = self._hrv_action(recovery, baselines, priority)
        if hrv_action:
            actions.append(hrv_action)
            priority += 1

        # Factor-driven action from top recovery drivers
        factor_action = self._factor_driven_action(factors, baselines, priority)
        if factor_action:
            actions.append(factor_action)
            priority += 1

        # Weather-informed action
        if weather_data:
            weather_action = self._weather_action(weather_data, recovery, priority)
            if weather_action:
                actions.append(weather_action)

        # Ensure we always return at least one action
        if not actions:
            actions.append(
                DailyAction(
                    action="Stay consistent with your routine",
                    reasoning="Consistency is the foundation of good recovery patterns",
                    category="lifestyle",
                    priority=1,
                )
            )

        return actions[:5]  # Cap at 5 actions

    def _training_action(
        self, recovery: RecoveryStatus, baselines: Dict, priority: int
    ) -> Optional[DailyAction]:
        """Generate training recommendation based on recovery state."""
        if recovery.category == "green":
            return DailyAction(
                action="Push your training today — your body is ready",
                reasoning=f"Recovery is {recovery.score:.0f}% (green). "
                f"This is a high-capacity day.",
                category="training",
                priority=priority,
            )
        elif recovery.category == "yellow":
            return DailyAction(
                action="Moderate training only — technique work or easy cardio",
                reasoning=f"Recovery is {recovery.score:.0f}% (yellow). "
                f"Save high-intensity sessions for green days.",
                category="training",
                priority=priority,
            )
        else:
            return DailyAction(
                action="Active recovery only — walk, stretch, or rest",
                reasoning=f"Recovery is {recovery.score:.0f}% (red). "
                f"Training hard today will dig a deeper hole.",
                category="recovery",
                priority=priority,
            )

    def _sleep_action(
        self,
        recovery: RecoveryStatus,
        baselines: Dict,
        sleep_patterns: Dict,
        priority: int,
    ) -> Optional[DailyAction]:
        """Generate sleep-related action if sleep is a concern."""
        optimal = sleep_patterns.get("optimal_sleep_hours", 8.0)
        avg_sleep = baselines.get("sleep_hours_7d")

        if avg_sleep and avg_sleep < optimal - 0.5:
            deficit = optimal - avg_sleep
            return DailyAction(
                action=f"Aim for {optimal:.0f}+ hours sleep tonight",
                reasoning=f"You've averaged {avg_sleep:.1f}h this week — "
                f"{deficit:.1f}h below your optimal of {optimal:.1f}h.",
                category="sleep",
                priority=priority,
            )

        if recovery.category == "red":
            return DailyAction(
                action="Prioritise an early bedtime tonight",
                reasoning="Your recovery needs a reset. Earlier sleep gives more deep and REM sleep.",
                category="sleep",
                priority=priority,
            )

        return None

    def _hrv_action(
        self, recovery: RecoveryStatus, baselines: Dict, priority: int
    ) -> Optional[DailyAction]:
        """Generate action based on HRV trends."""
        if recovery.hrv is None or baselines.get("hrv_7d") is None:
            return None

        hrv_diff_pct = ((recovery.hrv - baselines["hrv_7d"]) / baselines["hrv_7d"]) * 100

        if hrv_diff_pct > 10:
            return DailyAction(
                action="Your nervous system is primed — great day for a challenge",
                reasoning=f"HRV is {recovery.hrv:.0f}ms, {hrv_diff_pct:.0f}% above your 7-day average. "
                f"Your autonomic nervous system is ready for stress.",
                category="training",
                priority=priority,
            )
        elif hrv_diff_pct < -15:
            return DailyAction(
                action="Take it easy — your body is signalling fatigue",
                reasoning=f"HRV is {recovery.hrv:.0f}ms, {abs(hrv_diff_pct):.0f}% below your 7-day average. "
                f"This typically means accumulated stress or under-recovery.",
                category="recovery",
                priority=priority,
            )

        return None

    def _factor_driven_action(
        self, factors: List[Dict], baselines: Dict, priority: int
    ) -> Optional[DailyAction]:
        """Generate action from top recovery factor insights."""
        if not factors:
            return None

        top_factor = factors[0]
        name = top_factor.get("factor_name", "")
        threshold = top_factor.get("actionable_threshold", "")

        if threshold:
            return DailyAction(
                action=f"Focus on {name.lower()}: {threshold}",
                reasoning=f"{name} is your biggest recovery lever. "
                f"Hitting the right threshold here has the most impact.",
                category="lifestyle",
                priority=priority,
            )

        return None

    def _weather_action(
        self, weather_data: Dict, recovery: RecoveryStatus, priority: int
    ) -> Optional[DailyAction]:
        """Generate action informed by weather conditions."""
        current = weather_data.get("current", {})
        conditions = current.get("conditions", "").lower()
        temp = current.get("temp") or current.get("temperature")
        aqi_data = weather_data.get("air_quality", {})
        aqi = aqi_data.get("aqi")

        # High AQI warning
        if aqi and aqi >= 4:
            return DailyAction(
                action="Exercise indoors today — air quality is poor",
                reasoning=f"AQI is {aqi} ({aqi_data.get('description', 'poor')}). "
                f"Outdoor exercise with poor air quality undermines recovery.",
                category="lifestyle",
                priority=priority,
            )

        # Rainy conditions
        if any(w in conditions for w in ["rain", "drizzle", "thunderstorm"]):
            if recovery.category == "green":
                return DailyAction(
                    action="Indoor high-intensity session — rain outside",
                    reasoning=f"Weather is {conditions} but you're green. "
                    f"Gym, indoor cycling, or bodyweight work are good options.",
                    category="training",
                    priority=priority,
                )

        # Good weather + green recovery
        if temp and temp >= 10 and "rain" not in conditions and recovery.category == "green":
            return DailyAction(
                action=f"Take your workout outdoors — {temp:.0f}°C and {conditions}",
                reasoning="Good weather combined with green recovery is ideal for outdoor training.",
                category="lifestyle",
                priority=priority,
            )

        return None

    # =================== Sleep Target ===================

    def _build_sleep_target(self, sleep_patterns: Dict, baselines: Dict) -> SleepTarget:
        """Build tonight's sleep recommendation."""
        optimal_hours = sleep_patterns.get("optimal_sleep_hours", 8.0)
        optimal_bedtime_hour = sleep_patterns.get("optimal_bedtime_hour", 22)
        optimal_efficiency = sleep_patterns.get("optimal_efficiency", 85.0)

        # Format bedtime
        bedtime_str = f"{optimal_bedtime_hour:02d}:00"
        if optimal_bedtime_hour >= 20:
            # Adjust to 30-min precision
            bedtime_str = f"{optimal_bedtime_hour:02d}:30"

        reasoning_parts = [
            f"Your best recoveries come with {optimal_hours:.1f}+ hours of sleep"
        ]
        if optimal_efficiency and optimal_efficiency > 80:
            reasoning_parts.append(f"at {optimal_efficiency:.0f}%+ efficiency")

        return SleepTarget(
            target_bedtime=bedtime_str,
            target_hours=optimal_hours,
            reasoning=". ".join(reasoning_parts) + ".",
        )

    # =================== Context ===================

    def _build_context(
        self,
        weather_data: Optional[Dict],
        transport_data: Optional[Dict],
        tide_data: Optional[Dict],
    ) -> ContextSummary:
        """Build environmental context summary."""
        weather_str = None
        aqi_str = None
        transport_str = None
        outdoor_window = None

        if weather_data:
            current = weather_data.get("current", {})
            temp = current.get("temp") or current.get("temperature")
            conditions = current.get("conditions", "")
            forecast = weather_data.get("forecast_today", "")

            parts = []
            if temp is not None:
                parts.append(f"{temp:.0f}°C")
            if conditions:
                parts.append(conditions)
            if forecast:
                parts.append(forecast)
            weather_str = ", ".join(parts) if parts else None

            # AQI
            aqi_info = weather_data.get("air_quality", {})
            aqi_val = aqi_info.get("aqi")
            aqi_desc = aqi_info.get("description", "")
            if aqi_val:
                aqi_str = f"{aqi_desc} (AQI {aqi_val})"

        if transport_data and not transport_data.get("error"):
            lines = transport_data if isinstance(transport_data, list) else []
            disrupted = [
                line for line in lines
                if isinstance(line, dict) and line.get("status", "").lower() != "good service"
            ]
            if disrupted:
                issues = [f"{l.get('name', 'Line')}: {l.get('status', 'disrupted')}" for l in disrupted]
                transport_str = "; ".join(issues)
            elif lines:
                transport_str = "All lines running normally"

        if tide_data and weather_data:
            outdoor_window = self._compute_outdoor_window(weather_data, tide_data)

        return ContextSummary(
            weather=weather_str,
            air_quality=aqi_str,
            transport=transport_str,
            outdoor_window=outdoor_window,
        )

    def _compute_outdoor_window(
        self, weather_data: Dict, tide_data: Dict
    ) -> Optional[str]:
        """Find best outdoor activity window from weather and tide data."""
        # Simple heuristic: use sunrise/sunset from weather if available
        current = weather_data.get("current", {})
        sunrise = current.get("sunrise")
        sunset = current.get("sunset")

        if sunrise and sunset:
            return f"Daylight: {sunrise} - {sunset}"

        return None
