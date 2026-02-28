"""Lightweight tests for MLR analysis module.

These tests use synthetic DataFrames (no live DB required) to verify:
- Data prep / merge logic and dtype coercion
- OLS model fitting and result extraction
- Edge cases: insufficient data, constant columns, NaN-heavy data
- Serialisation to JSON-safe dicts
- Correlation matrix computation
"""

import numpy as np
import pandas as pd
import pytest

from whoopdata.analytics.mlr import (
    _build_recovery_mlr_df,
    fit_recovery_mlr_model,
    get_recovery_model_results,
    mlr_results_to_dict,
    RECOVERY_FEATURE_COLS,
    _build_hrv_mlr_df,
    fit_hrv_mlr_model,
    get_hrv_model_results,
    HRV_CORE_FEATURES,
)


# ---------------------------------------------------------------------------
# Helpers to build synthetic DataFrames mimicking ORM output
# ---------------------------------------------------------------------------

N = 50  # default sample size


def _make_cycles(n: int = N) -> pd.DataFrame:
    """Mimic cycles table output from pd.read_sql."""
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "id": range(1, n + 1),
            "date": pd.date_range("2025-01-01", periods=n).date,
            "strain": rng.uniform(5, 18, n),
            "max_heart_rate": rng.integers(140, 190, n).astype(float),
            # Extra cols needed for HRV prep
            "average_heart_rate": rng.integers(60, 100, n).astype(float),
            "kilojoule": rng.uniform(5000, 15000, n),
        }
    )


def _make_recoveries(n: int = N) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "cycle_id": range(1, n + 1),
            "recovery_score": rng.uniform(20, 95, n),
            "hrv_rmssd_milli": rng.uniform(30, 120, n),
            "resting_heart_rate": rng.uniform(45, 65, n),
            "spo2_percentage": rng.uniform(94, 100, n),
            "skin_temp_celsius": rng.uniform(33, 37, n),
        }
    )


def _make_sleeps(n: int = N) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "cycle_id": range(1, n + 1),
            # Integer columns from ORM — could arrive as int64 or object
            "total_slow_wave_sleep_time_milli": rng.integers(3_000_000, 8_000_000, n),
            "total_rem_sleep_time_milli": rng.integers(3_000_000, 7_000_000, n),
            "total_light_sleep_time_milli": rng.integers(5_000_000, 12_000_000, n),
            "sleep_efficiency_percentage": rng.uniform(70, 98, n),
            "respiratory_rate": rng.uniform(12, 18, n),
            "sleep_consistency_percentage": rng.uniform(50, 95, n),
            "disturbance_count": rng.integers(0, 15, n),
        }
    )


def _make_workouts(n: int = N) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    # Not every day has a workout
    n_workouts = n // 2
    dates = pd.date_range("2025-01-01", periods=n).date
    workout_dates = rng.choice(dates, n_workouts, replace=False)
    return pd.DataFrame(
        {
            "cycle_id": range(1, n_workouts + 1),
            "date": workout_dates,
            "start": pd.to_datetime(workout_dates),
            "workout_strain_raw": rng.uniform(5, 18, n_workouts),
            "workout_kj_raw": rng.uniform(500, 3000, n_workouts),
            "workout_id": range(1, n_workouts + 1),
        }
    )


# ---------------------------------------------------------------------------
# Recovery MLR tests
# ---------------------------------------------------------------------------


class TestBuildRecoveryMLR:
    def test_basic_merge(self):
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        assert len(df) > 0
        for col in RECOVERY_FEATURE_COLS + ["recovery_score", "date"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_output_dtypes_are_numeric(self):
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        for col in RECOVERY_FEATURE_COLS:
            assert pd.api.types.is_numeric_dtype(df[col]), (
                f"Column {col} has dtype {df[col].dtype}, expected numeric"
            )

    def test_no_nan_in_core_features(self):
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        # After merge, feature cols should have no NaN (all synthetic data is complete)
        for col in ["deep_sleep_hrs", "rem_sleep_hrs", "hrv_rmssd_milli", "strain"]:
            assert df[col].notna().all(), f"Unexpected NaN in {col}"

    def test_empty_workouts_handled(self):
        empty_workouts = pd.DataFrame(columns=["cycle_id", "date", "start"])
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), empty_workouts
        )
        assert "had_workout" in df.columns
        assert (df["had_workout"] == 0).all()

    def test_object_dtype_columns_coerced(self):
        """Simulate ORM returning object-dtype numeric columns."""
        cycles = _make_cycles()
        cycles["strain"] = cycles["strain"].astype(str)  # Force object dtype
        recoveries = _make_recoveries()
        recoveries["recovery_score"] = recoveries["recovery_score"].astype(str)

        df = _build_recovery_mlr_df(cycles, recoveries, _make_sleeps(), _make_workouts())
        assert pd.api.types.is_numeric_dtype(df["strain"])
        assert pd.api.types.is_numeric_dtype(df["recovery_score"])

    def test_none_values_in_numeric_columns(self):
        """Simulate NaN/None in ORM columns."""
        recoveries = _make_recoveries()
        recoveries.loc[0:2, "recovery_score"] = None
        df = _build_recovery_mlr_df(
            _make_cycles(), recoveries, _make_sleeps(), _make_workouts()
        )
        # Should still produce a DataFrame (NaN rows will be dropped during fit)
        assert len(df) > 0


class TestFitRecoveryMLR:
    def _make_df(self):
        return _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )

    def test_fit_returns_model(self):
        df = self._make_df()
        model, df_model = fit_recovery_mlr_model(df)
        assert model is not None
        assert len(df_model) >= 10

    def test_model_params_length(self):
        df = self._make_df()
        model, _ = fit_recovery_mlr_model(df)
        # params should be len(features) + 1 (intercept)
        assert len(model.params) == len(RECOVERY_FEATURE_COLS) + 1

    def test_r_squared_range(self):
        df = self._make_df()
        model, _ = fit_recovery_mlr_model(df)
        assert 0 <= model.rsquared <= 1

    def test_insufficient_data_returns_none(self):
        """DataFrame with fewer rows than min_observations."""
        df = self._make_df().head(5)
        model, df_model = fit_recovery_mlr_model(df, min_observations=10)
        assert model is None
        assert len(df_model) <= 5

    def test_constant_column_no_crash(self):
        """A feature with zero variance should not crash (we protect against zero std)."""
        df = self._make_df()
        df["had_workout"] = 0  # constant column
        model, _ = fit_recovery_mlr_model(df)
        assert model is not None


class TestGetRecoveryResults:
    def _fit(self):
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        model, df_model = fit_recovery_mlr_model(df)
        return model, df_model

    def test_result_keys(self):
        model, df_model = self._fit()
        results = get_recovery_model_results(model, df_model)
        expected = {
            "model", "y", "y_pred", "residuals", "coef_df",
            "partial_corr_df", "n_observations", "r_squared", "adj_r_squared",
        }
        assert expected.issubset(results.keys())

    def test_coef_df_columns(self):
        model, df_model = self._fit()
        results = get_recovery_model_results(model, df_model)
        coef_df = results["coef_df"]
        for col in ["Feature", "Coefficient", "Std Error", "t-value", "P-value", "Significant", "CI Lower", "CI Upper"]:
            assert col in coef_df.columns, f"Missing coef_df column: {col}"

    def test_p_values_in_range(self):
        model, df_model = self._fit()
        results = get_recovery_model_results(model, df_model)
        p_vals = results["coef_df"]["P-value"]
        assert (p_vals >= 0).all()
        assert (p_vals <= 1).all()

    def test_partial_corr_in_range(self):
        model, df_model = self._fit()
        results = get_recovery_model_results(model, df_model)
        pc_vals = results["partial_corr_df"]["Partial Correlation"]
        assert (pc_vals >= -1).all()
        assert (pc_vals <= 1).all()

    def test_n_observations(self):
        model, df_model = self._fit()
        results = get_recovery_model_results(model, df_model)
        assert results["n_observations"] == len(df_model)


class TestMLRSerialisation:
    def test_serialisation_produces_plain_types(self):
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        model, df_model = fit_recovery_mlr_model(df)
        results = get_recovery_model_results(model, df_model)
        serialised = mlr_results_to_dict(results)

        assert isinstance(serialised["coefficients"], list)
        assert isinstance(serialised["r_squared"], float)
        assert isinstance(serialised["n_observations"], int)
        # Check individual coefficient row types
        row = serialised["coefficients"][0]
        assert isinstance(row["feature"], str)
        assert isinstance(row["coefficient"], float)
        assert isinstance(row["significant"], bool)

    def test_serialisation_is_json_safe(self):
        import json

        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        model, df_model = fit_recovery_mlr_model(df)
        results = get_recovery_model_results(model, df_model)
        serialised = mlr_results_to_dict(results)

        # Should not raise
        json_str = json.dumps(serialised)
        assert len(json_str) > 0


# ---------------------------------------------------------------------------
# HRV MLR tests
# ---------------------------------------------------------------------------


class TestBuildHRVMLR:
    def test_basic_merge(self):
        cycles = _make_cycles()
        recoveries = _make_recoveries()
        sleeps = _make_sleeps()
        workouts = _make_workouts()
        df = _build_hrv_mlr_df(cycles, recoveries, sleeps, workouts)
        assert len(df) > 0
        for col in HRV_CORE_FEATURES:
            assert col in df.columns, f"Missing column: {col}"

    def test_workout_aggregation(self):
        df = _build_hrv_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        assert "workout_strain" in df.columns
        assert pd.api.types.is_numeric_dtype(df["workout_strain"])


class TestFitHRVMLR:
    def _make_df(self):
        return _build_hrv_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )

    def test_fit_returns_model(self):
        df = self._make_df()
        model, df_model, available_optional = fit_hrv_mlr_model(df)
        assert model is not None
        assert len(df_model) >= 10

    def test_available_optional_features(self):
        df = self._make_df()
        _, _, available_optional = fit_hrv_mlr_model(df)
        # Our synthetic data has disturbance_count and spo2_percentage
        assert isinstance(available_optional, list)

    def test_insufficient_data(self):
        df = self._make_df().head(3)
        model, _, _ = fit_hrv_mlr_model(df, min_observations=10)
        assert model is None


class TestGetHRVResults:
    def test_result_keys(self):
        df = _build_hrv_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        model, df_model, available_optional = fit_hrv_mlr_model(df)
        results = get_hrv_model_results(model, df_model, available_optional)
        assert "coef_df" in results
        assert "partial_corr_df" in results
        assert "r_squared" in results
        assert "adj_r_squared" in results

    def test_serialisation(self):
        import json

        df = _build_hrv_mlr_df(
            _make_cycles(), _make_recoveries(), _make_sleeps(), _make_workouts()
        )
        model, df_model, available_optional = fit_hrv_mlr_model(df)
        results = get_hrv_model_results(model, df_model, available_optional)
        serialised = mlr_results_to_dict(results)
        json_str = json.dumps(serialised)
        assert len(json_str) > 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_all_nan_column_in_sleep(self):
        """Simulate a sleep column being entirely NaN after merge.

        With fillna(0) in the coerce step, NaN becomes 0 (constant column).
        The model should still fit — zero-std protection handles constant features.
        """
        sleeps = _make_sleeps()
        sleeps["total_slow_wave_sleep_time_milli"] = np.nan
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), sleeps, _make_workouts()
        )
        # deep_sleep_hrs will be 0 (constant) due to fillna(0)
        model, df_model = fit_recovery_mlr_model(df)
        assert model is not None
        assert len(df_model) > 0

    def test_integer_columns_as_object(self):
        """ORM can return Integer columns as object dtype."""
        sleeps = _make_sleeps()
        sleeps["total_rem_sleep_time_milli"] = sleeps["total_rem_sleep_time_milli"].astype(object)
        df = _build_recovery_mlr_df(
            _make_cycles(), _make_recoveries(), sleeps, _make_workouts()
        )
        assert pd.api.types.is_numeric_dtype(df["rem_sleep_hrs"])

    def test_empty_dataframes(self):
        """All tables empty."""
        empty_cycles = pd.DataFrame(columns=["id", "date", "strain", "max_heart_rate"])
        empty_recoveries = pd.DataFrame(
            columns=["cycle_id", "recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]
        )
        empty_sleeps = pd.DataFrame(
            columns=[
                "cycle_id",
                "total_slow_wave_sleep_time_milli",
                "total_rem_sleep_time_milli",
                "total_light_sleep_time_milli",
                "sleep_efficiency_percentage",
            ]
        )
        empty_workouts = pd.DataFrame(columns=["cycle_id", "date", "start"])

        df = _build_recovery_mlr_df(empty_cycles, empty_recoveries, empty_sleeps, empty_workouts)
        assert len(df) == 0
        model, _ = fit_recovery_mlr_model(df)
        assert model is None


# ---------------------------------------------------------------------------
# Correlation matrix tests (uses compute_correlation_matrix logic directly)
# ---------------------------------------------------------------------------


class TestCorrelationMatrix:
    def test_matrix_is_square(self):
        """Test that correlation matrix output is square with diag == 1."""
        # Build a simple numeric DataFrame similar to what the method uses
        rng = np.random.default_rng(42)
        n = 30
        df = pd.DataFrame(
            {
                "recovery_score": rng.uniform(20, 95, n),
                "sleep_hours": rng.uniform(5, 9, n),
                "hrv_rmssd_milli": rng.uniform(30, 120, n),
                "resting_heart_rate": rng.uniform(45, 65, n),
                "strain": rng.uniform(5, 18, n),
            }
        )
        corr = df.corr()
        matrix = corr.values

        assert matrix.shape[0] == matrix.shape[1]
        # Diagonal should be 1.0
        for i in range(matrix.shape[0]):
            assert abs(matrix[i][i] - 1.0) < 1e-10

    def test_values_in_range(self):
        rng = np.random.default_rng(42)
        n = 30
        df = pd.DataFrame(
            {
                "a": rng.uniform(0, 1, n),
                "b": rng.uniform(0, 1, n),
                "c": rng.uniform(0, 1, n),
            }
        )
        corr = df.corr()
        assert (corr.values >= -1).all()
        assert (corr.values <= 1).all()
