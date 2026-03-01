"""Pydantic schemas for the daily decision engine and scenario planner."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


# =================== Daily Action Card ===================


class RecoveryStatus(BaseModel):
    """Current recovery state with explanation."""

    score: float
    category: str  # "green", "yellow", "red"
    hrv: Optional[float] = None
    resting_heart_rate: Optional[float] = None
    key_driver: str  # e.g. "Sleep duration was your top recovery driver"
    vs_baseline: Optional[str] = None  # e.g. "+8% above your 28-day average"


class DailyAction(BaseModel):
    """Single prioritised action for the day."""

    action: str  # e.g. "Keep training intensity moderate-to-high"
    reasoning: str  # e.g. "Your recovery is green and HRV is above your 7-day average"
    category: str  # "training", "sleep", "recovery", "lifestyle"
    priority: int  # 1 = highest


class SleepTarget(BaseModel):
    """Tonight's sleep recommendation."""

    target_bedtime: Optional[str] = None  # "22:30"
    target_hours: float  # 8.0
    reasoning: str  # "Your best recoveries come with 7.5+ hours"


class ContextSummary(BaseModel):
    """Environmental context that affects daily planning."""

    weather: Optional[str] = None  # "14°C, rain until 2pm, clear afternoon"
    air_quality: Optional[str] = None  # "Good (AQI 2)"
    transport: Optional[str] = None  # "All lines running normally"
    outdoor_window: Optional[str] = None  # "Best outdoor window: 2-5pm"


class DailyPlanResponse(BaseModel):
    """Complete daily action card response."""

    recovery_status: RecoveryStatus
    actions: List[DailyAction]
    sleep_target: SleepTarget
    context: ContextSummary
    generated_at: datetime


# =================== Scenario Planner ===================


class ScenarioInput(BaseModel):
    """Input for a single recovery scenario."""

    label: Optional[str] = None  # "Option A: Early night"
    sleep_hours: float = Field(..., ge=0, le=14)
    sleep_efficiency: Optional[float] = Field(None, ge=0, le=100)
    strain: Optional[float] = Field(None, ge=0, le=21)
    hrv: Optional[float] = Field(None, ge=0)
    rhr: Optional[float] = Field(None, ge=30, le=120)


class ScenarioResult(BaseModel):
    """Prediction result for a single scenario."""

    label: Optional[str] = None
    predicted_recovery: float
    confidence_interval: tuple[float, float]
    recovery_category: str  # "green", "yellow", "red"
    vs_baseline: str  # "+12% above your average" or "-5% below your average"
    verdict: str  # "You'd likely wake up green — go for it"
    contributing_factors: Dict[str, float]


class ScenarioRequest(BaseModel):
    """Request for single scenario prediction."""

    scenario: ScenarioInput


class ScenarioResponse(BaseModel):
    """Response for single scenario prediction."""

    result: ScenarioResult
    baseline_recovery: float  # User's 28-day average for comparison
    generated_at: datetime


class CompareRequest(BaseModel):
    """Request to compare multiple scenarios."""

    scenarios: List[ScenarioInput] = Field(..., min_length=2, max_length=5)


class CompareResponse(BaseModel):
    """Response comparing multiple scenarios."""

    results: List[ScenarioResult]
    best_option: str  # Label of the best scenario
    baseline_recovery: float
    generated_at: datetime
