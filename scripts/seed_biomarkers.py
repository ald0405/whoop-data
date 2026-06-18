#!/usr/bin/env python3
"""Seed the biomarker analyser tables from a parsed Emerald report.

Phase 0 prototype. Loads the parsed JSON intermediate at
``data/biomarkers/emerald_report.json`` (PDF -> JSON done by hand and committed
so it can be eyeballed) plus the generic education glossary, then truncate-and-
loads the biomarker tables via ``crud.replace_report`` — enforcing the
single-result-set / single-timepoint constraint.

Usage:
    python scripts/seed_biomarkers.py [--dry-run]
                                      [--report PATH] [--education PATH]

See docs/features/BIOMARKER_INTENDED_PURPOSE.md and BIOMARKER_SCHEMA.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath("."))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data" / "biomarkers" / "emerald_report.json"
DEFAULT_EDUCATION = ROOT / "data" / "biomarkers" / "biomarker_education.json"


def _parse_taken_on(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def _dedupe(rows: list[dict]) -> list[dict]:
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


def load_report(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text())
    return data["report"], _dedupe(data["results"])


def load_education(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("entries", [])


def _summarise(report: dict, results: list[dict], education: list[dict]) -> None:
    categories: dict[str, int] = {}
    one_sided = 0
    qualitative = 0
    with_operator = 0
    for row in results:
        categories[row.get("category", "?")] = categories.get(row.get("category", "?"), 0) + 1
        low, high = row.get("low"), row.get("high")
        if (low is None) ^ (high is None):
            one_sided += 1
        if row.get("value") is None and row.get("concept"):
            qualitative += 1
        if row.get("operator"):
            with_operator += 1

    print(f"Report: {report.get('order_number')} | {report.get('taken_on')} | "
          f"{report.get('lab_provider')}")
    print(f"Results: {len(results)} unique biomarkers across {len(categories)} body systems")
    for cat, n in sorted(categories.items()):
        print(f"  - {cat}: {n}")
    print(f"One-sided ranges: {one_sided} | qualitative results: {qualitative} | "
          f"operator (<,>) results: {with_operator}")
    print(f"Education entries: {len(education)}")


def seed(report: dict, results: list[dict], education: list[dict]) -> None:
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
    education_models = [
        BiomarkerEducation(
            source_biomarker_name=entry["name"],
            what_it_is=entry.get("what_it_is"),
            physiological_function=entry.get("physiological_function"),
        )
        for entry in education
    ]

    db = SessionLocal()
    try:
        crud.replace_report(db, report=report_model, results=result_models)
        crud.upsert_education(db, education_models)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed biomarker tables from a parsed report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--education", type=Path, default=DEFAULT_EDUCATION)
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and summarise only; do not write to the database.")
    args = parser.parse_args()

    report, results = load_report(args.report)
    education = load_education(args.education)

    _summarise(report, results, education)

    if args.dry_run:
        print("\n[dry-run] No database writes performed.")
        return 0

    seed(report, results, education)
    print("\nSeeded biomarker tables (truncate-and-load, biomarker tables only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
