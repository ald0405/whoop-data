"""Analytics API routes for advanced health insights.

Provides endpoints for factor analysis, correlations, predictions, and insights.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from whoopdata.database.database import get_db
from whoopdata.analytics.results_loader import results_loader
from whoopdata.schemas.analytics import (
    FactorImportanceResponse,
    CorrelationAnalysisResponse,
    RecoveryPredictionRequest,
    RecoveryPredictionResponse,
    SleepPredictionRequest,
    SleepPredictionResponse,
    InsightResponse,
    PatternDetectionResponse,
    AnalyticsSummaryResponse,
)
from whoopdata.analytics.engine import (
    RecoveryFactorAnalyzer,
    CorrelationAnalyzer,
    InsightGenerator,
    TimeSeriesAnalyzer,
)
from whoopdata.analytics.models import RecoveryPredictor, SleepPredictor
from whoopdata.analytics.model_manager import model_manager
from whoopdata.analytics.data_prep import (
    get_recovery_with_features,
    get_sleep_with_features,
    get_training_data,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/recovery/factors", response_model=FactorImportanceResponse)
async def analyze_recovery_factors(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Analyze what factors influence recovery most.

    Returns pre-computed ranked factors with importance percentages.
    Run the analytics pipeline (option 6) to compute/refresh results.

    Example response includes:
    - Ranked factors (e.g., Sleep Duration: 32%, HRV: 24%)
    - Actionable thresholds for each factor
    - Overall model accuracy (R² score)
    """
    try:
        result = results_loader.load_result("factor_importance", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Analytics not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata before returning
        result.pop("_computed_at", None)
        return FactorImportanceResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading recovery factors: {str(e)}")


@router.get("/sleep/factors")
async def analyze_sleep_quality_factors(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Analyze what factors influence sleep quality (efficiency) most.

    Returns pre-computed ranked factors with importance percentages.
    Run the analytics pipeline (option 6) to compute/refresh results.

    Includes:
    - Ranked factors (e.g., Bedtime: 28%, Day of Week: 15%)
    - Actionable thresholds (optimal bedtime, etc.)
    - Day-of-week sleep patterns
    - Bedtime analysis showing optimal sleep window
    - Overall model accuracy (R² score)
    """
    try:
        result = results_loader.load_result("sleep_quality_factors", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Sleep quality analytics not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata before returning
        result.pop("_computed_at", None)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading sleep quality factors: {str(e)}"
        )


@router.get("/correlations", response_model=CorrelationAnalysisResponse)
async def analyze_correlations(
    days_back: int = Query(365, description="Days of historical data"),
    significance_threshold: float = Query(0.05, description="P-value threshold for significance"),
    db: Session = Depends(get_db),
):
    """Analyze correlations between health metrics.

    Returns pre-computed statistically significant correlations with plain English
    explanations and real examples from your data.

    Example: "Strong correlation (0.72) between sleep quality and recovery -
    your best sleep nights consistently lead to better recovery"
    """
    try:
        result = results_loader.load_result("correlations", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Analytics not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata
        result.pop("_computed_at", None)
        return CorrelationAnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading correlations: {str(e)}")


@router.post("/predict/recovery", response_model=RecoveryPredictionResponse)
async def predict_recovery(request: RecoveryPredictionRequest, db: Session = Depends(get_db)):
    """Predict recovery score from input metrics using pre-trained model.

    Provide sleep hours, HRV, strain, etc. and get predicted recovery score
    with confidence interval and explanation.

    Example: "Based on 8 hours sleep and moderate strain, expect 68% recovery (±5%).
    Sleep duration +25%, low strain +15%, high HRV +10%"
    """
    try:
        # Load pre-trained model
        predictor = model_manager.recovery_predictor

        if predictor is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery model not trained. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Get median values from data for defaults
        df = get_recovery_with_features(db, days_back=365)

        if len(df) < 10:
            raise HTTPException(status_code=400, detail="Insufficient data for prediction defaults")

        # Make prediction
        features = {
            "hrv_rmssd_milli": request.hrv or df["hrv_rmssd_milli"].median(),
            "resting_heart_rate": request.rhr or df["resting_heart_rate"].median(),
            "sleep_hours": request.sleep_hours,
            "sleep_efficiency_percentage": request.sleep_efficiency or 85.0,
            "rem_sleep_hours": request.sleep_hours * 0.2,  # Approximate
            "slow_wave_sleep_hours": request.sleep_hours * 0.15,  # Approximate
            "strain": request.strain or 10.0,
            "sleep_quality_score": (request.sleep_efficiency or 85.0) * 0.5,
        }

        predicted, confidence, contributions = predictor.predict(features)
        explanation = predictor.explain_prediction(features)

        # Determine recovery category
        if predicted >= 67:
            category = "Green"
        elif predicted >= 34:
            category = "Yellow"
        else:
            category = "Red"

        # Format model accuracy
        accuracy_pct = predictor.model_accuracy * 100
        mae_pct = (predictor.mae / 100) * 100  # Convert to percentage
        model_accuracy = (
            f"This model is correct within {mae_pct:.0f}% on {accuracy_pct:.0f}% of predictions"
        )

        return RecoveryPredictionResponse(
            predicted_recovery=predicted,
            confidence_interval=confidence,
            recovery_category=category,
            explanation=explanation,
            contributing_factors=contributions,
            model_accuracy=model_accuracy,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting recovery: {str(e)}")


@router.post("/predict/sleep", response_model=SleepPredictionResponse)
async def predict_sleep_performance(request: SleepPredictionRequest, db: Session = Depends(get_db)):
    """Predict sleep performance from sleep metrics using pre-trained model.

    Provide total sleep hours, REM, and awake time to get predicted
    sleep performance score with explanation.
    """
    try:
        # Load pre-trained model
        predictor = model_manager.sleep_predictor

        if predictor is None:
            raise HTTPException(
                status_code=404,
                detail="Sleep model not trained. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Make prediction
        features = {
            "total_sleep_hours": request.total_sleep_hours,
            "rem_sleep_hours": request.rem_sleep_hours,
            "awake_time_hours": request.awake_time_hours,
        }

        predicted, confidence, contributions = predictor.predict(features)
        explanation = predictor.explain_prediction(features)

        return SleepPredictionResponse(
            predicted_performance=predicted,
            confidence_interval=confidence,
            explanation=explanation,
            contributing_factors=contributions,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting sleep performance: {str(e)}")


@router.get("/insights/weekly", response_model=InsightResponse)
async def get_weekly_insights(
    weeks: int = Query(1, description="Number of weeks to analyze", ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Get automated weekly insights and recommendations.

    Returns pre-computed 3-5 actionable insights about your health data including:
    - Recovery trends
    - Sleep patterns
    - Strain analysis
    - HRV trends
    - Best recovery patterns

    Each insight includes category (success/alert/opportunity) and priority.
    """
    try:
        result = results_loader.load_result("insights")

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Insights not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata
        result.pop("_computed_at", None)
        return InsightResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading insights: {str(e)}")


@router.get("/patterns/{metric}", response_model=PatternDetectionResponse)
async def analyze_metric_pattern(
    metric: str,
    days: int = Query(30, description="Days to analyze", ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Analyze trends and patterns for a specific metric.

    Supported metrics: recovery, hrv, rhr, sleep

    Returns pre-computed:
    - Trend direction (up/down/stable)
    - Trend percentage
    - Data points with annotations
    - Detected anomalies

    Example: "HRV trending up 8% over past 30 days - improvement correlates with consistent sleep"
    """
    try:
        valid_metrics = ["recovery", "hrv", "rhr", "sleep"]
        if metric.lower() not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
            )

        # Load trends result
        trends_result = results_loader.load_result("trends")

        if trends_result is None:
            raise HTTPException(
                status_code=404,
                detail="Trends not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Extract specific metric
        result = trends_result.get(metric.lower())
        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Trend for {metric} not found in computed results."
            )

        return PatternDetectionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading metric pattern: {str(e)}")


@router.get("/recovery/deep-dive")
async def get_recovery_deep_dive(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Get comprehensive recovery deep dive analysis.

    Returns pre-computed analysis including:
    - Recovery by sport/activity type
    - Recovery by workout time of day
    - Impact of HR zone distribution
    - Multi-day strain patterns
    - Day-of-week recovery patterns

    Run the analytics pipeline (option 6) to compute/refresh results.
    """
    try:
        result = results_loader.load_result("recovery_deep_dive", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery deep dive not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata before returning
        result.pop("_computed_at", None)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading recovery deep dive: {str(e)}")


@router.get("/recovery/by-sport")
async def get_recovery_by_sport(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Get recovery analysis by workout sport/activity type.

    Returns which sports/activities lead to best/worst recovery.
    """
    try:
        result = results_loader.load_result("recovery_deep_dive", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery deep dive not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        return result.get("by_sport", {"error": "Sport data not available"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading sport recovery data: {str(e)}")


@router.get("/recovery/by-time-of-day")
async def get_recovery_by_time_of_day(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Get recovery analysis by workout time of day.

    Returns whether morning, afternoon, or evening workouts yield best recovery.
    """
    try:
        result = results_loader.load_result("recovery_deep_dive", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery deep dive not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        return result.get("by_time_of_day", {"error": "Time-of-day data not available"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading time-of-day recovery data: {str(e)}"
        )


@router.get("/recovery/by-hr-zones")
async def get_recovery_by_hr_zones(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Get recovery analysis by HR zone distribution (intensity).

    Returns optimal workout intensity for recovery.
    """
    try:
        result = results_loader.load_result("recovery_deep_dive", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery deep dive not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        return result.get("by_hr_zones", {"error": "HR zone data not available"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading HR zone recovery data: {str(e)}"
        )


@router.get("/recovery/strain-patterns")
async def get_strain_patterns(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db),
):
    """Get analysis of multi-day strain accumulation patterns.

    Returns optimal 3-day strain load for recovery.
    """
    try:
        result = results_loader.load_result("recovery_deep_dive", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery deep dive not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        return result.get("strain_patterns", {"error": "Strain pattern data not available"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading strain pattern data: {str(e)}")


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    days_back: int = Query(365, description="Days of historical data"),
    db: Session = Depends(get_db),
):
    """Get comprehensive analytics summary for dashboard.

    Single pre-computed endpoint that returns:
    - Factor importance analysis
    - Top correlations (5-7 most significant)
    - Weekly insights
    - Recovery trend
    - HRV trend

    Designed for dashboard consumption - all data needed in one call.
    """
    try:
        result = results_loader.load_result("summary", days_back=days_back)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Analytics summary not yet computed. Run the analytics pipeline first (option 6 in CLI).",
            )

        # Remove metadata
        result.pop("_computed_at", None)
        return AnalyticsSummaryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading analytics summary: {str(e)}")
