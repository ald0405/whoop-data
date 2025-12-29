"""Health metrics aggregation service for dashboard endpoints."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from statistics import mean
from datetime import datetime

from whoopdata.models.models import Recovery, Sleep, Workout
from whoopdata.crud.recovery import get_recoveries
from whoopdata.crud.sleep import get_sleep
from whoopdata.crud.workout import get_recoveries as get_workouts


def calculate_avg(values: List[float], decimals: int = 2) -> Optional[float]:
    """Calculate average, returning None if list is empty."""
    return round(mean(values), decimals) if values else None


def get_metric_aggregation(values: List[float], unit: str = "") -> Dict[str, Any]:
    """
    Create standardized metric response with 7-day and 28-day averages.

    Args:
        values: List of values (should be in chronological order, most recent first)
        unit: Unit of measurement

    Returns:
        Standardized metric dict with last_7_days, avg_7_days, avg_28_days, latest
    """
    last_7 = values[:7] if len(values) >= 7 else values
    last_28 = values[:28] if len(values) >= 28 else values

    return {
        "last_7_days": [round(v, 2) for v in last_7],
        "avg_7_days": calculate_avg(last_7),
        "avg_28_days": calculate_avg(last_28),
        "latest": round(values[0], 2) if values else None,
        "unit": unit,
    }


def get_recovery_metrics(db: Session) -> Dict[str, Any]:
    """
    Get recovery score, RHR, and HRV metrics with aggregations.

    Returns:
        Dict with recovery_score, rhr, and hrv metrics
    """
    recoveries = get_recoveries(db, skip=0, limit=28)

    if not recoveries:
        return {
            "recovery_score": get_metric_aggregation([], "%"),
            "rhr": get_metric_aggregation([], "bpm"),
            "hrv": get_metric_aggregation([], "ms"),
        }

    # Extract values
    recovery_scores = [r.recovery_score for r in recoveries if r.recovery_score is not None]
    rhr_values = [r.resting_heart_rate for r in recoveries if r.resting_heart_rate is not None]
    hrv_values = [r.hrv_rmssd_milli for r in recoveries if r.hrv_rmssd_milli is not None]

    return {
        "recovery_score": get_metric_aggregation(recovery_scores, "%"),
        "rhr": get_metric_aggregation(rhr_values, "bpm"),
        "hrv": get_metric_aggregation(hrv_values, "ms"),
    }


def get_sleep_metrics(db: Session) -> Dict[str, Any]:
    """
    Get sleep metrics including hours slept, REM sleep, bedtime, and wake time.

    Returns:
        Dict with sleep_hours, rem_hours, rem_percentage, bedtime, wake_time
    """
    sleeps = get_sleep(db, skip=0, limit=28)

    if not sleeps:
        return {
            "sleep_hours": get_metric_aggregation([], "hours"),
            "rem_hours": get_metric_aggregation([], "hours"),
            "rem_percentage": get_metric_aggregation([], "%"),
            "sleep_efficiency": get_metric_aggregation([], "%"),
            "bedtime": {
                "last_7_days": [],
                "avg_7_days": None,
                "avg_28_days": None,
                "latest": None,
                "unit": "HH:MM",
            },
            "wake_time": {
                "last_7_days": [],
                "avg_7_days": None,
                "avg_28_days": None,
                "latest": None,
                "unit": "HH:MM",
            },
        }

    # Calculate sleep hours (total time in bed - awake time)
    sleep_hours = []
    rem_hours = []
    rem_percentages = []
    sleep_efficiency = []
    bedtimes = []
    wake_times = []

    for s in sleeps:
        # Sleep hours
        if s.total_time_in_bed_time_milli is not None and s.total_awake_time_milli is not None:
            total_sleep = (s.total_time_in_bed_time_milli - s.total_awake_time_milli) / 3600000
            sleep_hours.append(total_sleep)

            # REM hours and percentage
            if s.total_rem_sleep_time_milli is not None:
                rem_hour = s.total_rem_sleep_time_milli / 3600000
                rem_hours.append(rem_hour)

                # REM percentage of total sleep
                if total_sleep > 0:
                    rem_pct = (rem_hour / total_sleep) * 100
                    rem_percentages.append(rem_pct)

        # Sleep efficiency
        if s.sleep_efficiency_percentage is not None:
            sleep_efficiency.append(s.sleep_efficiency_percentage)

        # Bedtime
        if s.start:
            bedtimes.append(s.start.strftime("%H:%M"))

        # Wake time
        if s.end:
            wake_times.append(s.end.strftime("%H:%M"))

    return {
        "sleep_hours": get_metric_aggregation(sleep_hours, "hours"),
        "rem_hours": get_metric_aggregation(rem_hours, "hours"),
        "rem_percentage": get_metric_aggregation(rem_percentages, "%"),
        "sleep_efficiency": get_metric_aggregation(sleep_efficiency, "%"),
        "bedtime": {
            "last_7_days": bedtimes[:7],
            "latest": bedtimes[0] if bedtimes else None,
            "unit": "HH:MM",
        },
        "wake_time": {
            "last_7_days": wake_times[:7],
            "latest": wake_times[0] if wake_times else None,
            "unit": "HH:MM",
        },
    }


def get_strain_metrics(db: Session) -> Dict[str, Any]:
    """
    Get strain metrics with aggregations.

    Returns:
        Dict with strain metric
    """
    workouts = get_workouts(db, skip=0, limit=28)

    if not workouts:
        return {"strain": get_metric_aggregation([], "")}

    strain_values = [w.strain for w in workouts if w.strain is not None]

    return {"strain": get_metric_aggregation(strain_values, "")}


def get_all_health_metrics(db: Session) -> Dict[str, Any]:
    """
    Get all health metrics in standardized format.

    Returns:
        Dict with all health metrics (recovery, sleep, strain)
    """
    return {
        **get_recovery_metrics(db),
        **get_sleep_metrics(db),
        **get_strain_metrics(db),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
