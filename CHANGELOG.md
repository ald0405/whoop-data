# Changelog

All notable changes to the WHOOP Data Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [3.10.0] - 2026-06-03

### Added
- Phase-strip frame selection for tennis groundstrokes: `segment_stroke_phases()` carves each detected forehand/backhand into an ordered strip (preparation -> backswing -> forward swing -> contact -> follow-through). The best and worst rep are sent to the LLM as ~8-12 phase-labelled annotated frames instead of a single peak frame.
- New `whoopdata/agent/reference_angles.py` -- single source of truth for phase-keyed reference *bands* (not point targets), consumed by both the overlay and the prompt. Forehand bands are literature-anchored (contact elbow 100-130 deg, grip-dependent); backhand bands are wider/low-confidence.
- Kinetic-chain timing (`_kinetic_chain_order`): orders hip -> shoulder -> elbow -> wrist by peak-speed time and flags arm-led sequencing. Measurable from 2D even where rotation magnitude is not.
- Soft warnings + orientation gate: low pose-detection ratio, no strokes detected (evenly-spaced fallback strip), single-rep, and a warning when the racket arm is on the occluded far side. Warnings are shown to the user and injected into the prompt so coaching hedges its confidence.
- `/videotips` Telegram command and a once-per-chat first-video hint with filming guidance (10-30s, side-on with the racket arm to camera, full body, 60 fps, caption the shot).
- New tests in `tests/test_pose_analysis.py` covering phase segmentation, kinetic-chain ordering, band lookups/deviation, aggregation strips, orientation, and phase-aware prompt text.

### Changed
- The video pipeline now sends an ordered phase strip per selected rep rather than a single peak frame; `AggregatedMetrics` gains `key_phase_strips`, `pose_detection_ratio`, and `warnings`, and `RepMetrics` gains `phase_frames` and kinetic-chain fields.
- Reference angles consolidated: removed the duplicated `telegram_bot._REFERENCE_ANGLES`/`_get_reference_angles` in favour of `reference_angles.get_phase_reference`. Overlay deviation is now computed against acceptable bands (zero inside the band).
- Biomechanics prompt (`biomechanics_sub_agent.md`) gains forehand/backhand phase sections, instructs the model to reason across the phase strip, treats the contact frame as approximate (~5 ms contact vs 30 fps), and forbids presenting rotation (e.g. shoulder-hip separation) as a measured fault.

### Notes
- Reference angle bands are **provisional and flagged for SME review**: forehand is anchored to the literature; backhand joint angles are sparsely quantified and graded on fewer joints at lower confidence.

## [3.9.0] - 2026-04-12

### Added
- Added explicit routing/tool-wiring regression assertions in `tests/test_agent_architecture.py` covering:
  - `manage_memory` and `get_top_recoveries` presence in `TOOLS_BY_NAME`
  - supervisor direct-tool exclusions for protein recommendation routing
  - specialist ownership and biomechanics toolset invariants
- Expanded `whoopdata/agent/README.md` with a high-level tool-surface overview and clearer routing ownership notes.

### Changed
- Registered `manage_memory` in `TOOLS_BY_NAME` so specialists referencing it resolve correctly.
- Exposed `get_top_recoveries` through `AVAILABLE_TOOLS` and `health_data` specialist configuration.
- Consolidated protein recommendation routing by removing direct supervisor access and routing this domain through the nutrition specialist.
- Tightened specialist boundary language in registry/prompt guidance for overlap intents (metrics vs coaching, nutrition vs behaviour change).
- Expanded biomechanics specialist tooling to include workout-context data tools.
- Aligned specialist temperature defaults to `0.1` for improved response-path consistency.
- Increased exercise and behaviour-change `max_output_tokens` to reduce truncation risk for richer planning responses.
## [3.8.0] - 2026-03-30

### Added
- MediaPipe Pose Lite integration for local biomechanics computation. Processes up to 600 dense video frames with temporal tracking in VIDEO mode -- the LLM now receives computed joint angle measurements instead of trying to eyeball pixels.
- Pluggable activity detection: `TennisDetector` (shoulder + wrist speed peaks for serves and groundstrokes) and `GymDetector` (knee angle valleys for squat reps). Each returns typed `EventWindow` objects.
- Multi-rep analysis: per-rep joint angles, cross-rep aggregation (mean, SD, consistency), fatigue drift detection, best/worst rep selection.
- Colour-coded skeleton overlay on annotated frames: thin white context skeleton, bold red/yellow only on the worst fault segment, dashed cyan ghost showing the reference pose at that joint.
- Local video analysis archive at `data/video_analyses/<timestamp>_<activity>/` with `raw/`, `overlay/` (all frames with skeleton), `annotated/` (key frames with form diff), `metrics.json`, and `landmarks.json`.
- Dense frame extraction (`_extract_video_frames_dense`) with `np.linspace` uniform sampling and >60s clip rejection with user guidance.
- `make download-models` target for fetching the MediaPipe pose landmarker model (~6MB).
- `pose_analysis.py` (830 lines): `PoseAnalyser`, `Landmarks`, `JOINT_ANGLES`, `angle_between_three_points`, `find_peaks`, `AggregatedMetrics.format_for_prompt()`.
- `pose_overlay.py` (330 lines): `draw_form_diff`, `_find_worst_fault`, `_draw_dashed_line`, `encode_annotated_frame`.
- `video_archive.py` (120 lines): `save_analysis`, `serialise_landmarks`.
- 24 new tests for math utilities, activity detection, overlay colouring, rotation, reference angles, and backward compatibility.
- Added `mediapipe>=0.10.0` dependency.

### Changed
- Video pipeline is now three-stage: dense local analysis (MediaPipe + NumPy) -> LLM interpretation (structured metrics + annotated key frames) -> supervisor synthesis.
- Annotated photos sent to Telegram before the coaching text for visual-first feedback.
- Overlay redesigned based on user feedback: removed cluttered angle text labels, simplified to single-fault focus with ghost reference.
- Updated agent README video pipeline Mermaid diagram to show full dense processing flow.

## [3.7.0] - 2026-03-30

### Added
- Telegram video message support: videos (including iOS screen recordings) are now processed instead of silently dropped. Registered `filters.VIDEO | filters.VIDEO_NOTE` handler in the bot.
- Standalone biomechanics agent (`whoopdata/agent/biomechanics.py`) for direct video frame analysis using gpt-5.4-mini with vision. Extracts 6 evenly-spaced frames via OpenCV and sends them as multi-image `detail: high` content blocks.
- Two-stage video pipeline: biomechanics agent analyses frames first, then the supervisor synthesises the response with coaching tone and health-data context.
- Biomechanics specialist registered in `AGENT_REGISTRY` for text-based follow-up questions routed through the supervisor. Both paths share memory.
- Evidence-based biomechanics system prompt (`data/prompts/agents/biomechanics_sub_agent.md`) with gold-standard reference ranges for tennis serve (Kovacs & Ellenbecker 8-stage model, meta-analysis joint angles), barbell back squat, and conventional deadlift.
- Frame preprocessing pipeline stub (`_preprocess_frames`) as the extension point for future pose estimation (MediaPipe/MMPose).
- Package READMEs with Mermaid architecture diagrams for `agent/`, `api/`, `services/`, `models/`, `database/`, `crud/`, and `pipelines/`.
- Added `opencv-python-headless>=4.8.0` dependency.

### Changed
- Biomechanics analysis output format redesigned: leads with one priority fault and one coaching cue instead of a wall of text. Offers to go deeper on additional findings.
- Models README updated with lightweight relationships-only ER diagram and a joins column in the model summary table.

## [3.6.0] - 2026-03-30

### Added
- Introduced unified runtime model configuration loading and validation for supervisor and specialist agents.

### Changed
- Updated supervisor orchestration wiring and prompt behavior to use the canonical model config path and improve response consistency/actionability.
- Expanded conversation/agent test coverage and supporting service updates for the unified contract flow.

## [3.5.0] - 2026-03-28

### Added
- Expanded proactive coaching flows (morning and in-window nudges) and strengthened Telegram support for pushing agent responses.
- Added richer analytics outputs and supporting pipeline changes so insights can be served more reliably.

### Changed
- Improved the public API surface contracts and legacy route handling to make integrations clearer and easier to test.
- Broadened verification and test coverage around the agent boundary, analytics, and scheduled workflows.

## [3.4.0] - 2026-03-23

### Added

- Added a recurring macOS `launchd` ETL job, dedicated Make targets, and append-only ETL audit logging so headless health-data refresh runs can be scheduled and audited cleanly.
- Added focused regression coverage for WHOOP offline-scope auth, token persistence, and scheduled ETL audit-log output.

### Changed

- Updated WHOOP authentication flows to request the `offline` scope and persist token expiry metadata, enabling one-time re-authorization followed by headless token refresh on subsequent ETL runs.
## [3.3.0] - 2026-03-23

### Added

- Added a proactive Telegram push flow, API endpoint, and helper scripts so the morning summary and manual smoke tests can send agent responses into the same shared conversation thread the Telegram bot uses.
- Added persistent `launchd` service definitions and Make helpers for the API server, Telegram bot, and scheduled morning summary job on macOS.

### Changed

- Fixed Telegram conversation continuity so repeated messages in the same private chat reuse the canonical session/thread binding and correctly load LangGraph checkpoint state from the configured persistent checkpointer.
- Updated the Telegram bot transport and related tests to cover stable chat-bound session/thread reuse and the shared persistence path used by runtime services.
## [3.2.0] - 2026-03-22

### Added

- Added durable agent memory tools for storing and searching user profile, goal, constraint, commitment, and observation context.
- Added Postgres-backed agent persistence plumbing so the shared conversation boundary can use durable checkpointing and long-term memory when configured.
- Added Telegram photo handling through the shared conversation service so image messages can be forwarded into the agent runtime.
- Added `make postgres-up`, `make postgres-down`, `make postgres-logs`, `make dev-full`, and `make dev-full-stop` to streamline local development and cleanup.

### Changed

- Updated the active supervisor prompt to use memory more deliberately for coaching, exercise planning, and image follow-up conversations.
- Passed runtime context and memory store access through specialist wrappers so exercise and behaviour-change planning can use saved memories.
- Extended the shared conversation boundary and public agent responses to carry richer surface context and media-aware interactions across API, chat, and Telegram flows.
## [3.1.1] - 2026-03-22

### Changed

- Updated the default text-to-speech voice configuration to a supported OpenAI voice and refreshed the coaching narration instructions used by the agent audio experience.
## [3.0.0] - 2026-03-21

### Added

- Established the canonical public surface model across `data`, `insights`, and `agent` namespaces under `/api/v1/*`, with shared OpenAPI grouping and rollout verification coverage.
- Routed the Gradio chat experience through the shared conversation boundary so the UI and API now follow the same session and thread ownership model.
- Upgraded maintained WHOOP integrations to the WHOOP v2 developer API and added regression coverage around the migration.
- Added recovery modeling notebook groundwork and related dataset stabilization updates.

### Changed

- Reframed the repository README around product outcomes, reviewer-oriented context, and canonical run modes while preserving the tested technical guidance.
- Reorganized supporting docs and assets under `docs/` and moved the verification script under `scripts/` to reduce root-level noise.
- Simplified launcher guidance to favor canonical commands (`make etl`, `make server`, `make chat`, `make verify`) and removed redundant wrapper scripts.

### Removed

- Removed redundant launcher scripts `run_app.py` and `start_health_chat.py`.

### Breaking Changes

- The canonical public API model is now organized around `/api/v1/data/*`, `/api/v1/insights/*`, and `/api/v1/agent/*`. Legacy aliases remain only as temporary compatibility adapters and should not be treated as the primary integration surface.
- WHOOP developer integrations now target the WHOOP v2 API. Existing developer setups may require token refresh and migration validation.
- Repository workflow guidance now assumes the canonical make targets and current script locations rather than older top-level helper scripts.

## [1.8.1] - 2026-02-28

### Changed

- Rewrote README to use plain language, removed emojis and overly promotional tone.
- Listed all make commands in the README to match the actual Makefile (including etl-full, analytics, langgraph-dev, test-cov, and clean-all).
- Added acknowledgement for the MLR module inspiration from [idossha/whoop-insights](https://github.com/idossha/whoop-insights/blob/main/src/whoop_sync/mlr.py).

### Removed

- Removed RELEASE_NOTES_v1.5.0.md, v1.6.1.md, v1.7.1.md, and v1.8.0.md from the repository root. Release notes are now published as GitHub Releases only.

## [1.8.0] - 2026-02-28

### Added - Multiple Linear Regression Analytics

- **Recovery MLR model** using statsmodels OLS, predicting recovery score from sleep, physiological, and activity features. Outputs R-squared, coefficients, t-values, p-values, and partial correlations.
- **HRV MLR model** using the same approach for HRV (RMSSD), including workout strain and zone data where available.
- **Correlation heatmap** across all numeric health features, rendered on the analytics dashboard with retina-quality output and horizontal scroll.
- **Three new API endpoints**: `/analytics/recovery/mlr`, `/analytics/hrv/mlr`, `/analytics/correlations/matrix`.
- **Three new analytics pipeline steps** (11 total, up from 8): Recovery MLR, HRV MLR, and Correlation Matrix.
- **Dashboard sections** for MLR coefficient tables, partial correlation bar charts, and the correlation heatmap.
- **Pydantic schemas** for MLR coefficients, model responses, partial correlations, and correlation matrix.
- **30 unit tests** in `tests/test_mlr.py` covering data prep, model fitting, result extraction, serialisation, edge cases, and correlation matrix.
- Added `statsmodels>=0.14.0` and `loguru>=0.7.3` dependencies.

### Fixed

- Data join direction in MLR data preparation now uses Recovery as the hub table, matching the rest of the codebase.
- Derived light sleep time from existing columns (Sleep model does not have total_light_sleep_time_milli).
- NaN and Inf values in statsmodels output no longer break JSON serialisation.
- Added fillna(0) after outer joins to prevent dropna from removing all rows.

### Known Issues

- Workout.cycle_id remains NULL for all workouts (WHOOP API does not return it). Fix planned for a future release.
- Recovery.cycle_id stores WHOOP API IDs that do not match Cycle.id (auto-increment). The MLR module works around this with outer joins.

## [1.6.1] - 2026-01-06

### 🔧 Changed - Dependency Validation & Release Prep

- Clarified CLI dependency checks by splitting core API vs analytics requirements, adding numpy, scikit-learn, xgboost, and optional SHAP guidance for the ML pipeline.
- Provided actionable installation tips for each dependency group so users can unblock the analytics pipeline quickly.

## [1.5.0] - 2026-01-01


### ✨ Added - Cycle Data Loading & Sport-Specific Analysis

This release unlocks **workout-based analytics** by adding cycle data loading from the WHOOP API. Cycles represent "physiological days" (sleep-to-sleep periods) and are the key link between workouts and recovery outcomes.

#### Core Features
- **Cycle Data Loading** - ETL pipeline now loads cycle data (daily strain, energy expenditure, heart rate)
  - Cycles automatically load via incremental and full ETL
  - Proper upsert logic prevents duplicates (user_id + start time)
  - Integrated with existing recovery and workout data

- **Sport Name Mapping** - 100+ WHOOP sports now display as readable names
  - Workouts show "Tennis" instead of "sport_id: 34"
  - Automatic `sport_name` and `sport_category` computed fields
  - Categories: Cardio, Strength, Team Sport, Racquet Sport, Mind-Body, Recovery

- **Workout-Recovery Linking** - New data prep function connects workouts to next-day recovery
  - `get_workouts_with_recovery()` joins workouts → cycles → recoveries
  - Enables analysis of sport/timing/intensity impact on recovery
  - Foundation for future sport-specific analytics endpoints

#### Technical Implementation
- Added `transform_cycle()` function for cycle data transformation
- Updated `load_cycle()` with upsert logic (user_id + start time as unique key)
- Added cycle support to incremental ETL loading (etl_incremental.py)
- Integrated cycle loading into `run_complete_etl()` using WHOOP 'strain' endpoint
- Added `_transform_cycle_fields()` to WHOOP API client for data normalization
- Created comprehensive sport ID mapping (whoopdata/utils/sport_mapping.py)

#### What's Now Possible

**For Users:**
```bash
# Cycles load automatically with ETL
make etl  # or make run

# View workouts with sport names
curl http://localhost:8000/workouts/types/tennis
# Response includes: "sport_name": "Tennis", "sport_category": "Racquet Sport"
```

**For Analysts:**
```python
from whoopdata.analytics.data_prep import get_workouts_with_recovery
from whoopdata.database.database import SessionLocal

db = SessionLocal()
df = get_workouts_with_recovery(db, days_back=365)

# Analyze recovery by sport
recovery_by_sport = df.groupby('sport_name')['recovery_score'].mean()
print(recovery_by_sport.sort_values(ascending=False))

# Analyze by timing
morning_recovery = df[df['workout_is_morning']]['recovery_score'].mean()
evening_recovery = df[df['workout_is_evening']]['recovery_score'].mean()
```

### 🔧 Fixed
- **OAuth Scopes** - Added `read:cycles` scope to WHOOP authentication
  - Required to access cycle/strain endpoint data
  - Users must delete `.whoop_tokens.json` and re-authenticate after upgrading

### 📚 Documentation
- Added WHOOP troubleshooting section for 401 authorization errors
- Updated EXPERIMENTAL_FEATURES.md - moved cycles to "What Works Well"
- Documented cycle data in pipeline overview
- Added token deletion instructions for scope updates
- Included Python examples for workout-recovery analysis

### ⚠️ Breaking Changes
- **Token Re-authentication Required** after upgrade:
  ```bash
  rm .whoop_tokens.json
  make run  # Will prompt for re-authentication with new scopes
  ```

### 🔄 Migration Notes

After upgrading to 1.5.0:
1. Delete old WHOOP token: `rm .whoop_tokens.json`
2. Run ETL to authenticate and load cycles: `make run` (choose option 1 or 4)
3. Browser will open for OAuth re-authorization
4. Cycles will load automatically on future ETL runs

### 📊 Data Model Changes
- Cycles table now populates (was previously empty)
- Workouts and recoveries now properly linked via `cycle_id`
- Enables workout → cycle → recovery joins for analysis

### 🎯 Future Enhancements (Coming Soon)
The data infrastructure is complete. Future releases will add:
- `GET /analytics/recovery/by-sport` - Recovery analysis by sport type
- `GET /analytics/recovery/by-timing` - Recovery by workout time of day  
- `GET /analytics/recovery/by-intensity` - Recovery by workout intensity

For now, use `get_workouts_with_recovery()` data prep function directly.

### 🙏 Credits
Co-Authored-By: Warp <agent@warp.dev>

## [1.4.5] - 2025-12-31

### 🐛 Fixed
- **WHOOP Upsert Keys**: Sleep and Workout records now upsert by `whoop_id` (unique API identifier) instead of database primary key `id`, preventing unique constraint violations on incremental ETL runs
- **ETL Transaction Handling**: Added session rollback on per-record failures in WHOOP and Withings ETL loops to prevent session poisoning and allow subsequent records to process successfully

### 🔧 Technical Details
- Modified `DBLoader.upsert_sleep()` and `DBLoader.upsert_workout()` to use `whoop_id` as the unique constraint
- Added `session.rollback()` in exception handlers for WHOOP (`extract_data.py`) and Withings (`withings_data.py`) ETL loops
- Ensures incremental data loads can run repeatedly without errors

## [1.4.4] - 2025-12-31

### 🐛 Fixed
- Withings OAuth: treat missing expiry as invalid, add force reauth path, safer browser/callback handling
- Withings data freshness: use `lastupdate` delta sync and log newest API vs DB timestamps

### ✨ Added
- CLI: `whoop-withings-auth` to force re-authentication
- API: `/auth/withings/status` endpoint for token/data recency diagnostics

### 📚 Docs
- README and docs/guides/TESTING_GUIDE.md: Withings troubleshooting and health checks

## [1.4.3] - 2025-12-29

### 🧹 Chore - Repository Cleanup

#### Removed Files
- **Temporary Fix Scripts** (4 files)
  - `cleanup_duplicates.py` - One-time script for v1.1.0 duplicate cleanup (issue resolved with upsert logic)
  - `fix_sleep_analytics.py` - One-time script for v1.3.0 analytics circular logic fix (issue resolved)
  - `fix_sleep_id_mapping.py` - Migration script for v1.2.1 sleep_id foreign key mapping (migration complete)
  - `implement_analytics_enhancements.sh` - Empty stub script from analytics development (never used)

- **Obsolete Planning Documents** (3 files)
  - `ANALYTICS_SUMMARY.md` - PR summary for v1.3.0 (feature complete, documented in CHANGELOG)
  - `Implement Upsert ETL and Fix Withings Data Loading.md` - Planning doc for v1.1.1 (feature complete)
  - `CREATE_PR.md` - Single-use PR creation guide (specific to old restructure/whoop branch)

#### Rationale
- Temporary scripts completed their purpose and fixes are now part of the codebase
- Planning documents were working docs for completed features now documented in CHANGELOG
- Files cluttered the root directory and made navigation harder
- All content preserved in git history for reference

#### Files Kept
- Migration guides (`MIGRATION_UV.md`, `MIGRATION_v1.2.1.md`) for historical reference
- Active workflow documentation (`docs/guides/PR_WORKFLOW.md`, `docs/guides/TESTING_GUIDE.md`)
- Core documentation (`README.md`, `CHANGELOG.md`)

## [1.4.0] - 2025-12-29

### 🔄 Changed - UV Package Management Migration

#### Package Management Modernization
- **Migrated from pip/venv to UV** - Fast, modern Python package management
- **Added pyproject.toml** - PEP 621 compliant project configuration
- **Consolidated dependencies** - Single source of truth for all dependencies
- **Added uv.lock** - Reproducible dependency resolution
- **Updated Python requirement** to >=3.10 (required by Gradio 5.9.1)

#### Developer Experience Improvements
- **Added Makefile** with convenient commands:
  - `make install` / `make dev` - Install dependencies
  - `make run` / `make server` - Start application
  - `make test` / `make format` / `make lint` - Development tools
  - `make clean` - Cleanup commands
- **Updated shell scripts** to use UV (`activate_env.sh`, `scripts/daily_etl.sh`)
- **Console scripts** still work the same: `whoop-start`, `whoop-etl`

#### Technical Changes
- Build system: hatchling (replaces setuptools)
- Virtual environment: `.venv/` (UV managed)
- Added scikit-learn and scipy to dependencies (for analytics)
- Updated .gitignore for UV artifacts

### 📚 Documentation
- See `MIGRATION_UV.md` for migration guide
- Updated installation instructions in README.md
- Updated all command examples to use UV or Make

### ⚠️ Breaking Changes
- **Python >=3.10 required** (was >=3.8)
- Old `venv/` no longer used (can be removed with `make clean-all`)

### 🔄 Backward Compatibility
- `setup.py` kept for pip compatibility
- `requirements.txt` kept as reference
- All entry points work identically
- No changes to API or functionality

### 📦 Migration Instructions
```bash
# Remove old venv (optional)
rm -rf venv

# Install UV (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Or use make
make dev

# Run application
make run
# or
uv run whoop-start
```

## [1.3.0] - 2025-12-29

### ✨ Added - Advanced Analytics Engine (PR #13)

#### Core Analytics Features
- **Recovery Factor Analysis** - ML-based feature importance analysis identifies which factors (HRV, sleep, strain) most impact your recovery
- **Sleep Quality Impact** - Analyzes how sleep factors affect next-day recovery scores
- **Correlation Analysis** - Discovers statistically significant relationships between health metrics
- **Time Series Analysis** - 30-day trend detection with anomaly identification for recovery, HRV, RHR, and sleep
- **Weekly Insights Generator** - Automatically generates personalized, actionable health insights
- **Interactive Analytics Dashboard** - Beautiful Chart.js visualizations at `/analytics`

#### Technical Implementation
- Random Forest models for recovery and sleep prediction with cross-validation
- Pre-computed analytics stored in database for fast API responses
- Analytics pipeline (`whoopdata/pipelines/analytics_pipeline.py`) for batch processing
- Model persistence and management system
- Comprehensive analytics API endpoints (`/analytics/*`)

#### New API Endpoints
- `GET /analytics/summary` - Aggregated analytics overview
- `GET /analytics/recovery/factors` - Recovery factor importance rankings
- `GET /analytics/sleep/factors` - Sleep quality factor analysis
- `GET /analytics/correlations` - Health metric correlation matrix
- `GET /analytics/insights/weekly` - Personalized weekly insights
- `GET /analytics/patterns/{metric}` - Trend analysis for specific metrics
- `GET /analytics/recovery/deep-dive` - Comprehensive recovery analysis
- `POST /analytics/predict/recovery` - Predict recovery from input metrics
- `POST /analytics/predict/sleep` - Predict sleep quality

#### Agent Tools
- Conversational analytics through agent interface
- Natural language queries for health insights
- Integration with existing chat system

### 🐛 Fixed
- Sleep quality analyzer now correctly predicts recovery from sleep factors (not circular logic)
- Analytics dashboard UI now matches API response structure
- Added proper error messages when insufficient data for workout-based analytics
- Fixed missing `bedtime_consistency_score` feature in recovery dataset

### 📚 Documentation
- Comprehensive analytics documentation (`docs/features/ANALYTICS.md`)
- Implementation summary (`ANALYTICS_SUMMARY.md`)
- Experimental features guide (`docs/EXPERIMENTAL_FEATURES.md`)
- Result interpretation guidelines
- Privacy and data handling documentation

### ⚠️ Known Limitations (Experimental Features)
- **Workout-based analytics** require cycle data from WHOOP API
  - Recovery by sport/activity
  - Recovery by workout timing
  - Recovery by intensity
- **Reason**: Database has 2,126 workouts but 0 cycles (workouts linked via cycles)
- **Fix**: Sync cycle data through ETL process

### 🔒 Privacy
- All analytics computed locally on your machine
- No data sent to external servers
- Models trained on your data only
- No telemetry or tracking

### 📦 Dependencies
- scikit-learn for ML models
- Chart.js for visualizations
- Rich for CLI progress reporting

### 🚀 Performance
- Analytics pre-computation reduces dashboard load time
- Model caching for repeated predictions
- Efficient rolling feature calculations

### 🎯 Model Accuracy
- Recovery predictor: R² = 0.88
- Sleep efficiency predictor: R² = 0.96
- Factor analyzer: R² = 0.88

### 💡 Usage
Run analytics pipeline from CLI:
```bash
python -m whoopdata.cli
# Select option 6: Run analytics pipeline
```

View analytics dashboard:
```
http://localhost:8000/analytics
```

## [1.2.1] - 2025-12-XX

### 🐛 Fixed
- ETL datatype mismatch errors (#12)

## [1.2.0] - 2025-12-XX

### ✨ Added
- Incremental ETL loading for faster data updates (#11)

## [1.1.1] - 2025-12-XX

### 🐛 Fixed
- Upsert logic for WHOOP data to prevent duplicates (#10)

## [1.1.0] - 2025-12-XX

### ✨ Added
- Interactive health dashboard with real-time metrics visualization (#9)

## [1.0.0] - 2025-11-XX

### 🎉 Initial Release
- WHOOP data extraction and loading
- PostgreSQL database with SQLAlchemy models
- FastAPI REST API
- Basic health metrics visualization

---

[1.3.0]: https://github.com/ald0405/whoop-data/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/ald0405/whoop-data/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/ald0405/whoop-data/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/ald0405/whoop-data/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ald0405/whoop-data/compare/v1.0.0...v1.1.0
