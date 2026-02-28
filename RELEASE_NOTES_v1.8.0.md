# Release Notes - v1.8.0

**Release Date:** February 28, 2026
**Release Type:** Feature Release - Multiple Linear Regression Analytics

---

## Overview

This release adds statistical modelling to the analytics platform. You can now run Multiple Linear Regression (MLR) models against your recovery and HRV data, view partial correlation charts, and explore a full correlation heatmap across all health metrics.

---

## New Features

### Multiple Linear Regression Models

Two new MLR models are available, both using statsmodels OLS:

- **Recovery MLR** - Models recovery score as a function of sleep duration, sleep efficiency, REM and deep sleep time, respiratory rate, skin temperature, and resting heart rate. Produces R-squared, coefficients, t-values, p-values, and partial correlations for each predictor.
- **HRV MLR** - Models HRV (RMSSD) as a function of similar sleep and physiological features, plus workout strain and zone data where available. Same statistical output as the recovery model.

Both models handle edge cases such as constant columns, insufficient data, and NaN values from outer joins.

### Correlation Heatmap

A full correlation matrix is now computed across all numeric health features. The dashboard renders it as an interactive heatmap with:

- Retina-quality rendering (2x DPR)
- Larger cell sizes for readability
- Horizontal scroll for wide matrices
- Color scale from -1 (inverse) to +1 (positive)

### Dashboard Integration

The analytics dashboard (`/analytics`) now includes three new sections:

- **MLR Coefficient Tables** - One table per model showing each predictor's coefficient, standard error, t-value, p-value, and partial correlation. Significant predictors (p < 0.05) are highlighted.
- **Partial Correlation Bar Charts** - Visual comparison of how strongly each predictor relates to the target after controlling for other variables.
- **Correlation Heatmap** - Full matrix of pairwise correlations across all health metrics.

### API Endpoints

Three new GET endpoints:

- `/analytics/recovery/mlr` - Recovery MLR model results
- `/analytics/hrv/mlr` - HRV MLR model results
- `/analytics/correlations/matrix` - Full correlation matrix

All return JSON with proper error handling and informative messages when data is insufficient.

### Analytics Pipeline

The pipeline (`make run`, option 6) now runs 11 tasks (up from 8). The three new steps are:

1. Compute Recovery MLR
2. Compute HRV MLR
3. Compute Correlation Matrix

Results are stored in the `analytics_results` table and served by the API.

---

## Bug Fixes

### Data Join Corrections

During integration testing, several issues were found and fixed in the data preparation layer. These were pre-existing problems, not regressions:

- **Sleep.cycle_id does not exist** - The Sleep model has no cycle_id column. Fixed by selecting Recovery.cycle_id through the join instead.
- **Sleep.total_light_sleep_time_milli does not exist** - Fixed by deriving light sleep time from total time in bed minus awake, no-data, slow wave, and REM times.
- **Incorrect join direction** - Queries starting from Sleep and joining Recovery caused errors. Fixed by querying from Recovery and joining Sleep, matching the pattern used elsewhere in the codebase.
- **NULL columns causing NaN in statsmodels** - Cycle columns (strain, max_heart_rate) are always NULL due to a separate FK mismatch. After fillna(0), these become constant, causing statsmodels to produce NaN for t-values and p-values. Fixed with a safe_float helper that replaces NaN and Inf with sensible defaults.
- **Missing fillna(0) after outer joins** - Without fillna, dropna removed all rows. Added fillna(0) in the data preparation step.

### JSON Serialisation

- Fixed NaN and Inf values breaking JSON responses. The API now returns valid JSON in all cases.

---

## Dependencies

- Added `statsmodels>=0.14.0` for OLS regression
- Added `loguru>=0.7.3` for structured logging

---

## Tests

Added `tests/test_mlr.py` with 30 unit tests covering:

- Data preparation (merge, dtype coercion, NaN handling, empty inputs)
- Model fitting (parameter counts, R-squared range, insufficient data, constant columns)
- Result extraction (keys, coefficient columns, p-value ranges, partial correlations, observation counts)
- Serialisation (plain types, JSON safety)
- HRV model (data prep, workout aggregation, fitting, optional features, serialisation)
- Edge cases (all-NaN columns, integer-as-object dtypes, empty DataFrames)
- Correlation matrix (square shape, value range)

---

## Known Issues

The following issues exist in the codebase and are not caused by this release:

- **Workout.cycle_id is NULL for all workouts** - The WHOOP Workout API does not return a cycle_id, and the ETL does not populate it. This causes "Insufficient workout data" in the Recovery Deep Dive section. A fix is planned for a future release.
- **Recovery.cycle_id does not match Cycle.id** - Recovery stores WHOOP API cycle IDs (large integers), but Cycle.id is auto-increment (1-852). There is zero overlap. The MLR module works around this with outer joins and fillna(0).
- **test_withings.py has a pre-existing import error** - Unrelated to this release.

---

## File Changes

New files:
- `whoopdata/analytics/mlr.py` - Core MLR module (~690 lines)
- `tests/test_mlr.py` - 30 unit tests

Modified files:
- `pyproject.toml` - Version bump, new dependencies
- `whoopdata/analytics/engine.py` - Added compute_correlation_matrix method
- `whoopdata/schemas/analytics.py` - Four new Pydantic models
- `whoopdata/api/analytics_routes.py` - Three new endpoints
- `whoopdata/pipelines/analytics_pipeline.py` - Three new pipeline steps
- `templates/analytics.html` - MLR tables, partial correlation charts, heatmap

---

## Migration Guide

### For Users

No breaking changes. After pulling the update:

```bash
uv sync          # Install new dependencies (statsmodels, loguru)
make run         # Select option 6 to run the analytics pipeline
```

The new MLR sections will appear on the analytics dashboard once the pipeline has run.

### For Developers

- The MLR module (`whoopdata/analytics/mlr.py`) is designed for testability. All functions accept DataFrames directly rather than database sessions.
- Run `uv run pytest tests/test_mlr.py -v` to verify the new tests pass.
- The analytics pipeline now has 11 tasks. If you have custom pipeline integrations, update any task count assertions.

---

## Credits

Co-Authored-By: Oz <oz-agent@warp.dev>
