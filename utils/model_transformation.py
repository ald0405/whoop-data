from datetime import datetime


def parse_dt(dt_str):
    """
    Parses Whoop datetime into the correct SQLAlchemy format
    """
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")) if dt_str else None

def transform_recovery(item: dict) -> dict:
    score = item.get("score") or {}

    return {
        "user_id": item.get("user_id"),
        "cycle_id": item.get("cycle_id"),
        "sleep_id": item.get("sleep_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "score_state": item.get("score_state"),  # this is top-level
        "user_calibrating": score.get("user_calibrating"),
        "recovery_score": score.get("recovery_score"),
        "resting_heart_rate": score.get("resting_heart_rate"),
        "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
        "spo2_percentage": score.get("spo2_percentage"),
        "skin_temp_celsius": score.get("skin_temp_celsius"),
    }

def transform_sleep(item: dict) -> dict:
    score = item.get("score") or {}
    stage_summary = score.get("stage_summary") or {}
    sleep_needed = score.get("sleep_needed") or {}

    return {
        "id": item.get("id"),
        "user_id": item.get("user_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "start": parse_dt(item.get("start")),
        "end": parse_dt(item.get("end")),
        "timezone_offset": item.get("timezone_offset"),
        "nap": item.get("nap"),
        "score_state": item.get("score_state"),
        "respiratory_rate": score.get("respiratory_rate"),
        "sleep_performance_percentage": score.get("sleep_performance_percentage"),
        "sleep_consistency_percentage": score.get("sleep_consistency_percentage"),
        "sleep_efficiency_percentage": score.get("sleep_efficiency_percentage"),

        # Stage summary metrics
        "total_time_in_bed_time_milli": stage_summary.get("total_in_bed_time_milli"),
        "total_awake_time_milli": stage_summary.get("total_awake_time_milli"),
        "total_no_data_time_milli": stage_summary.get("total_no_data_time_milli"),
        "total_slow_wave_sleep_time_milli": stage_summary.get("total_slow_wave_sleep_time_milli"),
        "total_rem_sleep_time_milli": stage_summary.get("total_rem_sleep_time_milli"),
        "sleep_cycle_count": stage_summary.get("sleep_cycle_count"),
        "disturbance_count": stage_summary.get("disturbance_count"),

        # Sleep needed metrics
        "baseline_sleep_needed_milli": sleep_needed.get("baseline_milli"),
        "need_from_sleep_debt_milli": sleep_needed.get("need_from_sleep_debt_milli"),
        "need_from_recent_strain_milli": sleep_needed.get("need_from_recent_strain_milli"),
        "need_from_recent_nap_milli": sleep_needed.get("need_from_recent_nap_milli"),
    }



def transform_workout(item: dict) -> dict:
    score = item.get("score") or {} # As not every workout will have a nest?
    zone = score.get("zone_duration") or {}

    return {
        "id": item.get("id"),
        "user_id": item.get("user_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "start": parse_dt(item.get("start")),
        "end": parse_dt(item.get("end")),
        "timezone_offset": item.get("timezone_offset"),
        "sport_id": item.get("sport_id"),
        "score_state": item.get("score_state"),
        "strain": score.get("strain"),
        "average_heart_rate": score.get("average_heart_rate"),
        "max_heart_rate": score.get("max_heart_rate"),
        "kilojoule": score.get("kilojoule"),
        "percent_recorded": score.get("percent_recorded"),
        "distance_meter": score.get("distance_meter"),
        "altitude_gain_meter": score.get("altitude_gain_meter"),
        "altitude_change_meter": score.get("altitude_change_meter"),
        
        # Optional: add zone durations (in minutes or hours if you want to transform)
        "zone_zero_minutes": round(zone.get("zone_zero_milli", 0) / 60000, 2),
        "zone_one_minutes": round(zone.get("zone_one_milli", 0) / 60000, 2),
        "zone_two_minutes": round(zone.get("zone_two_milli", 0) / 60000, 2),
        "zone_three_minutes": round(zone.get("zone_three_milli", 0) / 60000, 2),
        "zone_four_minutes": round(zone.get("zone_four_milli", 0) / 60000, 2),
        "zone_five_minutes": round(zone.get("zone_five_milli", 0) / 60000, 2),
    }
