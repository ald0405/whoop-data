# Release v1.5.0 - Cycle Data Loading & Sport-Specific Analysis

**Release Date**: January 1, 2026  
**Branch**: `feature/add-cycle-data-loading` → `main`  
**Commits**: 10

## 🎯 Overview

Version 1.5.0 unlocks **workout-based analytics** by adding cycle data loading from the WHOOP API. This was the missing piece preventing sport-specific recovery analysis.

### What Are Cycles?

Cycles are WHOOP's "physiological days" - they run from **sleep-to-sleep** (when you fall asleep one night until you fall asleep the next night). Cycles contain:
- Total daily strain (sum of all workouts + daily activity)
- Energy expenditure (kilojoules)
- Daily heart rate statistics

Cycles are the **key link** between workouts and recovery outcomes.

## ✨ Key Features

### 1. Cycle Data Loading
- ✅ ETL pipeline automatically loads cycles from WHOOP API
- ✅ Incremental loading support (fetch only recent cycles)
- ✅ Proper upsert logic prevents duplicates
- ✅ Links workouts and recoveries through `cycle_id` foreign keys

### 2. Sport Name Mapping
- ✅ 100+ WHOOP sports mapped to readable names
- ✅ "Tennis" instead of "sport_id: 34"
- ✅ Sport categories: Cardio, Strength, Team Sport, Racquet Sport, etc.
- ✅ Automatic computed fields in API responses

### 3. Workout-Recovery Analysis
- ✅ New `get_workouts_with_recovery()` data prep function
- ✅ Joins workouts → cycles → next-day recoveries
- ✅ Enables analysis of:
  - Which sports yield better recovery?
  - Morning vs evening workout impact
  - High-intensity vs low-intensity recovery

## 🚀 What You Can Do Now

### For End Users

```bash
# Cycles load automatically with ETL
make run  # Choose option 1 or 4

# View tennis workouts with sport names
curl http://localhost:8000/workouts/types/tennis

# Response now includes:
# "sport_name": "Tennis"
# "sport_category": "Racquet Sport"
```

### For Data Analysts

```python
from whoopdata.analytics.data_prep import get_workouts_with_recovery
from whoopdata.database.database import SessionLocal

db = SessionLocal()
df = get_workouts_with_recovery(db, days_back=365)

# Which sports correlate with best recovery?
recovery_by_sport = df.groupby('sport_name')['recovery_score'].mean()
print(recovery_by_sport.sort_values(ascending=False))

# Morning vs evening workouts
timing_analysis = df.groupby(['workout_is_morning', 'workout_is_evening'])['recovery_score'].mean()
print(timing_analysis)

# High-intensity impact
high_intensity = df[df['high_intensity_pct'] > 50]['recovery_score'].mean()
low_intensity = df[df['high_intensity_pct'] <= 50]['recovery_score'].mean()
print(f"High intensity: {high_intensity:.1f}%, Low intensity: {low_intensity:.1f}%")
```

## ⚠️ Breaking Changes & Migration

### Required: Token Re-authentication

The new `read:cycles` OAuth scope requires re-authentication:

```bash
# 1. Delete old token
rm .whoop_tokens.json

# 2. Run ETL (will prompt for re-auth)
make run

# 3. Browser opens - approve WHOOP OAuth
# 4. Cycles load automatically!
```

**Why?** OAuth tokens are scoped. The old token doesn't include `read:cycles`, so the cycle endpoint returns 401 errors until you re-authenticate.

## 📊 Technical Details

### Database Changes
- **Cycles table** now populates (was previously empty)
- **Foreign keys** properly link: `Workout.cycle_id` → `Cycle.id` ← `Recovery.cycle_id`
- **Data model** now complete for workout-based analytics

### ETL Pipeline Updates
- Added cycle loading to `run_complete_etl()` (etl.py:424-433)
- Cycle endpoint: WHOOP's `/v2/cycle` (mapped as 'strain' endpoint)
- Incremental loading support via `etl_incremental.py`
- Upsert logic uses `user_id` + `start` time as unique key

### Files Modified/Created

**Core Implementation:**
- `whoopdata/model_transformation.py` - Added `transform_cycle()`
- `whoopdata/utils/db_loader.py` - Updated `load_cycle()` with upsert
- `whoopdata/etl.py` - Integrated cycle loading
- `whoopdata/etl_incremental.py` - Cycle window calculation
- `whoopdata/analysis/whoop_client.py` - Added `_transform_cycle_fields()`, OAuth scopes

**New Features:**
- `whoopdata/utils/sport_mapping.py` - Sport ID → name mapping (NEW FILE)
- `whoopdata/schemas/workout.py` - Added `sport_name`, `sport_category` computed fields
- `whoopdata/analytics/data_prep.py` - Added `get_workouts_with_recovery()` function

**Documentation:**
- `README.md` - Added WHOOP troubleshooting, cycle data overview
- `docs/EXPERIMENTAL_FEATURES.md` - Moved cycles to "What Works Well"
- `CHANGELOG.md` - Comprehensive v1.5.0 release notes
- `whoopdata/__version__.py` - Bumped to 1.5.0

### Commits (10)

```
e197869 chore: Bump version to 1.5.0 and update CHANGELOG
9717718 docs: Update experimental features - cycle data now complete
c19cf5f feat: Add get_workouts_with_recovery for sport-specific analysis
e0d5c44 docs: Add WHOOP troubleshooting and cycle data documentation
8f47d1a feat: Add sport name and category to workout schema
4831f13 fix: Add read:cycles scope to WHOOP OAuth
5af40f1 feat: Add sport ID to name mapping utility
f4da2fe feat: Add cycle data loading to ETL pipeline
```

## 🎯 Future Roadmap

### Coming in Future Releases

The data infrastructure is complete. Future versions will add API endpoints:

- `GET /analytics/recovery/by-sport` - Recovery analysis by sport type
- `GET /analytics/recovery/by-timing` - Recovery by workout time of day
- `GET /analytics/recovery/by-intensity` - Recovery by workout intensity

For now, analysts can use `get_workouts_with_recovery()` directly in Python.

## 🙏 Credits

This release was developed with assistance from Warp AI Agent.

**Co-Authored-By:** Warp <agent@warp.dev>

## 📝 Testing Checklist

Before merging:
- [x] ETL pipeline loads cycles successfully
- [x] Incremental loading works (fetch windows calculated)
- [x] OAuth re-authentication flow works
- [x] Sport names display in workout API responses
- [x] `get_workouts_with_recovery()` returns valid data
- [x] Documentation updated (README, EXPERIMENTAL_FEATURES)
- [x] CHANGELOG comprehensive and accurate
- [x] Version bumped to 1.5.0

## 🚢 Deployment Instructions

```bash
# 1. Review and approve PR
gh pr review --approve

# 2. Merge to main
git checkout main
git merge --no-ff feature/add-cycle-data-loading

# 3. Tag release
git tag -a v1.5.0 -m "Release v1.5.0 - Cycle Data Loading & Sport-Specific Analysis"

# 4. Push
git push origin main --tags

# 5. Users upgrade with:
git pull origin main
rm .whoop_tokens.json  # Force re-auth
make run
```

---

**Full CHANGELOG**: https://github.com/yourusername/whoop-data/blob/main/CHANGELOG.md#150---2026-01-01
