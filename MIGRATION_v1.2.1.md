# Migration Guide: v1.2.1 - Datatype Mismatch Fixes

## Overview
Version 1.2.1 fixes critical datatype mismatch errors that prevented WHOOP and Withings data from loading correctly into the database.

## What Changed

### Database Schema Changes
1. **Sleep Table**: Added `whoop_id` column (String) to store WHOOP API's string IDs
2. **Workout Table**: Added `whoop_id` column (String) to store WHOOP API's string IDs
3. The `id` column now uses auto-increment integers (database primary key)
4. The `whoop_id` column stores the API's unique identifier (string/UUID)

### Data Type Fixes
- **WHOOP Sleep/Workout**: Fixed ID field type from Integer to String
- **Withings date field**: Ensured it's always Integer (UNIX timestamp)
- **Withings datetime field**: Ensured it's always DateTime object
- Added explicit type conversions for grpid, deviceid, and category fields

### Upsert Logic
- Sleep and Workout now use upsert logic based on `whoop_id` to prevent duplicates
- Withings Weight and Heart Rate already had upsert logic (no changes)

## Migration Options

### Option 1: Fresh Start (Recommended for Development)
If you're okay with reloading all data:

```bash
# Run the migration script
python scripts/migrate_add_whoop_id.py

# Choose option 2: Drop all tables and recreate
# Then reload your data
python run_app.py
# Choose option 1 or 2 to run full pipeline
```

### Option 2: Automatic Migration (Only if tables are empty)
If your Sleep and Workout tables are empty:

```bash
python scripts/migrate_add_whoop_id.py
# Choose option 1: Migrate existing database
```

### Option 3: Manual Database Backup/Restore
If you have important data and want to preserve it:

1. **Backup your database:**
   ```bash
   cp whoop_data.db whoop_data_backup.db
   ```

2. **Export your data** (manual SQL export if needed)

3. **Drop and recreate tables:**
   ```bash
   python scripts/migrate_add_whoop_id.py
   # Choose option 2
   ```

4. **Reload data from API:**
   ```bash
   python run_app.py
   # Choose option 2: Full pipeline (full load)
   ```

## Testing the Fix

After migration, test the ETL pipeline:

```bash
# Test full load
python run_app.py
# Choose option 2: Full pipeline (full load)

# Verify no errors appear
# You should see successful inserts for:
# - WHOOP Recovery
# - WHOOP Workout
# - WHOOP Sleep
# - Withings Weight
# - Withings Heart Rate
```

## What to Expect

### Before (v1.2.0)
- ❌ Thousands of `sqlite3.IntegrityError: datatype mismatch` errors
- ❌ Sleep data failed to load
- ❌ Withings weight/heart rate data failed to load
- ⚠️ Only Recovery and Workout data loaded successfully

### After (v1.2.1)
- ✅ All WHOOP data loads successfully
- ✅ All Withings data loads successfully
- ✅ No datatype mismatch errors
- ✅ Incremental loading continues to work efficiently
- ✅ Upsert logic prevents duplicate records

## Breaking Changes

⚠️ **Database Schema Change**: The `id` field in Sleep and Workout tables is no longer the WHOOP API's ID. It's now an auto-incrementing integer. The API's ID is stored in the new `whoop_id` field.

If you have any custom queries or code that references Sleep or Workout IDs directly, you may need to update them to use `whoop_id` instead.

## Rollback

If you need to rollback to v1.2.0:

```bash
git checkout v1.2.0
# Restore your database backup
cp whoop_data_backup.db whoop_data.db
```

Note: This will reintroduce the datatype mismatch errors.

## Support

If you encounter issues during migration:
1. Check that you're using Python 3.8+
2. Ensure all dependencies are installed: `pip install -r requirements.txt`
3. Verify database file permissions
4. Check error logs for specific issues

## Related Issues

This release fixes the following issues from v1.2.0:
- `sqlite3.IntegrityError: datatype mismatch` on Sleep inserts
- `sqlite3.IntegrityError: datatype mismatch` on Withings Weight inserts
- `sqlite3.IntegrityError: datatype mismatch` on Withings Heart Rate inserts
