"""Boundary tests for the biomarker analyser (Phase 0 prototype).

The intended-purpose "does NOT" list (docs/features/BIOMARKER_INTENDED_PURPOSE.md)
is now enforced by the biomarkers sub-agent prompt rather than a deterministic
graph node, so it is no longer unit-testable here. What remains testable at the
data layer is the hard invariant that the agent-facing CRUD never surfaces the
lab's own verdict (``lab_status``) — surfacing it would be interpretation.
"""

from __future__ import annotations


def test_crud_results_never_expose_lab_status():
    """The agent-facing CRUD must never select the lab's own verdict."""
    from whoopdata.crud import biomarker as crud
    from whoopdata.database.database import SessionLocal
    from whoopdata.models.models import Base
    from whoopdata.database.database import engine

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rows = crud.get_results(db)
    finally:
        db.close()

    if rows:  # only assert when the DB has been seeded
        for row in rows:
            assert "lab_status" not in row
            assert "status" not in row
