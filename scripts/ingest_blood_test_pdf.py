#!/usr/bin/env python3
"""Ingest a blood-test PDF: extract -> preview -> (optionally) write to the DB.

PDF -> structured results via LLM extraction (text for digital PDFs, vision for
scanned ones), then the shared truncate-and-load write path. Defaults to a
DRY RUN (no DB writes) so the extracted values can be eyeballed first.

Usage:
    python scripts/ingest_blood_test_pdf.py REPORT.pdf            # dry-run preview
    python scripts/ingest_blood_test_pdf.py REPORT.pdf --out r.json
    python scripts/ingest_blood_test_pdf.py REPORT.pdf --commit   # write to DB

See docs/features/BIOMARKER_INTENDED_PURPOSE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath("."))


def main() -> int:
    from whoopdata.biomarkers.ingest_service import summarise, write_report
    from whoopdata.biomarkers.pdf_ingest import extract_report_from_pdf

    parser = argparse.ArgumentParser(
        description="Ingest a blood-test PDF into the biomarker tables."
    )
    parser.add_argument("pdf", type=Path, help="Path to the blood-test PDF.")
    parser.add_argument("--out", type=Path, help="Also write the extracted JSON to this path.")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write to the DB (truncate-and-load). Without this, dry-run preview only.",
    )
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"No such file: {args.pdf}", file=sys.stderr)
        return 1

    print(f"Extracting {args.pdf.name} …")
    payload = extract_report_from_pdf(args.pdf)
    report, results = payload["report"], payload["results"]

    print()
    print(summarise(report, results))

    if args.out:
        args.out.write_text(json.dumps(payload, indent=2))
        print(f"\nWrote extracted JSON to {args.out}")

    if not args.commit:
        print("\n[dry-run] No database writes performed. Re-run with --commit to save.")
        return 0

    n = write_report(payload)
    print(f"\nWrote {n} biomarker results (truncate-and-load, biomarker tables only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
