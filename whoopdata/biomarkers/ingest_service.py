"""Write a parsed biomarker report into the DB (single, shared write path).

Both the seeding script, the PDF-ingest CLI, and the Telegram upload flow go
through here, so the truncate-and-load / single-timepoint invariant lives in one
place. See ``whoopdata/crud/biomarker.py`` and
``docs/features/BIOMARKER_INTENDED_PURPOSE.md``.
"""

from __future__ import annotations

from datetime import datetime


def _parse_taken_on(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def dedupe_results(rows: list[dict]) -> list[dict]:
    """Keep the first occurrence of each biomarker (single timepoint, no dups)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        name = row["name"]
        if name in seen:
            continue
        seen.add(name)
        unique.append(row)
    return unique


def summarise(report: dict, results: list[dict], education: list[dict] | None = None) -> str:
    """Build a human-readable summary of a parsed report (for preview/confirm)."""
    education = education or []
    categories: dict[str, int] = {}
    one_sided = qualitative = with_operator = 0
    for row in results:
        cat = row.get("category") or "?"
        categories[cat] = categories.get(cat, 0) + 1
        low, high = row.get("low"), row.get("high")
        if (low is None) ^ (high is None):
            one_sided += 1
        if row.get("value") is None and row.get("concept"):
            qualitative += 1
        if row.get("operator"):
            with_operator += 1

    lines = [
        f"Report: {report.get('order_number')} | {report.get('taken_on')} | "
        f"{report.get('lab_provider')}",
        f"Results: {len(results)} unique biomarkers across {len(categories)} body systems",
    ]
    for cat, n in sorted(categories.items()):
        lines.append(f"  - {cat}: {n}")
    lines.append(
        f"One-sided ranges: {one_sided} | qualitative: {qualitative} | "
        f"operator (<,>): {with_operator}"
    )
    if education:
        lines.append(f"Education entries: {len(education)}")
    return "\n".join(lines)


def write_report(payload: dict, education: list[dict] | None = None) -> int:
    """Truncate-and-load the biomarker tables from a parsed payload.

    Args:
        payload: ``{"report": {...}, "results": [...]}`` (the seed JSON contract).
        education: optional generic education glossary entries to upsert.

    Returns:
        The number of result rows written.
    """
    from whoopdata.crud import biomarker as crud
    from whoopdata.database.database import SessionLocal, engine
    from whoopdata.models.models import (
        Base,
        BiomarkerEducation,
        BiomarkerReport,
        BiomarkerResult,
    )

    # Additive: only creates the biomarker tables if missing; never alters others.
    Base.metadata.create_all(bind=engine)

    report = payload["report"]
    results = dedupe_results(payload["results"])

    report_model = BiomarkerReport(
        order_number=report.get("order_number"),
        taken_on=_parse_taken_on(report.get("taken_on")),
        lab_provider=report.get("lab_provider"),
        report_status=report.get("report_status"),
        biological_sex=report.get("biological_sex"),
        source_file=report.get("source_file"),
    )
    result_models = [
        BiomarkerResult(
            source_biomarker_name=row["name"],
            category=row.get("category"),
            result_raw=row.get("raw"),
            value_as_number=row.get("value"),
            value_as_concept=row.get("concept"),
            operator=row.get("operator"),
            unit=row.get("unit"),
            range_low=row.get("low"),
            range_high=row.get("high"),
            lab_status=row.get("status"),  # stored, never surfaced
        )
        for row in results
    ]

    db = SessionLocal()
    try:
        crud.replace_report(db, report=report_model, results=result_models)
        if education:
            education_models = [
                BiomarkerEducation(
                    source_biomarker_name=entry["name"],
                    what_it_is=entry.get("what_it_is"),
                    physiological_function=entry.get("physiological_function"),
                )
                for entry in education
            ]
            crud.upsert_education(db, education_models)
    finally:
        db.close()

    return len(result_models)
