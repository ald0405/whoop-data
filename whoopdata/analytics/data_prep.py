"""Data preparation utilities for analytics.

Handles joins, feature engineering, and data cleaning for ML models.
"""

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from typing import Tuple, Optional
from datetime import datetime, timedelta

from whoopdata.models.models import Recovery, Sleep, Workout, Cycle, WithingsWeight


def get_recovery_with_features(
    db: Session, limit: Optional[int] = None, days_back: Optional[int] = 365
) -> pd.DataFrame:
    """Get recovery data with engineered features for ML.

    Joins recovery, sleep, and workout data to create comprehensive feature set.

    Features included:
    Basic metrics:
    - recovery_score (target)
    - hrv_rmssd_milli
    - resting_heart_rate
    - spo2_percentage
    - skin_temp_celsius

    Sleep features:
    - sleep_hours, rem_sleep_hours, slow_wave_sleep_hours, awake_time_hours
    - sleep_efficiency_percentage, sleep_consistency_percentage
    - respiratory_rate
    - sleep_cycle_count, disturbance_count
    - sleep_debt (computed from sleep need metrics)
    - sleep_quality_score (composite)

    Activity features:
    - strain (from associated cycle)
    - average_heart_rate, max_heart_rate, kilojoule

    Temporal features:
    - bedtime_hour, is_weekend
    - previous_day_recovery, previous_day_hrv, previous_day_rhr
    - rolling averages (7d, 14d, 30d)
    - trends and variability

    Args:
        db: Database session
        limit: Maximum number of records (None for all)
        days_back: Only include data from last N days

    Returns:
        DataFrame with recovery records and features
    """
    # Calculate date threshold
    date_threshold = datetime.now() - timedelta(days=days_back) if days_back else None

    # Query recovery with sleep data
    query = (
        db.query(
            Recovery.id,
            Recovery.created_at,
            Recovery.recovery_score,
            Recovery.hrv_rmssd_milli,
            Recovery.resting_heart_rate,
            Recovery.spo2_percentage,
            Recovery.skin_temp_celsius,
            Recovery.user_calibrating,
            Recovery.cycle_id,
            # Sleep data - expanded features
            Sleep.sleep_efficiency_percentage,
            Sleep.sleep_consistency_percentage,
            Sleep.sleep_performance_percentage,
            Sleep.respiratory_rate,
            Sleep.total_time_in_bed_time_milli,
            Sleep.total_awake_time_milli,
            Sleep.total_rem_sleep_time_milli,
            Sleep.total_slow_wave_sleep_time_milli,
            Sleep.total_no_data_time_milli,
            Sleep.sleep_cycle_count,
            Sleep.disturbance_count,
            Sleep.start.label("sleep_start"),
            Sleep.end.label("sleep_end"),
            # Sleep need/debt metrics
            Sleep.baseline_sleep_needed_milli,
            Sleep.need_from_sleep_debt_milli,
            Sleep.need_from_recent_strain_milli,
            Sleep.need_from_recent_nap_milli,
            # Cycle data for strain and activity
            Cycle.strain,
            Cycle.average_heart_rate,
            Cycle.max_heart_rate,
            Cycle.kilojoule,
            Cycle.start.label("cycle_start"),
            Cycle.end.label("cycle_end"),
        )
        .join(Sleep, Recovery.sleep_id == Sleep.id, isouter=True)
        .join(Cycle, Recovery.cycle_id == Cycle.id, isouter=True)
    )

    if date_threshold:
        query = query.filter(Recovery.created_at >= date_threshold)

    query = query.filter(Recovery.recovery_score.isnot(None))  # Only complete records
    query = query.order_by(Recovery.created_at.desc())

    if limit:
        query = query.limit(limit)

    # Convert to DataFrame
    df = pd.read_sql(query.statement, db.bind)

    # Sort by date for temporal features
    df = df.sort_values("created_at").reset_index(drop=True)

    # ===== Basic Sleep Time Features =====
    df["sleep_hours"] = (
        df["total_time_in_bed_time_milli"] - df["total_awake_time_milli"]
    ) / 3600000
    df["time_in_bed_hours"] = df["total_time_in_bed_time_milli"] / 3600000
    df["rem_sleep_hours"] = df["total_rem_sleep_time_milli"] / 3600000
    df["slow_wave_sleep_hours"] = df["total_slow_wave_sleep_time_milli"] / 3600000
    df["awake_time_hours"] = df["total_awake_time_milli"] / 3600000
    df["light_sleep_hours"] = (
        df["total_time_in_bed_time_milli"]
        - df["total_awake_time_milli"]
        - df["total_rem_sleep_time_milli"]
        - df["total_slow_wave_sleep_time_milli"]
    ) / 3600000

    # ===== Sleep Debt & Need Features =====
    df["baseline_sleep_needed_hours"] = df["baseline_sleep_needed_milli"] / 3600000
    df["sleep_debt_hours"] = df["need_from_sleep_debt_milli"] / 3600000
    df["sleep_need_from_strain_hours"] = df["need_from_recent_strain_milli"] / 3600000
    df["total_sleep_need_hours"] = (
        df["baseline_sleep_needed_milli"]
        + df["need_from_sleep_debt_milli"]
        + df["need_from_recent_strain_milli"]
    ) / 3600000
    df["sleep_deficit"] = df["total_sleep_need_hours"] - df["sleep_hours"]  # Negative = surplus

    # ===== Sleep Stage Ratios =====
    df["rem_percentage"] = (df["rem_sleep_hours"] / df["sleep_hours"] * 100).fillna(0)
    df["deep_sleep_percentage"] = (df["slow_wave_sleep_hours"] / df["sleep_hours"] * 100).fillna(0)
    df["light_sleep_percentage"] = (df["light_sleep_hours"] / df["sleep_hours"] * 100).fillna(0)

    # ===== Composite Sleep Quality Score =====
    df["sleep_quality_score"] = (
        (df["sleep_efficiency_percentage"] * 0.3)
        + (df["rem_percentage"] * 0.25)
        + (df["deep_sleep_percentage"] * 0.25)
        + ((100 - df["disturbance_count"] * 5).clip(0, 100) * 0.2)  # Fewer disturbances = better
    )

    # ===== Heart Rate Metrics =====
    # Only calculate if we have max_heart_rate from cycle data
    df["hr_reserve"] = (df["max_heart_rate"] - df["resting_heart_rate"]).astype("float64").fillna(0)
    df["avg_hr_percentage_of_max"] = (
        (df["average_heart_rate"] / df["max_heart_rate"] * 100).astype("float64").fillna(0)
    )

    # ===== Temporal Features =====
    df["bedtime_hour"] = pd.to_datetime(df["sleep_start"]).dt.hour
    df["wake_hour"] = pd.to_datetime(df["sleep_end"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["created_at"]).dt.dayofweek
    df["is_weekend"] = df["day_of_week"] >= 5

    # ===== Strain & Activity Features =====
    df["strain"] = df["strain"].astype("float64").fillna(0)
    df["kilojoule"] = df["kilojoule"].astype("float64").fillna(0)

    # ===== Previous Day Features (lagged) =====
    df["prev_recovery_score"] = df["recovery_score"].shift(1)
    df["prev_hrv"] = df["hrv_rmssd_milli"].shift(1)
    df["prev_rhr"] = df["resting_heart_rate"].shift(1)
    df["prev_strain"] = df["strain"].shift(1)
    df["prev_sleep_hours"] = df["sleep_hours"].shift(1)

    # Recovery change from previous day
    df["recovery_change"] = df["recovery_score"] - df["prev_recovery_score"]
    df["hrv_change"] = df["hrv_rmssd_milli"] - df["prev_hrv"]
    df["rhr_change"] = df["resting_heart_rate"] - df["prev_rhr"]

    # ===== Rolling Average Features (7-day, 14-day) =====
    for window in [7, 14]:
        df[f"recovery_rolling_{window}d"] = (
            df["recovery_score"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"hrv_rolling_{window}d"] = (
            df["hrv_rmssd_milli"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"rhr_rolling_{window}d"] = (
            df["resting_heart_rate"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"strain_rolling_{window}d"] = (
            df["strain"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"sleep_rolling_{window}d"] = (
            df["sleep_hours"].shift(1).rolling(window=window, min_periods=3).mean()
        )

    # ===== Rolling Variability Features (standard deviation) =====
    for window in [7, 14]:
        df[f"hrv_std_{window}d"] = (
            df["hrv_rmssd_milli"].shift(1).rolling(window=window, min_periods=3).std()
        )
        df[f"rhr_std_{window}d"] = (
            df["resting_heart_rate"].shift(1).rolling(window=window, min_periods=3).std()
        )
        df[f"recovery_std_{window}d"] = (
            df["recovery_score"].shift(1).rolling(window=window, min_periods=3).std()
        )

    # ===== Deviation from Rolling Average (how far from normal) =====
    df["hrv_deviation_from_avg"] = df["hrv_rmssd_milli"] - df["hrv_rolling_7d"]
    df["rhr_deviation_from_avg"] = df["resting_heart_rate"] - df["rhr_rolling_7d"]
    df["strain_deviation_from_avg"] = df["strain"] - df["strain_rolling_7d"]

    # ===== Cumulative Strain (last 3 days) =====
    df["strain_3d_sum"] = df["strain"].shift(1).rolling(window=3, min_periods=1).sum()

    # ===== Workout Features =====
    # Initialize workout columns with defaults
    df["sport_id"] = 0
    df["workout_strain"] = 0.0
    df["workout_kilojoule"] = 0.0
    df["total_zone_minutes"] = 0.0
    df["high_intensity_pct"] = 0.0
    df["workout_start_hour"] = pd.NaT
    df["workout_is_morning"] = False
    df["workout_is_afternoon"] = False
    df["workout_is_evening"] = False

    for zone in range(6):
        df[f"zone_{zone}_minutes"] = 0.0
        df[f"zone_{zone}_pct"] = 0.0

    # Join workout data from the cycle's day
    if "cycle_id" in df.columns and len(df) > 0:
        try:
            workouts_query = db.query(
                Workout.cycle_id,
                Workout.sport_id,
                Workout.strain.label("workout_strain"),
                Workout.zone_zero_minutes,
                Workout.zone_one_minutes,
                Workout.zone_two_minutes,
                Workout.zone_three_minutes,
                Workout.zone_four_minutes,
                Workout.zone_five_minutes,
                Workout.start.label("workout_start"),
                Workout.end.label("workout_end"),
                Workout.kilojoule.label("workout_kilojoule"),
            )
            workouts_df = pd.read_sql(workouts_query.statement, db.bind)

            if len(workouts_df) > 0:
                # Aggregate workouts by cycle (multiple workouts per cycle possible)
                workout_agg = (
                    workouts_df.groupby("cycle_id")
                    .agg(
                        {
                            "sport_id": lambda x: (
                                x.mode()[0] if len(x.mode()) > 0 else None
                            ),  # Most common sport
                            "workout_strain": "sum",
                            "zone_zero_minutes": "sum",
                            "zone_one_minutes": "sum",
                            "zone_two_minutes": "sum",
                            "zone_three_minutes": "sum",
                            "zone_four_minutes": "sum",
                            "zone_five_minutes": "sum",
                            "workout_start": "min",  # First workout start
                            "workout_end": "max",  # Last workout end
                            "workout_kilojoule": "sum",
                        }
                    )
                    .reset_index()
                )

                # Merge workout data
                df = df.merge(workout_agg, on="cycle_id", how="left", suffixes=("", "_workout"))

                # Update columns from merged data
                if "sport_id_workout" in df.columns:
                    df["sport_id"] = df["sport_id_workout"].fillna(0).astype(int)
                if "workout_strain_workout" in df.columns:
                    df["workout_strain"] = df["workout_strain_workout"].fillna(0)
                if "workout_kilojoule_workout" in df.columns:
                    df["workout_kilojoule"] = df["workout_kilojoule_workout"].fillna(0)

                # Zone times are already in minutes
                for zone in range(6):
                    zone_col = f"zone_{zone}_minutes"
                    if f"{zone_col}_workout" in df.columns:
                        df[zone_col] = df[f"{zone_col}_workout"].fillna(0)

                # Calculate total workout time and HR zone percentages
                df["total_zone_minutes"] = sum(df[f"zone_{i}_minutes"] for i in range(6))

                # Calculate zone percentages, handling zero division
                for zone in range(6):
                    mask = df["total_zone_minutes"] > 0
                    df.loc[mask, f"zone_{zone}_pct"] = (
                        df.loc[mask, f"zone_{zone}_minutes"]
                        / df.loc[mask, "total_zone_minutes"]
                        * 100
                    )

                # High intensity percentage (zones 4-5)
                df["high_intensity_pct"] = df["zone_four_pct"] + df["zone_five_pct"]

                # Workout timing features
                if "workout_start" in df.columns:
                    df["workout_start_hour"] = pd.to_datetime(
                        df["workout_start"], errors="coerce"
                    ).dt.hour
                    df["workout_is_morning"] = (df["workout_start_hour"] >= 5) & (
                        df["workout_start_hour"] < 12
                    )
                    df["workout_is_afternoon"] = (df["workout_start_hour"] >= 12) & (
                        df["workout_start_hour"] < 18
                    )
                    df["workout_is_evening"] = (df["workout_start_hour"] >= 18) & (
                        df["workout_start_hour"] < 22
                    )

                # Clean up temporary columns
                drop_cols = [col for col in df.columns if col.endswith("_workout")]
                df = df.drop(columns=drop_cols)
        except Exception as e:
            # If workout data fails to load, columns are already initialized with defaults
            pass

    # Drop rows with critical missing data
    # For ML models, we need records with sufficient history for rolling features (at least 14 days)
    # First row has no lagged features, first 7 rows have no 7d rolling, first 14 rows have no 14d rolling
    df = df.dropna(subset=["recovery_score", "hrv_rmssd_milli", "resting_heart_rate"])

    # Add a flag indicating if row has complete rolling features (for ML training)
    df["has_rolling_features"] = (~df[["hrv_rolling_7d", "hrv_rolling_14d"]].isna()).all(axis=1)

    return df


def get_sleep_with_features(
    db: Session, limit: Optional[int] = None, days_back: Optional[int] = 365
) -> pd.DataFrame:
    """Get sleep data with engineered features for sleep performance prediction.

    Args:
        db: Database session
        limit: Maximum number of records
        days_back: Only include data from last N days

    Returns:
        DataFrame with sleep records and features
    """
    date_threshold = datetime.now() - timedelta(days=days_back) if days_back else None

    query = db.query(Sleep).filter(
        Sleep.nap == False, Sleep.sleep_performance_percentage.isnot(None)  # Exclude naps
    )

    if date_threshold:
        query = query.filter(Sleep.created_at >= date_threshold)

    query = query.order_by(Sleep.created_at.desc())

    if limit:
        query = query.limit(limit)

    df = pd.read_sql(query.statement, db.bind)

    # Feature engineering
    df["total_sleep_hours"] = (
        df["total_time_in_bed_time_milli"] - df["total_awake_time_milli"]
    ) / 3600000
    df["rem_sleep_hours"] = df["total_rem_sleep_time_milli"] / 3600000
    df["slow_wave_sleep_hours"] = df["total_slow_wave_sleep_time_milli"] / 3600000
    df["awake_time_hours"] = df["total_awake_time_milli"] / 3600000
    df["time_in_bed_hours"] = df["total_time_in_bed_time_milli"] / 3600000

    # Bedtime consistency (will need historical calculation)
    df["bedtime_hour"] = pd.to_datetime(df["start"]).dt.hour

    # Drop critical missing values
    df = df.dropna(subset=["sleep_performance_percentage", "total_sleep_hours"])

    return df


def get_sleep_quality_features(
    db: Session, limit: Optional[int] = None, days_back: Optional[int] = 365
) -> pd.DataFrame:
    """Get sleep data with comprehensive features for sleep efficiency analysis.

    Joins sleep with recovery and cycle data to create rich feature set focused on
    understanding what drives sleep quality (efficiency).

    Features included:
    - Sleep duration and stages (REM, deep, light, awake)
    - Sleep efficiency and consistency
    - Respiratory rate
    - Bedtime and wake time
    - Day of week patterns
    - Previous day recovery and strain
    - Sleep debt and deficit
    - Rolling averages and trends

    Args:
        db: Database session
        limit: Maximum number of records (None for all)
        days_back: Only include data from last N days

    Returns:
        DataFrame with sleep records and engineered features
    """
    date_threshold = datetime.now() - timedelta(days=days_back) if days_back else None

    # Query sleep with recovery and cycle data
    query = (
        db.query(
            Sleep.id,
            Sleep.created_at,
            Sleep.start.label("sleep_start"),
            Sleep.end.label("sleep_end"),
            Sleep.sleep_efficiency_percentage,
            Sleep.sleep_consistency_percentage,
            Sleep.sleep_performance_percentage,
            Sleep.respiratory_rate,
            Sleep.total_time_in_bed_time_milli,
            Sleep.total_awake_time_milli,
            Sleep.total_rem_sleep_time_milli,
            Sleep.total_slow_wave_sleep_time_milli,
            Sleep.total_no_data_time_milli,
            Sleep.sleep_cycle_count,
            Sleep.disturbance_count,
            # Sleep need/debt metrics
            Sleep.baseline_sleep_needed_milli,
            Sleep.need_from_sleep_debt_milli,
            Sleep.need_from_recent_strain_milli,
            Sleep.need_from_recent_nap_milli,
            # Recovery data from same day
            Recovery.recovery_score,
            Recovery.hrv_rmssd_milli,
            Recovery.resting_heart_rate,
            # Cycle data for strain
            Cycle.strain,
        )
        .join(Recovery, Sleep.id == Recovery.sleep_id, isouter=True)
        .join(Cycle, Recovery.cycle_id == Cycle.id, isouter=True)
        .filter(Sleep.nap == False, Sleep.sleep_efficiency_percentage.isnot(None))  # Exclude naps
    )

    if date_threshold:
        query = query.filter(Sleep.created_at >= date_threshold)

    query = query.order_by(Sleep.created_at.desc())

    if limit:
        query = query.limit(limit)

    # Convert to DataFrame
    df = pd.read_sql(query.statement, db.bind)

    # Sort by date for temporal features
    df = df.sort_values("created_at").reset_index(drop=True)

    # ===== Basic Sleep Time Features =====
    df["total_sleep_hours"] = (
        df["total_time_in_bed_time_milli"] - df["total_awake_time_milli"]
    ) / 3600000
    df["time_in_bed_hours"] = df["total_time_in_bed_time_milli"] / 3600000
    df["rem_sleep_hours"] = df["total_rem_sleep_time_milli"] / 3600000
    df["slow_wave_sleep_hours"] = df["total_slow_wave_sleep_time_milli"] / 3600000
    df["awake_time_hours"] = df["total_awake_time_milli"] / 3600000
    df["light_sleep_hours"] = (
        df["total_time_in_bed_time_milli"]
        - df["total_awake_time_milli"]
        - df["total_rem_sleep_time_milli"]
        - df["total_slow_wave_sleep_time_milli"]
    ) / 3600000

    # ===== Sleep Debt & Need Features =====
    df["baseline_sleep_needed_hours"] = df["baseline_sleep_needed_milli"] / 3600000
    df["sleep_debt_hours"] = df["need_from_sleep_debt_milli"] / 3600000
    df["sleep_need_from_strain_hours"] = df["need_from_recent_strain_milli"] / 3600000
    df["total_sleep_need_hours"] = (
        df["baseline_sleep_needed_milli"]
        + df["need_from_sleep_debt_milli"]
        + df["need_from_recent_strain_milli"]
    ) / 3600000
    df["sleep_deficit"] = (
        df["total_sleep_need_hours"] - df["total_sleep_hours"]
    )  # Negative = surplus

    # ===== Sleep Stage Ratios =====
    df["rem_percentage"] = (df["rem_sleep_hours"] / df["total_sleep_hours"] * 100).fillna(0)
    df["deep_sleep_percentage"] = (
        df["slow_wave_sleep_hours"] / df["total_sleep_hours"] * 100
    ).fillna(0)
    df["light_sleep_percentage"] = (df["light_sleep_hours"] / df["total_sleep_hours"] * 100).fillna(
        0
    )

    # ===== Temporal Features =====
    df["bedtime_hour"] = pd.to_datetime(df["sleep_start"]).dt.hour
    df["wake_hour"] = pd.to_datetime(df["sleep_end"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["created_at"]).dt.dayofweek
    df["is_weekend"] = df["day_of_week"] >= 5

    # ===== Strain & Activity Features =====
    df["strain"] = df["strain"].astype("float64").fillna(0)

    # ===== Previous Night Features (lagged) =====
    df["prev_sleep_efficiency"] = df["sleep_efficiency_percentage"].shift(1)
    df["prev_sleep_hours"] = df["total_sleep_hours"].shift(1)
    df["prev_strain"] = df["strain"].shift(1)
    df["prev_recovery_score"] = df["recovery_score"].shift(1)
    df["prev_bedtime_hour"] = df["bedtime_hour"].shift(1)

    # Sleep quality change from previous night
    df["sleep_efficiency_change"] = df["sleep_efficiency_percentage"] - df["prev_sleep_efficiency"]

    # ===== Rolling Average Features (7-day) =====
    for window in [7]:
        df[f"sleep_efficiency_rolling_{window}d"] = (
            df["sleep_efficiency_percentage"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"sleep_hours_rolling_{window}d"] = (
            df["total_sleep_hours"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"bedtime_rolling_{window}d"] = (
            df["bedtime_hour"].shift(1).rolling(window=window, min_periods=3).mean()
        )
        df[f"strain_rolling_{window}d"] = (
            df["strain"].shift(1).rolling(window=window, min_periods=3).mean()
        )

    # ===== Bedtime Consistency =====
    df["bedtime_std_7d"] = df["bedtime_hour"].shift(1).rolling(window=7, min_periods=3).std()
    df["bedtime_consistency_score"] = (100 - df["bedtime_std_7d"] * 20).clip(
        0, 100
    )  # Lower std = better consistency

    # ===== Deviation from Average Bedtime =====
    df["bedtime_deviation"] = df["bedtime_hour"] - df["bedtime_rolling_7d"]

    # Drop rows with critical missing data
    df = df.dropna(subset=["sleep_efficiency_percentage", "total_sleep_hours"])

    # Add a flag indicating if row has complete rolling features
    df["has_rolling_features"] = (
        ~df[["sleep_efficiency_rolling_7d", "sleep_hours_rolling_7d"]].isna()
    ).all(axis=1)

    return df


def get_training_data(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list,
    test_size: float = 0.2,
    scale_features: bool = True,
) -> Tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    Optional[StandardScaler],
    Optional[SimpleImputer],
]:
    """Prepare training and test datasets with preprocessing.

    Args:
        df: Source DataFrame
        target_col: Name of target column
        feature_cols: List of feature column names
        test_size: Fraction of data for testing (0.0-1.0)
        scale_features: Whether to standardize features

    Returns:
        Tuple of (X_train, X_test, y_train, y_test, scaler, imputer)

    Raises:
        ValueError: If dataframe is empty or has insufficient samples
    """
    from sklearn.model_selection import train_test_split

    if len(df) == 0:
        raise ValueError("DataFrame is empty - cannot train model with 0 samples")

    # Extract features and target
    X = df[feature_cols].copy()
    y = df[target_col].copy()

    if len(X) == 0:
        raise ValueError(
            f"No valid samples found after extracting features. DataFrame has {len(df)} rows but features resulted in 0 samples."
        )

    # Handle missing values
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_imputed, y, test_size=test_size, random_state=42
    )

    # Scale features if requested
    scaler = None
    if scale_features:
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler, imputer


def calculate_rolling_features(
    df: pd.DataFrame, metric_col: str, window_sizes: list = [7, 14, 30]
) -> pd.DataFrame:
    """Calculate rolling averages and trends.

    Args:
        df: DataFrame with time series data
        metric_col: Column name to calculate rolling stats for
        window_sizes: List of window sizes in days

    Returns:
        DataFrame with additional rolling feature columns
    """
    df = df.sort_values("created_at")

    for window in window_sizes:
        df[f"{metric_col}_rolling_{window}d"] = (
            df[metric_col].rolling(window=window, min_periods=1).mean()
        )
        df[f"{metric_col}_std_{window}d"] = (
            df[metric_col].rolling(window=window, min_periods=1).std()
        )

    # Calculate trend (difference from rolling mean)
    df[f"{metric_col}_trend"] = df[metric_col] - df[f"{metric_col}_rolling_7d"]

    return df


def get_workouts_with_recovery(
    db: Session, limit: Optional[int] = None, days_back: Optional[int] = 365
) -> pd.DataFrame:
    """Get workout data with next-day recovery outcomes for sport-specific analysis.

    This function enables analysis like:
    - Which sports correlate with better/worse recovery?
    - Does workout timing (morning vs evening) affect recovery?
    - How does workout intensity impact next-day recovery?

    Features included:
    - Workout details (sport, strain, duration, heart rate zones)
    - Workout timing (hour of day, morning/afternoon/evening)
    - Next-day recovery score and metrics
    - Cycle-level daily strain

    Args:
        db: Database session
        limit: Maximum number of records (None for all)
        days_back: Only include data from last N days

    Returns:
        DataFrame with workouts and their recovery outcomes
    """
    from whoopdata.utils.sport_mapping import get_sport_name, get_sport_category

    date_threshold = datetime.now() - timedelta(days=days_back) if days_back else None

    # Query workouts with cycle and recovery data
    # We want: Workout -> Cycle -> Next Cycle's Recovery
    query = (
        db.query(
            Workout.id.label("workout_id"),
            Workout.created_at.label("workout_date"),
            Workout.start.label("workout_start"),
            Workout.end.label("workout_end"),
            Workout.sport_id,
            Workout.strain.label("workout_strain"),
            Workout.average_heart_rate.label("workout_avg_hr"),
            Workout.max_heart_rate.label("workout_max_hr"),
            Workout.kilojoule.label("workout_kilojoule"),
            Workout.distance_meter,
            Workout.zone_zero_minutes,
            Workout.zone_one_minutes,
            Workout.zone_two_minutes,
            Workout.zone_three_minutes,
            Workout.zone_four_minutes,
            Workout.zone_five_minutes,
            # Cycle data (the day of the workout)
            Cycle.id.label("cycle_id"),
            Cycle.start.label("cycle_start"),
            Cycle.end.label("cycle_end"),
            Cycle.strain.label("daily_strain"),  # Total strain for the day
            Cycle.kilojoule.label("daily_kilojoule"),
        )
        .join(Cycle, Workout.cycle_id == Cycle.id)
    )

    if date_threshold:
        query = query.filter(Workout.created_at >= date_threshold)

    query = query.filter(
        Workout.sport_id.isnot(None), Workout.strain.isnot(None)
    )  # Valid workouts only
    query = query.order_by(Workout.created_at.desc())

    if limit:
        query = query.limit(limit)

    # Convert to DataFrame
    df = pd.read_sql(query.statement, db.bind)

    if len(df) == 0:
        return df  # Return empty DataFrame

    # Add sport names and categories
    df["sport_name"] = df["sport_id"].apply(get_sport_name)
    df["sport_category"] = df["sport_id"].apply(get_sport_category)

    # Calculate workout duration
    df["workout_duration_minutes"] = (
        pd.to_datetime(df["workout_end"]) - pd.to_datetime(df["workout_start"])
    ).dt.total_seconds() / 60

    # Calculate total zone time and percentages
    df["total_zone_minutes"] = sum(df[f"zone_{i}_minutes"] for i in range(6))

    for zone in range(6):
        df[f"zone_{zone}_pct"] = (
            df[f"zone_{zone}_minutes"] / df["total_zone_minutes"] * 100
        ).fillna(0)

    # High intensity percentage (zones 4-5)
    df["high_intensity_pct"] = df["zone_four_pct"] + df["zone_five_pct"]

    # Workout timing features
    df["workout_hour"] = pd.to_datetime(df["workout_start"]).dt.hour
    df["workout_day_of_week"] = pd.to_datetime(df["workout_start"]).dt.dayofweek
    df["workout_is_weekend"] = df["workout_day_of_week"] >= 5
    df["workout_is_morning"] = (df["workout_hour"] >= 5) & (df["workout_hour"] < 12)
    df["workout_is_afternoon"] = (df["workout_hour"] >= 12) & (df["workout_hour"] < 18)
    df["workout_is_evening"] = (df["workout_hour"] >= 18) & (df["workout_hour"] < 22)

    # Now join with next-day recovery
    # We need to find the recovery from the NEXT cycle after this workout's cycle
    # This is complex, so we'll do it by finding recoveries where created_at > workout date
    
    # For each workout, find the next recovery (within 48 hours)
    recoveries_query = db.query(
        Recovery.cycle_id,
        Recovery.created_at.label("recovery_date"),
        Recovery.recovery_score,
        Recovery.hrv_rmssd_milli.label("recovery_hrv"),
        Recovery.resting_heart_rate.label("recovery_rhr"),
        Recovery.spo2_percentage,
        Recovery.user_calibrating,
    )

    recoveries_df = pd.read_sql(recoveries_query.statement, db.bind)

    # Sort both dataframes
    df = df.sort_values("workout_date").reset_index(drop=True)
    recoveries_df = recoveries_df.sort_values("recovery_date").reset_index(drop=True)

    # For each workout, find next recovery (merge_asof)
    df_with_recovery = pd.merge_asof(
        df,
        recoveries_df,
        left_on="workout_date",
        right_on="recovery_date",
        direction="forward",
        tolerance=pd.Timedelta("48 hours"),  # Recovery must be within 48h
    )

    # Calculate time to recovery
    df_with_recovery["hours_to_recovery"] = (
        pd.to_datetime(df_with_recovery["recovery_date"])
        - pd.to_datetime(df_with_recovery["workout_date"])
    ).dt.total_seconds() / 3600

    # Only keep workouts that have a next-day recovery (within 12-36 hours is typical)
    df_with_recovery = df_with_recovery[
        (df_with_recovery["hours_to_recovery"] >= 12)
        & (df_with_recovery["hours_to_recovery"] <= 36)
    ].copy()

    # Drop rows with missing recovery data
    df_with_recovery = df_with_recovery.dropna(subset=["recovery_score"])

    return df_with_recovery
