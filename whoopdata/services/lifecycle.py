"""Lifecycle-based coaching segments.

Detects the user's current fitness phase from historical trends
and adapts recommendation strategies accordingly.

Phases:
- building: Increasing fitness, can tolerate higher strain
- maintaining: Stable metrics, focus on consistency
- recovering: Declining trends, needs rest and recovery focus
- returning: Coming back from a break, gradual ramp-up needed
"""

import logging
from typing import Dict, Optional

import pandas as pd
from sqlalchemy.orm import Session

from whoopdata.analytics.data_prep import get_recovery_with_features

logger = logging.getLogger(__name__)


# Segment definitions with recommendation strategies
SEGMENTS = {
    "building": {
        "name": "Building Fitness",
        "description": "Your metrics are trending up. Your body is adapting to increased load.",
        "strategy": {
            "strain_tolerance": "high",
            "recovery_priority": "moderate",
            "sleep_emphasis": "maintain current levels",
            "key_message": "You're building. Push when green, but respect yellow days.",
        },
    },
    "maintaining": {
        "name": "Maintaining",
        "description": "Your metrics are stable. Focus on consistency and marginal gains.",
        "strategy": {
            "strain_tolerance": "moderate",
            "recovery_priority": "moderate",
            "sleep_emphasis": "optimise efficiency",
            "key_message": "Consistency is your edge. Don't chase big numbers — maintain the routine.",
        },
    },
    "recovering": {
        "name": "Needs Recovery",
        "description": "Your metrics are declining. Accumulated fatigue or stress is showing.",
        "strategy": {
            "strain_tolerance": "low",
            "recovery_priority": "high",
            "sleep_emphasis": "increase duration and prioritise early bedtime",
            "key_message": "Your body is asking for a break. Reduce strain and maximise recovery.",
        },
    },
    "returning": {
        "name": "Returning",
        "description": "You're coming back after a period of low activity or data gap.",
        "strategy": {
            "strain_tolerance": "low-moderate",
            "recovery_priority": "high",
            "sleep_emphasis": "build consistency first",
            "key_message": "Ease back in. Build consistency before intensity.",
        },
    },
}


class LifecycleDetector:
    """Detect user's current fitness lifecycle segment."""

    def __init__(self, db: Session):
        self.db = db

    def detect_segment(self, lookback_days: int = 28) -> Dict:
        """Detect the user's current lifecycle segment.

        Uses rolling 28-day trend analysis across recovery, HRV, and strain.

        Args:
            lookback_days: Days of data to analyse (default 28)

        Returns:
            Dictionary with segment ID, name, description, and strategy
        """
        df = get_recovery_with_features(self.db, days_back=lookback_days + 14)

        if len(df) < 14:
            return {
                "segment": "maintaining",
                **SEGMENTS["maintaining"],
                "confidence": "low",
                "reason": "Insufficient data for lifecycle detection (need 14+ days).",
            }

        # Check for data gap (returning)
        if self._detect_data_gap(df, lookback_days):
            return {
                "segment": "returning",
                **SEGMENTS["returning"],
                "confidence": "high",
                "reason": "Detected a gap in recent data — appears to be returning from a break.",
            }

        # Compute trends
        recent = df.head(lookback_days)
        first_half = recent.tail(lookback_days // 2)
        second_half = recent.head(lookback_days // 2)

        trends = self._compute_trends(first_half, second_half)
        segment_id, reason = self._classify_segment(trends)

        return {
            "segment": segment_id,
            **SEGMENTS[segment_id],
            "confidence": "medium" if len(df) < 21 else "high",
            "reason": reason,
            "trends": trends,
        }

    def _detect_data_gap(self, df: pd.DataFrame, lookback_days: int) -> bool:
        """Detect if there's a significant gap in recent data."""
        if len(df) < 7:
            return True

        recent = df.head(lookback_days)
        if len(recent) < lookback_days * 0.5:
            return True

        # Check for multi-day gaps
        if "created_at" in recent.columns:
            dates = pd.to_datetime(recent["created_at"]).sort_values()
            gaps = dates.diff().dt.days
            max_gap = gaps.max()
            if max_gap and max_gap > 5:
                return True

        return False

    def _compute_trends(self, first_half: pd.DataFrame, second_half: pd.DataFrame) -> Dict:
        """Compute trend percentages for key metrics."""
        trends = {}

        for col, label in [
            ("recovery_score", "recovery"),
            ("hrv_rmssd_milli", "hrv"),
            ("strain", "strain"),
            ("sleep_hours", "sleep"),
        ]:
            first_avg = first_half[col].mean() if col in first_half.columns else None
            second_avg = second_half[col].mean() if col in second_half.columns else None

            if (
                first_avg is not None
                and second_avg is not None
                and not pd.isna(first_avg)
                and not pd.isna(second_avg)
                and first_avg > 0
            ):
                change_pct = ((second_avg - first_avg) / first_avg) * 100
                trends[label] = {
                    "first_half_avg": round(float(first_avg), 1),
                    "second_half_avg": round(float(second_avg), 1),
                    "change_pct": round(float(change_pct), 1),
                }

        return trends

    def _classify_segment(self, trends: Dict) -> tuple:
        """Classify lifecycle segment from computed trends."""
        recovery_trend = trends.get("recovery", {}).get("change_pct", 0)
        hrv_trend = trends.get("hrv", {}).get("change_pct", 0)
        strain_trend = trends.get("strain", {}).get("change_pct", 0)

        # Recovering: declining recovery AND HRV
        if recovery_trend < -5 and hrv_trend < -5:
            return (
                "recovering",
                f"Recovery trending {recovery_trend:.0f}% and HRV trending {hrv_trend:.0f}%. "
                f"Your body needs more rest.",
            )

        # Building: improving recovery AND/OR HRV with increasing strain
        if (recovery_trend > 5 or hrv_trend > 5) and strain_trend >= 0:
            return (
                "building",
                f"Recovery trending {recovery_trend:+.0f}% and HRV {hrv_trend:+.0f}% "
                f"with strain {strain_trend:+.0f}%. You're adapting well.",
            )

        # Recovering: HRV dropping significantly even if recovery looks ok
        if hrv_trend < -10:
            return (
                "recovering",
                f"HRV trending {hrv_trend:.0f}% — early sign of accumulated fatigue.",
            )

        # Maintaining: everything within ±5%
        return (
            "maintaining",
            "Metrics are stable. Focus on consistency and marginal gains.",
        )
