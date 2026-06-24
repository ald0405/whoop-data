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
from pathlib import Path

sys.path.append(os.path.abspath("."))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data" / "biomarkers" / "emerald_report.json"
DEFAULT_EDUCATION = ROOT / "data" / "biomarkers" / "biomarker_education.json"


def load_report(path: Path) -> tuple[dict, list[dict]]:
    from whoopdata.biomarkers.ingest_service import dedupe_results

    data = json.loads(path.read_text())
    return data["report"], dedupe_results(data["results"])


def load_education(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("entries", [])


def main() -> int:
    from whoopdata.biomarkers.ingest_service import summarise, write_report

    parser = argparse.ArgumentParser(description="Seed biomarker tables from a parsed report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--education", type=Path, default=DEFAULT_EDUCATION)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and summarise only; do not write to the database.",
    )
    args = parser.parse_args()

    report, results = load_report(args.report)
    education = load_education(args.education)

    print(summarise(report, results, education))

    if args.dry_run:
        print("\n[dry-run] No database writes performed.")
        return 0

    write_report({"report": report, "results": results}, education=education)
    print("\nSeeded biomarker tables (truncate-and-load, biomarker tables only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
