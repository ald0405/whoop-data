# Changelog

All notable changes to the WHOOP Data Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- README and TESTING_GUIDE: Withings troubleshooting and health checks

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
- Active workflow documentation (`PR_WORKFLOW.md`, `TESTING_GUIDE.md`)
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
