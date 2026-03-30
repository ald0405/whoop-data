# CRUD

Data access layer providing read operations against the SQLAlchemy ORM models.
Each module corresponds to a single domain entity and exposes query functions
consumed by services, API routes, and analytics.

## Module Map

| Module | Entity | Key Functions |
|---|---|---|
| `recovery.py` | `Recovery` | `get_recoveries` (paginated, descending), `get_top_recoveries` (by score), `get_recent_recovories` (last N days), `get_avg_recovery_by_week` (weekly averages over N weeks) |
| `sleep.py` | `Sleep` | `get_sleep` (paginated, descending by date) |
| `workout.py` | `Workout` | `get_recoveries` (all workouts -- historical naming), `get_runs` (sport_id=0), `get_tennis` (sport_id=34); all support optional date range filtering |

## Conventions

- All query functions accept a SQLAlchemy `Session` as the first argument
  and return lists of ORM model instances.
- Results are ordered by `created_at` descending (most recent first) unless
  stated otherwise.
- Pagination uses `skip`/`limit` parameters with sensible defaults.
- Date filtering is optional via `start_date`/`end_date` keyword arguments
  where supported.
- Functions do not commit or modify data -- this layer is read-only.

## Usage

```python
from whoopdata.database.database import SessionLocal
from whoopdata.crud.recovery import get_recoveries

db = SessionLocal()
recent = get_recoveries(db, limit=7)
db.close()
```

## Notes

- `workout.py` contains a function named `get_recoveries` that actually
  returns workouts. This is a legacy naming artefact -- the function
  predates the recovery module and the name was never updated.
- Sport type filtering uses integer IDs from the WHOOP API. The mapping
  from ID to human-readable name lives in `utils/sport_mapping.py`.
