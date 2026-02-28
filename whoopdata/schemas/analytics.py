"""Pydantic schemas for analytics API endpoints."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class FactorImportance(BaseModel):
    """Individual factor importance with explanation."""

    factor_name: str
    importance_percentage: float
    explanation: str
    direction: str  # "positive", "negative", or "neutral"
    actionable_threshold: Optional[str] = None


class FactorImportanceResponse(BaseModel):
    """Response for recovery factor importance analysis."""

    factors: List[FactorImportance]
    top_lever: str  # Plain English summary of #1 factor
    model_accuracy: float  # R² score
    explanation: str  # Overall interpretation


class CorrelationPair(BaseModel):
    """Single correlation relationship."""

    metric_1: str
    metric_2: str
    correlation: float
    p_value: float
    significance: str  # "strong", "moderate", "weak", "not_significant"
    explanation: str  # Plain English interpretation
    example: Optional[str] = None  # Real example from user data


class CorrelationAnalysisResponse(BaseModel):
    """Response for correlation analysis."""

    correlations: List[CorrelationPair]
    summary: str  # Overall interpretation
    timestamp: datetime


class RecoveryPredictionRequest(BaseModel):
    """Request for recovery prediction."""

    sleep_hours: float = Field(..., ge=0, le=14, description="Hours of sleep")
    sleep_efficiency: Optional[float] = Field(
        None, ge=0, le=100, description="Sleep efficiency percentage"
    )
    strain: Optional[float] = Field(None, ge=0, le=21, description="Strain score")
    hrv: Optional[float] = Field(None, ge=0, description="HRV in milliseconds")
    rhr: Optional[float] = Field(None, ge=30, le=120, description="Resting heart rate")


class RecoveryPredictionResponse(BaseModel):
    """Response for recovery prediction."""

    predicted_recovery: float  # Percentage 0-100
    confidence_interval: tuple[float, float]  # (lower, upper)
    recovery_category: str  # "Green", "Yellow", "Red"
    explanation: str  # "Sleep duration +20%, low strain +15%..."
    contributing_factors: Dict[str, float]  # Factor: contribution percentage
    model_accuracy: str  # "This model is correct within 10% on 85% of predictions"


class SleepPredictionRequest(BaseModel):
    """Request for sleep performance prediction."""

    total_sleep_hours: float = Field(..., ge=0, le=14)
    rem_sleep_hours: float = Field(..., ge=0, le=5)
    awake_time_hours: float = Field(..., ge=0, le=5)


class SleepPredictionResponse(BaseModel):
    """Response for sleep performance prediction."""

    predicted_performance: float  # Percentage 0-100
    confidence_interval: tuple[float, float]
    explanation: str
    contributing_factors: Dict[str, float]


class Insight(BaseModel):
    """Single actionable insight."""

    insight_text: str  # Natural language insight
    category: str  # "success", "opportunity", "alert"
    priority: int  # 1-5, 1 being highest priority
    emoji: str  # Visual indicator


class InsightResponse(BaseModel):
    """Response for weekly insights."""

    insights: List[Insight]
    summary: str  # Overall weekly summary
    timestamp: datetime


class TrendPoint(BaseModel):
    """Single point in time series."""

    date: str
    value: float
    annotation: Optional[str] = None  # e.g., "↑ 12% improvement"


class PatternDetectionResponse(BaseModel):
    """Response for pattern/trend detection."""

    metric_name: str
    trend_direction: str  # "up", "down", "stable"
    trend_percentage: float  # Overall change
    trend_description: str  # Plain English
    data_points: List[TrendPoint]
    anomalies: List[str]  # Detected anomalies with context
    timestamp: datetime


class AnalyticsSummaryResponse(BaseModel):
    """Comprehensive analytics summary for dashboard."""

    factor_importance: FactorImportanceResponse
    top_correlations: List[CorrelationPair]  # Top 5-7 only
    weekly_insights: InsightResponse
    recovery_trend: PatternDetectionResponse
    hrv_trend: PatternDetectionResponse
    timestamp: datetime


# =================== MLR Schemas ===================


class MLRCoefficientRow(BaseModel):
    """Single row from an OLS coefficient table."""

    feature: str
    coefficient: float
    std_error: float
    t_value: float
    p_value: float
    significant: bool
    ci_lower: float
    ci_upper: float


class PartialCorrelationRow(BaseModel):
    """Partial correlation for a single feature."""

    feature: str
    partial_correlation: float


class MLRModelResponse(BaseModel):
    """Response for an MLR (OLS) model analysis."""

    coefficients: List[MLRCoefficientRow]
    partial_correlations: List[PartialCorrelationRow]
    r_squared: float
    adj_r_squared: float
    n_observations: int


class CorrelationMatrixResponse(BaseModel):
    """Full correlation matrix for heatmap rendering."""

    features: List[str]
    matrix: List[List[float]]
