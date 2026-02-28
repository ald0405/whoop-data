"""Multiple Linear Regression (MLR) analysis for health metrics.

Provides OLS-based models for Recovery and HRV prediction with:
- Standardised coefficients for comparing feature importance
- Per-feature p-values and significance flags
- Confidence intervals
- Partial correlations (independent contribution of each feature)

Functions are split into prepare / fit / results stages.
The prepare functions accept a DB session for production use,
but fit and results functions accept DataFrames directly for testability.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple

from whoopdata.models.models import Recovery, Sleep, Cycle, Workout


# ---------------------------------------------------------------------------
# Feature label mappings (internal col name -> human-readable)
# ---------------------------------------------------------------------------

RECOVERY_FEATURE_LABELS = {
    "deep_sleep_hrs": "Deep Sleep (hrs)",
    "rem_sleep_hrs": "REM Sleep (hrs)",
    "hrv_rmssd_milli": "HRV (ms)",
    "max_heart_rate": "Max HR (bpm)",
    "strain": "Strain",
    "had_workout": "Had Workout",
}

HRV_FEATURE_LABELS = {
    "deep_sleep_hrs": "Deep Sleep (hrs)",
    "rem_sleep_hrs": "REM Sleep (hrs)",
    "total_sleep_hrs": "Total Sleep (hrs)",
    "sleep_efficiency_percentage": "Sleep Efficiency (%)",
    "resting_heart_rate": "Resting HR (bpm)",
    "respiratory_rate": "Respiratory Rate",
    "workout_strain": "Workout Strain",
    "day_strain": "Day Strain",
    "spo2_percentage": "SpO2 (%)",
    "skin_temp_celsius": "Skin Temp (°C)",
    "disturbance_count": "Disturbances",
}


# ============================= Recovery MLR =================================


def prepare_recovery_mlr_data(db: Session) -> pd.DataFrame:
    """Query and merge cycles, recoveries, sleeps, workouts into MLR-ready DataFrame.

    Uses Recovery as the hub table (it links to both Cycle and Sleep).

    Args:
        db: SQLAlchemy session

    Returns:
        DataFrame with engineered features ready for ``fit_recovery_mlr_model``
    """
    # Single query using Recovery as hub, matching pattern in data_prep.py
    base_df = pd.read_sql(
        db.query(
            Recovery.cycle_id,
            Recovery.created_at,
            Recovery.recovery_score,
            Recovery.hrv_rmssd_milli,
            Recovery.resting_heart_rate,
            Cycle.strain,
            Cycle.max_heart_rate,
            Cycle.start.label("cycle_start"),
            Sleep.total_slow_wave_sleep_time_milli,
            Sleep.total_rem_sleep_time_milli,
            Sleep.total_time_in_bed_time_milli,
            Sleep.total_awake_time_milli,
            Sleep.total_no_data_time_milli,
            Sleep.sleep_efficiency_percentage,
        )
        .join(Sleep, Recovery.sleep_id == Sleep.id, isouter=True)
        .join(Cycle, Recovery.cycle_id == Cycle.id, isouter=True)
        .filter(Recovery.recovery_score.isnot(None))
        .statement,
        db.bind,
    )

    # Derive light sleep
    for c in [
        "total_time_in_bed_time_milli", "total_awake_time_milli",
        "total_no_data_time_milli", "total_slow_wave_sleep_time_milli",
        "total_rem_sleep_time_milli",
    ]:
        base_df[c] = pd.to_numeric(base_df[c], errors="coerce").fillna(0)

    base_df["total_light_sleep_time_milli"] = (
        base_df["total_time_in_bed_time_milli"]
        - base_df["total_awake_time_milli"]
        - base_df["total_no_data_time_milli"]
        - base_df["total_slow_wave_sleep_time_milli"]
        - base_df["total_rem_sleep_time_milli"]
    ).clip(lower=0)

    # Add date column for workout matching
    base_df["date"] = pd.to_datetime(
        base_df["cycle_start"].fillna(base_df["created_at"])
    ).dt.date

    # Rename to match _build_recovery_mlr_df expectations
    base_df["id"] = base_df["cycle_id"]

    workouts_df = pd.read_sql(
        db.query(Workout.cycle_id, Workout.start).statement,
        db.bind,
    )
    if not workouts_df.empty and "start" in workouts_df.columns:
        workouts_df["date"] = pd.to_datetime(workouts_df["start"]).dt.date

    return _build_recovery_mlr_df(base_df, base_df, base_df, workouts_df)


def _build_recovery_mlr_df(
    cycles_df: pd.DataFrame,
    recoveries_df: pd.DataFrame,
    sleeps_df: pd.DataFrame,
    workouts_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge and engineer features from raw table DataFrames.

    This is the testable core — accepts DataFrames rather than a DB session.
    """
    # --- Coerce dtypes (ORM Integer cols can arrive as object) -----------
    # Cycle-derived columns may be NULL due to FK mismatch; fillna(0) matches data_prep.py
    for col in ["strain", "max_heart_rate"]:
        if col in cycles_df.columns:
            cycles_df[col] = pd.to_numeric(cycles_df[col], errors="coerce").fillna(0)

    for col in ["recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]:
        if col in recoveries_df.columns:
            recoveries_df[col] = pd.to_numeric(recoveries_df[col], errors="coerce")

    int_cols = [
        "total_slow_wave_sleep_time_milli",
        "total_rem_sleep_time_milli",
        "total_light_sleep_time_milli",
    ]
    for col in int_cols:
        if col in sleeps_df.columns:
            sleeps_df[col] = pd.to_numeric(sleeps_df[col], errors="coerce").fillna(0)
    if "sleep_efficiency_percentage" in sleeps_df.columns:
        sleeps_df["sleep_efficiency_percentage"] = pd.to_numeric(
            sleeps_df["sleep_efficiency_percentage"], errors="coerce"
        ).fillna(0)

    # --- Merge -----------------------------------------------------------
    df = (
        cycles_df[["id", "date", "strain", "max_heart_rate"]]
        .merge(
            recoveries_df[["cycle_id", "recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_df[
                [
                    "cycle_id",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_light_sleep_time_milli",
                    "sleep_efficiency_percentage",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
            suffixes=("", "_sleep"),
        )
    )

    # --- Workout flag ----------------------------------------------------
    if not workouts_df.empty and "date" in workouts_df.columns:
        workout_dates = set(workouts_df["date"].dropna())
        df["had_workout"] = df["date"].isin(workout_dates).astype(int)
    else:
        df["had_workout"] = 0

    # --- Derived features ------------------------------------------------
    df["deep_sleep_hrs"] = pd.to_numeric(
        df["total_slow_wave_sleep_time_milli"], errors="coerce"
    ) / 3_600_000
    df["rem_sleep_hrs"] = pd.to_numeric(
        df["total_rem_sleep_time_milli"], errors="coerce"
    ) / 3_600_000
    df["total_sleep_hrs"] = (
        pd.to_numeric(df["total_slow_wave_sleep_time_milli"], errors="coerce")
        + pd.to_numeric(df["total_rem_sleep_time_milli"], errors="coerce")
        + pd.to_numeric(df["total_light_sleep_time_milli"], errors="coerce")
    ) / 3_600_000

    return df


# ---- Fit & results ------------------------------------------------------


RECOVERY_FEATURE_COLS = [
    "deep_sleep_hrs",
    "rem_sleep_hrs",
    "hrv_rmssd_milli",
    "max_heart_rate",
    "strain",
    "had_workout",
]


def fit_recovery_mlr_model(
    df_mlr: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    target_col: str = "recovery_score",
    min_observations: int = 10,
) -> Tuple[Optional[sm.regression.linear_model.RegressionResultsWrapper], pd.DataFrame]:
    """Fit a standardised OLS model for recovery prediction.

    Args:
        df_mlr: DataFrame from ``prepare_recovery_mlr_data`` or ``_build_recovery_mlr_df``
        feature_cols: Feature column names (defaults to RECOVERY_FEATURE_COLS)
        target_col: Target column name
        min_observations: Minimum rows required to fit

    Returns:
        (fitted_model_or_None, df_model) — model is None if insufficient data
    """
    if feature_cols is None:
        feature_cols = RECOVERY_FEATURE_COLS

    df_model = df_mlr[feature_cols + [target_col, "date"]].dropna()

    if len(df_model) < min_observations:
        return None, df_model

    X = df_model[feature_cols].astype(float)
    y = df_model[target_col].astype(float)

    # Standardise — protect against zero-std columns
    stds = X.std()
    safe_stds = stds.replace(0, 1)
    X_std = (X - X.mean()) / safe_stds
    X_std = sm.add_constant(X_std)

    model = sm.OLS(y, X_std).fit()
    return model, df_model


def get_recovery_model_results(
    model: sm.regression.linear_model.RegressionResultsWrapper,
    df_model: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    target_col: str = "recovery_score",
    feature_labels: Optional[Dict[str, str]] = None,
) -> Dict:
    """Extract comprehensive results from a fitted recovery OLS model.

    Returns dict with keys: model, y, y_pred, residuals, coef_df,
    partial_corr_df, n_observations, r_squared, adj_r_squared.
    """
    if feature_cols is None:
        feature_cols = RECOVERY_FEATURE_COLS
    if feature_labels is None:
        feature_labels = RECOVERY_FEATURE_LABELS

    X = df_model[feature_cols].astype(float)
    y = df_model[target_col].astype(float)

    stds = X.std()
    safe_stds = stds.replace(0, 1)
    X_std = (X - X.mean()) / safe_stds
    X_std = sm.add_constant(X_std)

    y_pred = model.predict(X_std)
    residuals = y - y_pred

    # Coefficient table
    labels = ["Intercept"] + [feature_labels.get(f, f) for f in feature_cols]
    coef_df = pd.DataFrame(
        {
            "Feature": labels,
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "t-value": model.tvalues.values,
            "P-value": model.pvalues.values,
        }
    )
    coef_df["Significant"] = coef_df["P-value"] < 0.05
    coef_df["CI Lower"] = model.conf_int()[0].values
    coef_df["CI Upper"] = model.conf_int()[1].values

    # Partial correlations
    df_resid = model.df_resid
    partial_corrs = []
    for i in range(len(feature_cols)):
        t_val = model.tvalues.iloc[i + 1]
        partial_r = t_val / np.sqrt(t_val**2 + df_resid)
        partial_corrs.append(float(partial_r))

    partial_corr_df = pd.DataFrame(
        {
            "Feature": [feature_labels.get(f, f) for f in feature_cols],
            "Partial Correlation": partial_corrs,
        }
    )

    return {
        "model": model,
        "y": y,
        "y_pred": y_pred,
        "residuals": residuals,
        "coef_df": coef_df,
        "partial_corr_df": partial_corr_df,
        "n_observations": len(df_model),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
    }


# ================================ HRV MLR ==================================


HRV_CORE_FEATURES = [
    "deep_sleep_hrs",
    "rem_sleep_hrs",
    "total_sleep_hrs",
    "sleep_efficiency_percentage",
    "resting_heart_rate",
    "respiratory_rate",
    "workout_strain",
    "day_strain",
]

HRV_OPTIONAL_FEATURES = ["spo2_percentage", "skin_temp_celsius", "disturbance_count"]


def prepare_hrv_mlr_data(db: Session) -> pd.DataFrame:
    """Query and merge data for HRV MLR analysis.

    Uses Recovery as the hub table (it links to both Cycle and Sleep).

    Args:
        db: SQLAlchemy session

    Returns:
        DataFrame ready for ``fit_hrv_mlr_model``
    """
    # Single query using Recovery as hub
    base_df = pd.read_sql(
        db.query(
            Recovery.cycle_id,
            Recovery.created_at,
            Recovery.hrv_rmssd_milli,
            Recovery.resting_heart_rate,
            Recovery.spo2_percentage,
            Recovery.skin_temp_celsius,
            Cycle.strain,
            Cycle.max_heart_rate,
            Cycle.average_heart_rate,
            Cycle.kilojoule,
            Cycle.start.label("cycle_start"),
            Sleep.total_slow_wave_sleep_time_milli,
            Sleep.total_rem_sleep_time_milli,
            Sleep.total_time_in_bed_time_milli,
            Sleep.total_awake_time_milli,
            Sleep.total_no_data_time_milli,
            Sleep.sleep_efficiency_percentage,
            Sleep.respiratory_rate,
            Sleep.sleep_consistency_percentage,
            Sleep.disturbance_count,
        )
        .join(Sleep, Recovery.sleep_id == Sleep.id, isouter=True)
        .join(Cycle, Recovery.cycle_id == Cycle.id, isouter=True)
        .filter(Recovery.hrv_rmssd_milli.isnot(None))
        .statement,
        db.bind,
    )

    # Derive light sleep
    for c in [
        "total_time_in_bed_time_milli", "total_awake_time_milli",
        "total_no_data_time_milli", "total_slow_wave_sleep_time_milli",
        "total_rem_sleep_time_milli",
    ]:
        base_df[c] = pd.to_numeric(base_df[c], errors="coerce").fillna(0)

    base_df["total_light_sleep_time_milli"] = (
        base_df["total_time_in_bed_time_milli"]
        - base_df["total_awake_time_milli"]
        - base_df["total_no_data_time_milli"]
        - base_df["total_slow_wave_sleep_time_milli"]
        - base_df["total_rem_sleep_time_milli"]
    ).clip(lower=0)

    # Add date column
    base_df["date"] = pd.to_datetime(
        base_df["cycle_start"].fillna(base_df["created_at"])
    ).dt.date

    # Rename to match _build_hrv_mlr_df expectations
    base_df["id"] = base_df["cycle_id"]

    workouts_df = pd.read_sql(
        db.query(
            Workout.cycle_id,
            Workout.start,
            Workout.strain.label("workout_strain_raw"),
            Workout.kilojoule.label("workout_kj_raw"),
            Workout.id.label("workout_id"),
        ).statement,
        db.bind,
    )
    if not workouts_df.empty and "start" in workouts_df.columns:
        workouts_df["date"] = pd.to_datetime(workouts_df["start"]).dt.date

    return _build_hrv_mlr_df(base_df, base_df, base_df, workouts_df)


def _build_hrv_mlr_df(
    cycles_df: pd.DataFrame,
    recoveries_df: pd.DataFrame,
    sleeps_df: pd.DataFrame,
    workouts_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge and engineer features for HRV MLR.  Testable core."""

    # --- Coerce dtypes ---------------------------------------------------
    # Cycle-derived columns may be NULL due to FK mismatch; fillna(0) matches data_prep.py
    for col in ["strain", "max_heart_rate", "average_heart_rate", "kilojoule"]:
        if col in cycles_df.columns:
            cycles_df[col] = pd.to_numeric(cycles_df[col], errors="coerce").fillna(0)

    for col in ["hrv_rmssd_milli", "resting_heart_rate", "spo2_percentage", "skin_temp_celsius"]:
        if col in recoveries_df.columns:
            recoveries_df[col] = pd.to_numeric(recoveries_df[col], errors="coerce")

    for col in [
        "total_slow_wave_sleep_time_milli",
        "total_rem_sleep_time_milli",
        "total_light_sleep_time_milli",
        "sleep_efficiency_percentage",
        "respiratory_rate",
        "disturbance_count",
    ]:
        if col in sleeps_df.columns:
            sleeps_df[col] = pd.to_numeric(sleeps_df[col], errors="coerce").fillna(0)

    # --- Merge -----------------------------------------------------------
    df = (
        cycles_df[["id", "date", "strain", "max_heart_rate", "average_heart_rate", "kilojoule"]]
        .rename(columns={"strain": "day_strain"})
        .merge(
            recoveries_df[
                [
                    "cycle_id",
                    "hrv_rmssd_milli",
                    "resting_heart_rate",
                    "spo2_percentage",
                    "skin_temp_celsius",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_df[
                [
                    "cycle_id",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_light_sleep_time_milli",
                    "sleep_efficiency_percentage",
                    "respiratory_rate",
                    "disturbance_count",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
            suffixes=("", "_sleep"),
        )
    )

    # --- Workout aggregation ---------------------------------------------
    if not workouts_df.empty and "date" in workouts_df.columns:
        for col in ["workout_strain_raw", "workout_kj_raw"]:
            if col in workouts_df.columns:
                workouts_df[col] = pd.to_numeric(workouts_df[col], errors="coerce")

        workout_agg = (
            workouts_df.groupby("date")
            .agg(
                workout_strain=("workout_strain_raw", "sum"),
                workout_kilojoule=("workout_kj_raw", "sum"),
                workout_count=("workout_id", "count"),
            )
            .reset_index()
        )
        df = df.merge(workout_agg, on="date", how="left")
        df["workout_strain"] = df["workout_strain"].fillna(0)
        df["workout_kilojoule"] = df["workout_kilojoule"].fillna(0)
        df["workout_count"] = df["workout_count"].fillna(0).astype(int)
    else:
        df["workout_strain"] = 0
        df["workout_kilojoule"] = 0
        df["workout_count"] = 0

    # --- Derived features ------------------------------------------------
    df["deep_sleep_hrs"] = pd.to_numeric(
        df["total_slow_wave_sleep_time_milli"], errors="coerce"
    ) / 3_600_000
    df["rem_sleep_hrs"] = pd.to_numeric(
        df["total_rem_sleep_time_milli"], errors="coerce"
    ) / 3_600_000
    df["total_sleep_hrs"] = (
        pd.to_numeric(df["total_slow_wave_sleep_time_milli"], errors="coerce")
        + pd.to_numeric(df["total_rem_sleep_time_milli"], errors="coerce")
        + pd.to_numeric(df["total_light_sleep_time_milli"], errors="coerce")
    ) / 3_600_000

    return df


def fit_hrv_mlr_model(
    df_mlr_hrv: pd.DataFrame,
    min_observations: int = 10,
) -> Tuple[
    Optional[sm.regression.linear_model.RegressionResultsWrapper],
    pd.DataFrame,
    List[str],
]:
    """Fit a standardised OLS model for HRV prediction.

    Automatically detects which optional features have enough data.

    Returns:
        (model_or_None, df_model, available_optional_features)
    """
    available_optional: List[str] = []
    for feat in HRV_OPTIONAL_FEATURES:
        if feat in df_mlr_hrv.columns:
            non_null = df_mlr_hrv[feat].notna().sum()
            if non_null >= min_observations:
                available_optional.append(feat)

    feature_cols = HRV_CORE_FEATURES + available_optional
    target_col = "hrv_rmssd_milli"

    df_model = df_mlr_hrv[feature_cols + [target_col, "date"]].dropna()

    if len(df_model) < min_observations:
        return None, df_model, available_optional

    X = df_model[feature_cols].astype(float)
    y = df_model[target_col].astype(float)

    stds = X.std()
    safe_stds = stds.replace(0, 1)
    X_std = (X - X.mean()) / safe_stds
    X_std = sm.add_constant(X_std)

    model = sm.OLS(y, X_std).fit()
    return model, df_model, available_optional


def get_hrv_model_results(
    model: sm.regression.linear_model.RegressionResultsWrapper,
    df_model: pd.DataFrame,
    available_optional: List[str],
) -> Dict:
    """Extract comprehensive results from a fitted HRV OLS model."""
    feature_cols = HRV_CORE_FEATURES + available_optional
    target_col = "hrv_rmssd_milli"

    X = df_model[feature_cols].astype(float)
    y = df_model[target_col].astype(float)

    stds = X.std()
    safe_stds = stds.replace(0, 1)
    X_std = (X - X.mean()) / safe_stds
    X_std = sm.add_constant(X_std)

    y_pred = model.predict(X_std)
    residuals = y - y_pred

    labels = ["Intercept"] + [HRV_FEATURE_LABELS.get(f, f) for f in feature_cols]
    coef_df = pd.DataFrame(
        {
            "Feature": labels,
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "t-value": model.tvalues.values,
            "P-value": model.pvalues.values,
        }
    )
    coef_df["Significant"] = coef_df["P-value"] < 0.05
    coef_df["CI Lower"] = model.conf_int()[0].values
    coef_df["CI Upper"] = model.conf_int()[1].values

    df_resid = model.df_resid
    partial_corrs = []
    for i in range(len(feature_cols)):
        t_val = model.tvalues.iloc[i + 1]
        partial_r = t_val / np.sqrt(t_val**2 + df_resid)
        partial_corrs.append(float(partial_r))

    partial_corr_df = pd.DataFrame(
        {
            "Feature": [HRV_FEATURE_LABELS.get(f, f) for f in feature_cols],
            "Partial Correlation": partial_corrs,
        }
    )

    return {
        "model": model,
        "y": y,
        "y_pred": y_pred,
        "residuals": residuals,
        "coef_df": coef_df,
        "partial_corr_df": partial_corr_df,
        "n_observations": len(df_model),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "available_optional": available_optional,
    }


# ======================== Serialisation helpers =============================


def _safe_float(val: float, default: float = 0.0) -> float:
    """Convert to float, replacing NaN/Inf with a default."""
    f = float(val)
    if np.isnan(f) or np.isinf(f):
        return default
    return f


def mlr_results_to_dict(results: Dict) -> Dict:
    """Convert MLR results to a JSON-serialisable dictionary.

    Strips the statsmodels model object and pandas objects,
    keeping only plain Python types suitable for storage in analytics_results.
    NaN/Inf values (e.g. from constant-column features) are replaced with 0.0.
    """
    coef_rows = []
    for _, row in results["coef_df"].iterrows():
        coef_rows.append(
            {
                "feature": str(row["Feature"]),
                "coefficient": _safe_float(row["Coefficient"]),
                "std_error": _safe_float(row["Std Error"]),
                "t_value": _safe_float(row["t-value"]),
                "p_value": _safe_float(row["P-value"], 1.0),
                "significant": bool(row["Significant"]) if not pd.isna(row["Significant"]) else False,
                "ci_lower": _safe_float(row["CI Lower"]),
                "ci_upper": _safe_float(row["CI Upper"]),
            }
        )

    partial_corr_rows = []
    for _, row in results["partial_corr_df"].iterrows():
        partial_corr_rows.append(
            {
                "feature": str(row["Feature"]),
                "partial_correlation": _safe_float(row["Partial Correlation"]),
            }
        )

    return {
        "coefficients": coef_rows,
        "partial_correlations": partial_corr_rows,
        "r_squared": _safe_float(results["r_squared"]),
        "adj_r_squared": _safe_float(results["adj_r_squared"]),
        "n_observations": int(results["n_observations"]),
    }
