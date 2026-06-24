"""Tests for blood-test PDF extraction + the shared write service.

The LLM call is always mocked (no network, deterministic), and the DB write is
exercised against an isolated temp SQLite so the real whoop.db is never touched.
"""

from __future__ import annotations

import pytest

from whoopdata.biomarkers.pdf_ingest import (
    ExtractedDocument,
    ExtractedReport,
    ExtractedResult,
    _normalise,
)


def _sample_doc() -> ExtractedDocument:
    return ExtractedDocument(
        report=ExtractedReport(
            order_number="X1",
            taken_on="2026-06-01",
            lab_provider="Lab",
            report_status="Final",
            biological_sex="Male",
        ),
        results=[
            ExtractedResult(
                name="LDL Cholesterol",
                category="Heart & circulation",
                raw="<3",
                operator="<",
                unit="mmol/L",
                low=None,
                high=3,
                status="Normal",
            ),
            ExtractedResult(
                name="Mystery marker",
                category="Diabetes Testing",  # disease header -> must be dropped
                raw="weird",
                operator="?",  # invalid -> must be nulled
            ),
        ],
    )


def test_normalise_coerces_category_operator_and_source():
    out = _normalise(_sample_doc(), "report.pdf")

    assert out["report"]["source_file"] == "report.pdf"
    ldl, mystery = out["results"]
    assert ldl["category"] == "Heart & circulation"
    assert ldl["operator"] == "<"
    assert ldl["high"] == 3 and ldl["low"] is None
    assert ldl["status"] == "Normal"  # stored verbatim (surfacing is blocked in CRUD)
    # disease header dropped; invalid operator nulled
    assert mystery["category"] is None
    assert mystery["operator"] is None


def test_extract_uses_text_path_for_digital_pdf(monkeypatch):
    import whoopdata.biomarkers.pdf_ingest as mod

    monkeypatch.setattr(mod, "_extract_text", lambda b: "x" * 500)
    monkeypatch.setattr(mod, "_extract_from_text", lambda text: _sample_doc())

    def _no_vision(*a, **k):
        raise AssertionError("vision path must not run for a text PDF")

    monkeypatch.setattr(mod, "_extract_from_images", _no_vision)

    out = mod.extract_report_from_pdf(b"%PDF-fake", "f.pdf")
    assert out["report"]["lab_provider"] == "Lab"
    assert len(out["results"]) == 2


def test_extract_falls_back_to_vision_when_no_text(monkeypatch):
    import whoopdata.biomarkers.pdf_ingest as mod

    monkeypatch.setattr(mod, "_extract_text", lambda b: "")
    monkeypatch.setattr(mod, "_render_pages_png", lambda b, **k: [b"png-bytes"])
    monkeypatch.setattr(mod, "_extract_from_images", lambda images: _sample_doc())

    def _no_text(*a, **k):
        raise AssertionError("text path must not run for a scanned PDF")

    monkeypatch.setattr(mod, "_extract_from_text", _no_text)

    out = mod.extract_report_from_pdf(b"%PDF", "f.pdf")
    assert len(out["results"]) == 2


def test_dedupe_keeps_first_occurrence():
    from whoopdata.biomarkers.ingest_service import dedupe_results

    rows = [{"name": "A", "value": 1}, {"name": "A", "value": 2}, {"name": "B"}]
    out = dedupe_results(rows)
    assert [r["name"] for r in out] == ["A", "B"]
    assert out[0]["value"] == 1


def test_summarise_reports_counts():
    from whoopdata.biomarkers.ingest_service import summarise

    s = summarise(
        {"order_number": "O", "taken_on": "2026-06-01", "lab_provider": "L"},
        [{"name": "x", "category": "Liver", "value": 1.0, "low": 0, "high": 2}],
    )
    assert "1 unique biomarkers" in s
    assert "Liver" in s


def test_write_report_isolated_db_never_surfaces_lab_status(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import whoopdata.database.database as dbmod

    engine = create_engine(
        f"sqlite:///{tmp_path/'t.db'}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(dbmod, "engine", engine)
    monkeypatch.setattr(
        dbmod, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )

    from whoopdata.biomarkers.ingest_service import write_report
    from whoopdata.crud import biomarker as crud

    payload = {
        "report": {
            "order_number": "O",
            "taken_on": "2026-06-01",
            "lab_provider": "L",
            "source_file": "f.pdf",
        },
        "results": [
            {
                "name": "LDL Cholesterol",
                "category": "Heart & circulation",
                "raw": "<3",
                "value": None,
                "concept": None,
                "operator": "<",
                "unit": "mmol/L",
                "low": None,
                "high": 3,
                "status": "High",  # must be stored but never surfaced
            }
        ],
    }

    assert write_report(payload) == 1

    db = dbmod.SessionLocal()
    try:
        rows = crud.get_results(db)
    finally:
        db.close()

    assert len(rows) == 1
    assert rows[0]["source_biomarker_name"] == "LDL Cholesterol"
    assert "lab_status" not in rows[0]
    assert "status" not in rows[0]
