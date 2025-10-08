from datetime import datetime
import json


def parse_dt(dt_str):
    """
    Parses Whoop datetime into the correct SQLAlchemy format
    """
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")) if dt_str else None

def transform_recovery(item: dict) -> dict:
    """
    Transform recovery data for database insertion.
    Note: Fields are now already flattened by the API client.
    """
    if isinstance(item, str):
        try:
            item = json.loads(item)
        except json.JSONDecodeError:
            item = {}  # Assign empty dict to prevent AttributeError
            pass

    return {
        "user_id": item.get("user_id"),
        "cycle_id": item.get("cycle_id"),
        "sleep_id": item.get("sleep_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "score_state": item.get("score_state"),
        # These fields are now already flattened (no more 'score.' prefix)
        "user_calibrating": item.get("user_calibrating"),
        "recovery_score": item.get("recovery_score"),
        "resting_heart_rate": item.get("resting_heart_rate"),
        "hrv_rmssd_milli": item.get("hrv_rmssd_milli"),
        "spo2_percentage": item.get("spo2_percentage"),
        "skin_temp_celsius": item.get("skin_temp_celsius"),
    }

def transform_sleep(item: dict) -> dict:
    """
    Transform sleep data for database insertion.
    Note: Fields are now already flattened by the API client.
    """
    return {
        "id": item.get("v1_id") or item.get("id"),  # Use v1_id if available, fallback to id
        "user_id": item.get("user_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "start": parse_dt(item.get("start")),
        "end": parse_dt(item.get("end")),
        "timezone_offset": item.get("timezone_offset"),
        "nap": item.get("nap"),
        "score_state": item.get("score_state"),
        # These fields are now already flattened
        "respiratory_rate": item.get("respiratory_rate"),
        "sleep_performance_percentage": item.get("sleep_performance_percentage"),
        "sleep_consistency_percentage": item.get("sleep_consistency_percentage"),
        "sleep_efficiency_percentage": item.get("sleep_efficiency_percentage"),

        # Stage summary metrics (already flattened)
        "total_time_in_bed_time_milli": item.get("total_time_in_bed_time_milli"),
        "total_awake_time_milli": item.get("total_awake_time_milli"),
        "total_no_data_time_milli": item.get("total_no_data_time_milli"),
        "total_slow_wave_sleep_time_milli": item.get("total_slow_wave_sleep_time_milli"),
        "total_rem_sleep_time_milli": item.get("total_rem_sleep_time_milli"),
        "sleep_cycle_count": item.get("sleep_cycle_count"),
        "disturbance_count": item.get("disturbance_count"),

        # Sleep needed metrics (already flattened)
        "baseline_sleep_needed_milli": item.get("baseline_sleep_needed_milli"),
        "need_from_sleep_debt_milli": item.get("need_from_sleep_debt_milli"),
        "need_from_recent_strain_milli": item.get("need_from_recent_strain_milli"),
        "need_from_recent_nap_milli": item.get("need_from_recent_nap_milli"),
    }



def transform_workout(item: dict) -> dict:
    """
    Transform workout data for database insertion.
    Note: Fields are now already flattened by the API client.
    """
    return {
        "id": item.get("v1_id"),
        "user_id": item.get("user_id"),
        "created_at": parse_dt(item.get("created_at")),
        "updated_at": parse_dt(item.get("updated_at")),
        "start": parse_dt(item.get("start")),
        "end": parse_dt(item.get("end")),
        "timezone_offset": item.get("timezone_offset"),
        "sport_id": item.get("sport_id"),
        "score_state": item.get("score_state"),
        # These fields are now already flattened
        "strain": item.get("strain"),
        "average_heart_rate": item.get("average_heart_rate"),
        "max_heart_rate": item.get("max_heart_rate"),
        "kilojoule": item.get("kilojoule"),
        "percent_recorded": item.get("percent_recorded"),
        "distance_meter": item.get("distance_meter"),
        "altitude_gain_meter": item.get("altitude_gain_meter"),
        "altitude_change_meter": item.get("altitude_change_meter"),
        
        # Zone durations are already converted to minutes by the API client
        "zone_zero_minutes": item.get("zone_zero_minutes", 0.0),
        "zone_one_minutes": item.get("zone_one_minutes", 0.0),
        "zone_two_minutes": item.get("zone_two_minutes", 0.0),
        "zone_three_minutes": item.get("zone_three_minutes", 0.0),
        "zone_four_minutes": item.get("zone_four_minutes", 0.0),
        "zone_five_minutes": item.get("zone_five_minutes", 0.0),
    }


def transform_withings_weight(item: dict) -> dict:
    """
    Transform Withings weight/body composition data for database insertion.
    Expects data from the transformed pandas DataFrame from WithingsClient.
    """
    return {
        "user_id": item.get("user_id") or "default_user",  # Set default if not provided
        "grpid": item.get("grpid"),
        "deviceid": item.get("deviceid"),
        "created_at": datetime.now(),
        "updated_at": item.get("datetime") or datetime.fromtimestamp(item.get("date", 0)) if item.get("date") else datetime.now(),
        "date": item.get("date"),
        "datetime": item.get("datetime") or datetime.fromtimestamp(item.get("date", 0)) if item.get("date") else datetime.now(),
        "timezone": item.get("timezone"),
        "comment": item.get("comment"),
        "category": item.get("category", 1),
        
        # Extract measurements by type
        "weight_kg": item.get("actual_value") if item.get("measure_type") == 1 else None,
        "height_m": item.get("actual_value") if item.get("measure_type") == 4 else None,
        "fat_free_mass_kg": item.get("actual_value") if item.get("measure_type") == 5 else None,
        "fat_ratio_percent": item.get("actual_value") if item.get("measure_type") == 6 else None,
        "fat_mass_kg": item.get("actual_value") if item.get("measure_type") == 8 else None,
        "muscle_mass_kg": item.get("actual_value") if item.get("measure_type") == 76 else None,
        "bone_mass_kg": item.get("actual_value") if item.get("measure_type") == 88 else None,
        "hydration_kg": item.get("actual_value") if item.get("measure_type") == 77 else None,
        "visceral_fat": item.get("actual_value") if item.get("measure_type") == 170 else None,
    }


def transform_withings_heart_rate(item: dict) -> dict:
    """
    Transform Withings heart rate/blood pressure data for database insertion.
    Expects data from the transformed pandas DataFrame from WithingsClient.
    """
    return {
        "user_id": item.get("user_id") or "default_user",
        "grpid": item.get("grpid"),
        "deviceid": item.get("deviceid"),
        "created_at": datetime.now(),
        "updated_at": item.get("datetime") or datetime.fromtimestamp(item.get("date", 0)) if item.get("date") else datetime.now(),
        "date": item.get("date"),
        "datetime": item.get("datetime") or datetime.fromtimestamp(item.get("date", 0)) if item.get("date") else datetime.now(),
        "timezone": item.get("timezone"),
        "category": item.get("category", 1),
        
        # Extract measurements by type
        "diastolic_bp_mmhg": item.get("actual_value") if item.get("measure_type") == 9 else None,
        "systolic_bp_mmhg": item.get("actual_value") if item.get("measure_type") == 10 else None,
        "heart_rate_bpm": item.get("actual_value") if item.get("measure_type") == 11 else None,
    }
