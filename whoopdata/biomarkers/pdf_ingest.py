"""Extract a blood-test PDF into the biomarker JSON contract.

The output dict matches exactly what ``scripts/seed_biomarkers.py`` already
consumes and what :func:`whoopdata.biomarkers.ingest_service.write_report`
writes::

    {
      "report":  {order_number, taken_on, lab_provider, report_status,
                  biological_sex, source_file},
      "results": [{name, category, raw, value, concept, operator, unit,
                   low, high, status}, ...],
    }

Strategy (text-first, vision-fallback):
- Digital PDFs (selectable text) -> pdfplumber text -> LLM structured output.
- Scanned/image PDFs (little/no text) -> render pages to PNG (PyMuPDF) -> the
  same LLM call with image input.

This module is **pure**: it never touches the database. The caller previews the
result and confirms before writing (CLI ``--commit`` / Telegram confirm button).
The intended-purpose boundary is unchanged -- see
``docs/features/BIOMARKER_INTENDED_PURPOSE.md``.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from whoopdata.agent import settings

# Neutral body-system groups (no disease/condition headers). Source of truth for
# the `category` field; the LLM must map each result into one of these.
ALLOWED_CATEGORIES = [
    "Blood & immune cells",
    "Blood & iron",
    "Body measurements",
    "Bone",
    "Digestive",
    "Heart & circulation",
    "Hormones",
    "Immune & inflammation",
    "Kidney",
    "Liver",
    "Muscle & joint",
    "Pancreas",
    "Sugar & metabolism",
    "Thyroid",
    "Urine",
    "Vitamins & minerals",
]

# Below this many extracted characters we treat the PDF as scanned and use vision.
_TEXT_THRESHOLD = 200
_MAX_VISION_PAGES = 12

_SYSTEM_PROMPT = f"""You extract structured data from a single blood-test / lab report.

Return the report metadata and every individual analyte result. Rules:
- Transcribe values EXACTLY as printed. Never invent, infer, or "correct" a value, unit, or range. If a field is absent, leave it null.
- `raw`: the verbatim result cell text, e.g. "<6.72", "Negative", "144.0".
- `value`: the numeric value as a number when the result is quantitative, else null.
- `concept`: the qualitative result (e.g. "Negative", "Positive", "Not detected") when the result is NOT numeric, else null.
- `operator`: one of "<", ">", "=" if the result cell carries one, else null.
- `unit`: the measurement unit as printed (e.g. "mmol/L", "10^9/l"), else null.
- `low` / `high`: the laboratory's own reference range bounds as numbers. Ranges are often one-sided (e.g. "<3" -> high=3, low=null; ">1" -> low=1, high=null).
- `status`: the lab's own verdict text if shown (e.g. "Normal", "High", "Low", "Low risk"), else null. Transcribe it; it is stored but not displayed.
- `category`: map each result to EXACTLY ONE of these neutral body-system groups (never a disease/condition name): {", ".join(ALLOWED_CATEGORIES)}. If genuinely unclear, use null.
- `taken_on`: the sample/collection date in YYYY-MM-DD format.
- `biological_sex`: "Male"/"Female" if stated, else null.
Extract ALL results across all pages; do not summarise or skip any.
"""


class ExtractedResult(BaseModel):
    """One analyte row, mirroring BiomarkerResult's public fields + status."""

    name: str = Field(description="The biomarker name verbatim from the report")
    category: Optional[str] = Field(default=None, description="Neutral body-system group")
    raw: Optional[str] = Field(default=None, description="Verbatim result cell text")
    value: Optional[float] = Field(default=None, description="Numeric value, if quantitative")
    concept: Optional[str] = Field(default=None, description="Qualitative result, if not numeric")
    operator: Optional[str] = Field(default=None, description='One of "<", ">", "="')
    unit: Optional[str] = None
    low: Optional[float] = Field(default=None, description="Lab reference range lower bound")
    high: Optional[float] = Field(default=None, description="Lab reference range upper bound")
    status: Optional[str] = Field(default=None, description="Lab's own verdict (stored, not shown)")


class ExtractedReport(BaseModel):
    order_number: Optional[str] = None
    taken_on: Optional[str] = Field(default=None, description="Collection date, YYYY-MM-DD")
    lab_provider: Optional[str] = None
    report_status: Optional[str] = None
    biological_sex: Optional[str] = None


class ExtractedDocument(BaseModel):
    report: ExtractedReport
    results: list[ExtractedResult]


def _read_bytes(data: bytes | str | Path) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    return Path(data).read_bytes()


def _extract_text(pdf_bytes: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _render_pages_png(
    pdf_bytes: bytes, max_pages: int = _MAX_VISION_PAGES, dpi: int = 200
) -> list[bytes]:
    import fitz  # PyMuPDF

    images: list[bytes] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            if len(images) >= max_pages:
                break
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
    return images


def _build_structured_llm():
    from langchain.chat_models import init_chat_model

    model = settings.BIOMARKER_OCR_MODEL
    llm = init_chat_model(f"openai:{model}", temperature=0, use_responses_api=False)
    return llm.with_structured_output(ExtractedDocument)


def _extract_from_text(text: str) -> ExtractedDocument:
    from langchain_core.messages import HumanMessage, SystemMessage

    structured = _build_structured_llm()
    return structured.invoke([SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=text)])


def _extract_from_images(images: list[bytes]) -> ExtractedDocument:
    from langchain_core.messages import HumanMessage

    content: list[dict] = [{"type": "text", "text": _SYSTEM_PROMPT}]
    for png in images:
        b64 = base64.b64encode(png).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    structured = _build_structured_llm()
    return structured.invoke([HumanMessage(content=content)])


def _normalise(doc: ExtractedDocument, source_file: str | None) -> dict:
    """Coerce the model output into the seed JSON contract."""
    report = doc.report.model_dump()
    report["source_file"] = source_file

    results: list[dict] = []
    for r in doc.results:
        row = r.model_dump()
        # Drop categories outside the allowed list rather than leak a disease header.
        if row.get("category") not in ALLOWED_CATEGORIES:
            row["category"] = None
        # Normalise operator to the canonical set.
        if row.get("operator") not in ("<", ">", "="):
            row["operator"] = None
        results.append(row)
    return {"report": report, "results": results}


def extract_report_from_pdf(data: bytes | str | Path, source_file: str | None = None) -> dict:
    """Extract a blood-test PDF into the biomarker JSON contract (no DB writes).

    Args:
        data: PDF bytes, or a path to a PDF file.
        source_file: Original filename to record on the report (defaults to the
            path name when ``data`` is a path).

    Returns:
        ``{"report": {...}, "results": [...]}`` ready for
        :func:`whoopdata.biomarkers.ingest_service.write_report`.
    """
    pdf_bytes = _read_bytes(data)
    if source_file is None and isinstance(data, (str, Path)):
        source_file = Path(data).name

    text = _extract_text(pdf_bytes)
    if len(text.strip()) >= _TEXT_THRESHOLD:
        doc = _extract_from_text(text)
    else:
        images = _render_pages_png(pdf_bytes)
        if not images:
            raise ValueError("PDF has no extractable text and no renderable pages.")
        doc = _extract_from_images(images)

    return _normalise(doc, source_file)
