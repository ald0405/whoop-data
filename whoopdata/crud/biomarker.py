"""CRUD for the biomarker analyser (Phase 0 prototype).

Two hard rules enforced here, both load-bearing for the intended purpose
(docs/features/BIOMARKER_INTENDED_PURPOSE.md):

1. ``lab_status`` is NEVER selected into agent-facing results — the lab's own
   high/low verdict must not leak through the data layer.
2. ``replace_report`` is a TRUNCATE-AND-LOAD scoped strictly to the biomarker
   tables, so the system only ever holds one result set (single timepoint).
   It must never touch WHOOP/Withings tables.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from whoopdata.models.models import (
    BiomarkerEducation,
    BiomarkerReport,
    BiomarkerResult,
)

# Columns the agent is allowed to see. lab_status / *_concept_id are deliberately
# excluded — lab_status is a verdict; concept ids are internal mapping hooks.
_PUBLIC_RESULT_COLUMNS = (
    BiomarkerResult.source_biomarker_name,
    BiomarkerResult.category,
    BiomarkerResult.result_raw,
    BiomarkerResult.value_as_number,
    BiomarkerResult.value_as_concept,
    BiomarkerResult.operator,
    BiomarkerResult.unit,
    BiomarkerResult.range_low,
    BiomarkerResult.range_high,
)


def get_active_report(db: Session) -> Optional[BiomarkerReport]:
    """Return the single active report (there is only ever one)."""
    return db.query(BiomarkerReport).order_by(BiomarkerReport.report_id.desc()).first()


def get_results(db: Session, category: Optional[str] = None) -> list[dict]:
    """Return agent-visible results (never includes lab_status).

    Returns plain dicts built from the public column subset so a verdict can
    never be selected by accident.
    """
    query = db.query(*_PUBLIC_RESULT_COLUMNS)
    if category:
        query = query.filter(BiomarkerResult.category == category)
    query = query.order_by(BiomarkerResult.category, BiomarkerResult.source_biomarker_name)
    return [row._asdict() for row in query.all()]


def get_education(db: Session, biomarker: str) -> Optional[BiomarkerEducation]:
    """Return the generic glossary entry for a biomarker, if present."""
    return (
        db.query(BiomarkerEducation)
        .filter(BiomarkerEducation.source_biomarker_name == biomarker)
        .first()
    )


def replace_report(
    db: Session,
    *,
    report: BiomarkerReport,
    results: list[BiomarkerResult],
) -> None:
    """Truncate-and-load the biomarker result tables with a single new report.

    Scoped strictly to biomarker_report + biomarker_results. Never deletes any
    other table. Enforces the single-result-set / single-timepoint constraint.
    """
    db.query(BiomarkerResult).delete()
    db.query(BiomarkerReport).delete()
    db.flush()

    db.add(report)
    db.flush()  # assign report_id
    for result in results:
        result.report_id = report.report_id
        db.add(result)
    db.commit()


def upsert_education(db: Session, entries: list[BiomarkerEducation]) -> None:
    """Replace the generic education glossary."""
    db.query(BiomarkerEducation).delete()
    for entry in entries:
        db.add(entry)
    db.commit()
