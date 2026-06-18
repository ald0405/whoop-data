"""Pydantic schemas for the biomarker analyser (Phase 0 prototype).

These describe the agent-facing shape of a result. Crucially, ``lab_status``
is NOT part of any agent-facing schema — the lab's own verdict is never
surfaced. See docs/features/BIOMARKER_INTENDED_PURPOSE.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BiomarkerResultPublic(BaseModel):
    """A single result as the agent is allowed to see it (no lab_status)."""

    source_biomarker_name: str
    category: Optional[str] = None
    result_raw: Optional[str] = None
    value_as_number: Optional[float] = None
    value_as_concept: Optional[str] = None
    operator: Optional[str] = None
    unit: Optional[str] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None

    class Config:
        from_attributes = True


class BiomarkerEducationPublic(BaseModel):
    """Generic glossary entry: definition + normal function only."""

    source_biomarker_name: str
    what_it_is: Optional[str] = None
    physiological_function: Optional[str] = None

    class Config:
        from_attributes = True


class BiomarkerReportPublic(BaseModel):
    """Report-level metadata for the single active result set."""

    order_number: Optional[str] = None
    taken_on: Optional[datetime] = None
    lab_provider: Optional[str] = None
    report_status: Optional[str] = None

    class Config:
        from_attributes = True
