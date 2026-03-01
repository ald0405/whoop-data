# v2.0.0 — From Data Display to Daily Decisions

## Overview

This release transforms the WHOOP Data Platform from a passive data viewer into an **active daily decision engine**. The homepage now delivers a personalised daily action card, a "What If?" scenario planner, and coaching-quality recommendations — all powered by your existing ML models and health data.

## New Features

### Daily Decision Engine (`whoopdata/services/daily_engine.py`)
- Generates a personalised daily action card on every homepage load
- Pulls latest recovery, sleep, HRV, and strain data
- Uses ML factor importance to explain **why** your recovery is what it is
- Produces 3–5 prioritised actions across training, sleep, recovery, and lifestyle
- Calculates a personalised sleep target based on your best recovery patterns
- Integrates weather, air quality, and transport context into recommendations

### Scenario Planner (`whoopdata/services/scenario_planner.py`)
- "What If?" slider widget on the homepage
- Adjust sleep hours, strain, and sleep efficiency to predict tomorrow's recovery
- Uses the trained RandomForest model with all 35 features (user inputs override median baselines)
- Returns predicted recovery score, confidence interval, recovery category, and plain-English verdict
- Supports side-by-side comparison of up to 5 scenarios via `POST /api/scenarios/compare`

### Weekly Coaching Report (`whoopdata/analytics/engine.py`)
- New `generate_coaching_report()` method on `InsightGenerator`
- Four sections: What Happened, What Worked, What To Change, Progress
- Available via `GET /api/reports/weekly` and the `/report` page

### Coaching Personas (`whoopdata/services/personas.py`)
- Three configurable coaching voices: Direct Coach, Gentle Guide, Data Scientist
- Each persona reframes the same data with a different tone and emphasis

### Lifecycle Coaching (`whoopdata/services/lifecycle.py`)
- Detects fitness phase from 28-day trends (building, maintaining, recovering, detraining)
- Adapts recommendations based on detected phase

### Adherence Tracking (`whoopdata/services/adherence_tracker.py`)
- Records daily recommendations and tracks follow-through
- Evaluates adherence and computes correlation with recovery outcomes
- New DB models: `Recommendation`, `RecommendationOutcome`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/daily-plan` | Personalised daily action card |
| POST | `/api/scenarios/recovery` | Single scenario prediction |
| POST | `/api/scenarios/compare` | Compare 2–5 scenarios |
| GET | `/api/reports/weekly` | Weekly coaching report |

## Homepage Transformation

The homepage (`/`) has been redesigned:
- **Recovery Banner** — score, category (green/yellow/red), key driver explanation, HRV
- **Daily Actions** — 3–5 prioritised action cards with reasoning
- **Sleep Target** — personalised hours and bedtime recommendation
- **"What If?" Planner** — interactive sliders for sleep, strain, and efficiency with live prediction
- **Context Panel** — weather, air quality, and transport status

## Bug Fixes

- Fixed scenario planner 404/503 errors caused by feature count mismatch (model trained on 35 features, planner was sending 8)
- `RecoveryPredictor.train()` now accepts and persists the actual training feature names
- Scenario endpoints return 503 (not 404) when the ML model hasn't been trained

## Tests

- 22 new tests in `tests/test_daily_engine.py` covering schemas, personas, action generation, and daily engine logic
- All 52 tests pass (22 new + 30 existing)

## Files Added
- `whoopdata/schemas/daily.py` — Pydantic models for daily plan and scenarios
- `whoopdata/services/daily_engine.py` — Core daily decision engine
- `whoopdata/services/scenario_planner.py` — What-if scenario predictions
- `whoopdata/services/adherence_tracker.py` — Recommendation tracking
- `whoopdata/services/personas.py` — Coaching persona templates
- `whoopdata/services/lifecycle.py` — Fitness phase detection
- `whoopdata/api/daily_routes.py` — Daily engine API routes
- `templates/weekly_report.html` — Coaching report page
- `tests/test_daily_engine.py` — New test suite

## Files Modified
- `main.py` — Added daily router and `/report` page route
- `templates/index.html` — Homepage redesign with daily action card and scenario planner
- `whoopdata/analytics/engine.py` — Added coaching report generation
- `whoopdata/analytics/models.py` — `train()` accepts feature names
- `whoopdata/models/models.py` — Added Recommendation and RecommendationOutcome models
- `whoopdata/pipelines/analytics_pipeline.py` — Passes feature names to predictor
