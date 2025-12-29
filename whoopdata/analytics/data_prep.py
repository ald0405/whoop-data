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

from whoopdata.models.models import Recovery, Sleep, Workout, Cycle


def get_recovery_with_features(
    db: Session,
    limit: Optional[int] = None,
    days_back: Optional[int] = 365
) -> pd.DataFrame:
    """Get recovery data with engineered features for ML.
    
    Joins recovery, sleep, and workout data to create comprehensive feature set.
    
    Features included:
    - recovery_score (target)
    - hrv_rmssd_milli
    - resting_heart_rate
    - spo2_percentage
    - skin_temp_celsius
    - sleep_hours (computed)
    - sleep_efficiency_percentage
    - sleep_consistency_percentage
    - rem_sleep_hours (computed)
    - slow_wave_sleep_hours (computed)
    - awake_time_hours (computed)
    - strain (from associated cycle/workout)
    - days_since_high_strain
    
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
    query = db.query(
        Recovery.id,
        Recovery.created_at,
        Recovery.recovery_score,
        Recovery.hrv_rmssd_milli,
        Recovery.resting_heart_rate,
        Recovery.spo2_percentage,
        Recovery.skin_temp_celsius,
        Recovery.user_calibrating,
        # Sleep data
        Sleep.sleep_efficiency_percentage,
        Sleep.sleep_consistency_percentage,
        Sleep.total_time_in_bed_time_milli,
        Sleep.total_awake_time_milli,
        Sleep.total_rem_sleep_time_milli,
        Sleep.total_slow_wave_sleep_time_milli,
        Sleep.sleep_cycle_count,
        Sleep.disturbance_count,
        Sleep.start.label('sleep_start'),
        Sleep.end.label('sleep_end'),
        # Cycle data for strain
        Cycle.strain,
        Cycle.average_heart_rate,
        Cycle.max_heart_rate,
        Cycle.kilojoule,
    ).join(
        Sleep, Recovery.sleep_id == Sleep.id, isouter=True
    ).join(
        Cycle, Recovery.cycle_id == Cycle.id, isouter=True
    )
    
    if date_threshold:
        query = query.filter(Recovery.created_at >= date_threshold)
    
    query = query.filter(Recovery.recovery_score.isnot(None))  # Only complete records
    query = query.order_by(Recovery.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    # Convert to DataFrame
    df = pd.read_sql(query.statement, db.bind)
    
    # Feature engineering
    df['sleep_hours'] = (df['total_time_in_bed_time_milli'] - df['total_awake_time_milli']) / 3600000
    df['time_in_bed_hours'] = df['total_time_in_bed_time_milli'] / 3600000
    df['rem_sleep_hours'] = df['total_rem_sleep_time_milli'] / 3600000
    df['slow_wave_sleep_hours'] = df['total_slow_wave_sleep_time_milli'] / 3600000
    df['awake_time_hours'] = df['total_awake_time_milli'] / 3600000
    
    # Calculate sleep quality score (custom metric)
    df['sleep_quality_score'] = (
        (df['sleep_efficiency_percentage'] * 0.4) +
        (df['rem_sleep_hours'] * 10) +  # Normalize REM to percentage-like scale
        (df['slow_wave_sleep_hours'] * 10)
    )
    
    # Bedtime hour (24-hour format)
    df['bedtime_hour'] = pd.to_datetime(df['sleep_start']).dt.hour
    
    # Weekend indicator
    df['is_weekend'] = pd.to_datetime(df['created_at']).dt.dayofweek >= 5
    
    # Fill missing strain with 0 (rest day)
    df['strain'] = df['strain'].fillna(0)
    
    # Drop rows with critical missing data
    df = df.dropna(subset=['recovery_score', 'hrv_rmssd_milli', 'resting_heart_rate'])
    
    return df


def get_sleep_with_features(
    db: Session,
    limit: Optional[int] = None,
    days_back: Optional[int] = 365
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
        Sleep.nap == False,  # Exclude naps
        Sleep.sleep_performance_percentage.isnot(None)
    )
    
    if date_threshold:
        query = query.filter(Sleep.created_at >= date_threshold)
    
    query = query.order_by(Sleep.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    df = pd.read_sql(query.statement, db.bind)
    
    # Feature engineering
    df['total_sleep_hours'] = (df['total_time_in_bed_time_milli'] - df['total_awake_time_milli']) / 3600000
    df['rem_sleep_hours'] = df['total_rem_sleep_time_milli'] / 3600000
    df['slow_wave_sleep_hours'] = df['total_slow_wave_sleep_time_milli'] / 3600000
    df['awake_time_hours'] = df['total_awake_time_milli'] / 3600000
    df['time_in_bed_hours'] = df['total_time_in_bed_time_milli'] / 3600000
    
    # Bedtime consistency (will need historical calculation)
    df['bedtime_hour'] = pd.to_datetime(df['start']).dt.hour
    
    # Drop critical missing values
    df = df.dropna(subset=['sleep_performance_percentage', 'total_sleep_hours'])
    
    return df


def get_training_data(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list,
    test_size: float = 0.2,
    scale_features: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Optional[StandardScaler], Optional[SimpleImputer]]:
    """Prepare training and test datasets with preprocessing.
    
    Args:
        df: Source DataFrame
        target_col: Name of target column
        feature_cols: List of feature column names
        test_size: Fraction of data for testing (0.0-1.0)
        scale_features: Whether to standardize features
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test, scaler, imputer)
    """
    from sklearn.model_selection import train_test_split
    
    # Extract features and target
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Handle missing values
    imputer = SimpleImputer(strategy='median')
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
    df: pd.DataFrame,
    metric_col: str,
    window_sizes: list = [7, 14, 30]
) -> pd.DataFrame:
    """Calculate rolling averages and trends.
    
    Args:
        df: DataFrame with time series data
        metric_col: Column name to calculate rolling stats for
        window_sizes: List of window sizes in days
        
    Returns:
        DataFrame with additional rolling feature columns
    """
    df = df.sort_values('created_at')
    
    for window in window_sizes:
        df[f'{metric_col}_rolling_{window}d'] = df[metric_col].rolling(window=window, min_periods=1).mean()
        df[f'{metric_col}_std_{window}d'] = df[metric_col].rolling(window=window, min_periods=1).std()
    
    # Calculate trend (difference from rolling mean)
    df[f'{metric_col}_trend'] = df[metric_col] - df[f'{metric_col}_rolling_7d']
    
    return df
