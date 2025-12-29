"""Analytics API routes for advanced health insights.

Provides endpoints for factor analysis, correlations, predictions, and insights.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from whoopdata.database.database import get_db
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
from whoopdata.analytics.data_prep import get_recovery_with_features, get_sleep_with_features, get_training_data

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/recovery/factors", response_model=FactorImportanceResponse)
async def analyze_recovery_factors(
    days_back: int = Query(365, description="Days of historical data to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze what factors influence recovery most.
    
    Returns ranked factors with importance percentages and plain English explanations.
    Trains a RandomForest model to determine feature importance.
    
    Example response includes:
    - Ranked factors (e.g., Sleep Duration: 32%, HRV: 24%)
    - Actionable thresholds for each factor
    - Overall model accuracy (R² score)
    """
    try:
        analyzer = RecoveryFactorAnalyzer(db)
        result = analyzer.analyze(days_back=days_back)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return FactorImportanceResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing recovery factors: {str(e)}"
        )


@router.get("/correlations", response_model=CorrelationAnalysisResponse)
async def analyze_correlations(
    days_back: int = Query(365, description="Days of historical data"),
    significance_threshold: float = Query(0.05, description="P-value threshold for significance"),
    db: Session = Depends(get_db)
):
    """Analyze correlations between health metrics.
    
    Returns statistically significant correlations (p < 0.05) with plain English
    explanations and real examples from your data.
    
    Example: "Strong correlation (0.72) between sleep quality and recovery -
    your best sleep nights consistently lead to better recovery"
    """
    try:
        analyzer = CorrelationAnalyzer(db)
        result = analyzer.analyze(days_back=days_back, significance_threshold=significance_threshold)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return CorrelationAnalysisResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing correlations: {str(e)}"
        )


@router.post("/predict/recovery", response_model=RecoveryPredictionResponse)
async def predict_recovery(
    request: RecoveryPredictionRequest,
    db: Session = Depends(get_db)
):
    """Predict recovery score from input metrics.
    
    Provide sleep hours, HRV, strain, etc. and get predicted recovery score
    with confidence interval and explanation.
    
    Example: "Based on 8 hours sleep and moderate strain, expect 68% recovery (±5%).
    Sleep duration +25%, low strain +15%, high HRV +10%"
    """
    try:
        # Get training data
        df = get_recovery_with_features(db, days_back=365)
        
        if len(df) < 50:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data to train prediction model (need 50+ records)"
            )
        
        feature_cols = [
            'hrv_rmssd_milli',
            'resting_heart_rate',
            'sleep_hours',
            'sleep_efficiency_percentage',
            'rem_sleep_hours',
            'slow_wave_sleep_hours',
            'strain',
            'sleep_quality_score',
        ]
        
        df_clean = df[feature_cols + ['recovery_score']].dropna()
        X_train, X_test, y_train, y_test, _, _ = get_training_data(
            df_clean,
            target_col='recovery_score',
            feature_cols=feature_cols,
            scale_features=False
        )
        
        # Train predictor
        predictor = RecoveryPredictor()
        predictor.train(X_train, y_train, X_test, y_test)
        
        # Make prediction
        features = {
            'hrv_rmssd_milli': request.hrv or df['hrv_rmssd_milli'].median(),
            'resting_heart_rate': request.rhr or df['resting_heart_rate'].median(),
            'sleep_hours': request.sleep_hours,
            'sleep_efficiency_percentage': request.sleep_efficiency or 85.0,
            'rem_sleep_hours': request.sleep_hours * 0.2,  # Approximate
            'slow_wave_sleep_hours': request.sleep_hours * 0.15,  # Approximate
            'strain': request.strain or 10.0,
            'sleep_quality_score': (request.sleep_efficiency or 85.0) * 0.5
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
        model_accuracy = f"This model is correct within {mae_pct:.0f}% on {accuracy_pct:.0f}% of predictions"
        
        return RecoveryPredictionResponse(
            predicted_recovery=predicted,
            confidence_interval=confidence,
            recovery_category=category,
            explanation=explanation,
            contributing_factors=contributions,
            model_accuracy=model_accuracy
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error predicting recovery: {str(e)}"
        )


@router.post("/predict/sleep", response_model=SleepPredictionResponse)
async def predict_sleep_performance(
    request: SleepPredictionRequest,
    db: Session = Depends(get_db)
):
    """Predict sleep performance from sleep metrics.
    
    Provide total sleep hours, REM, and awake time to get predicted
    sleep performance score with explanation.
    """
    try:
        # Get training data
        df = get_sleep_with_features(db, days_back=365)
        
        if len(df) < 30:
            raise HTTPException(
                status_code=400,
                detail="Insufficient sleep data for prediction"
            )
        
        feature_cols = ['total_sleep_hours', 'rem_sleep_hours', 'awake_time_hours']
        df_clean = df[feature_cols + ['sleep_performance_percentage']].dropna()
        
        X_train, X_test, y_train, y_test, _, _ = get_training_data(
            df_clean,
            target_col='sleep_performance_percentage',
            feature_cols=feature_cols,
            scale_features=False
        )
        
        # Train predictor
        predictor = SleepPredictor()
        predictor.train(X_train, y_train, X_test, y_test)
        
        # Make prediction
        features = {
            'total_sleep_hours': request.total_sleep_hours,
            'rem_sleep_hours': request.rem_sleep_hours,
            'awake_time_hours': request.awake_time_hours
        }
        
        predicted, confidence, contributions = predictor.predict(features)
        explanation = predictor.explain_prediction(features)
        
        return SleepPredictionResponse(
            predicted_performance=predicted,
            confidence_interval=confidence,
            explanation=explanation,
            contributing_factors=contributions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error predicting sleep performance: {str(e)}"
        )


@router.get("/insights/weekly", response_model=InsightResponse)
async def get_weekly_insights(
    weeks: int = Query(1, description="Number of weeks to analyze", ge=1, le=12),
    db: Session = Depends(get_db)
):
    """Get automated weekly insights and recommendations.
    
    Returns 3-5 actionable insights about your health data including:
    - Recovery trends
    - Sleep patterns
    - Strain analysis
    - HRV trends
    - Best recovery patterns
    
    Each insight includes category (success/alert/opportunity) and priority.
    """
    try:
        generator = InsightGenerator(db)
        result = generator.generate_weekly_insights(weeks=weeks)
        
        return InsightResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(e)}"
        )


@router.get("/patterns/{metric}", response_model=PatternDetectionResponse)
async def analyze_metric_pattern(
    metric: str,
    days: int = Query(30, description="Days to analyze", ge=7, le=365),
    db: Session = Depends(get_db)
):
    """Analyze trends and patterns for a specific metric.
    
    Supported metrics: recovery, hrv, rhr, sleep
    
    Returns:
    - Trend direction (up/down/stable)
    - Trend percentage
    - Data points with annotations
    - Detected anomalies
    
    Example: "HRV trending up 8% over past 30 days - improvement correlates with consistent sleep"
    """
    try:
        valid_metrics = ['recovery', 'hrv', 'rhr', 'sleep']
        if metric.lower() not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
            )
        
        analyzer = TimeSeriesAnalyzer(db)
        result = analyzer.analyze_metric(metric.lower(), days=days)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return PatternDetectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing metric pattern: {str(e)}"
        )


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    days_back: int = Query(365, description="Days of historical data"),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics summary for dashboard.
    
    Single endpoint that returns:
    - Factor importance analysis
    - Top correlations (5-7 most significant)
    - Weekly insights
    - Recovery trend
    - HRV trend
    
    Designed for dashboard consumption - all data needed in one call.
    """
    try:
        # Factor importance
        factor_analyzer = RecoveryFactorAnalyzer(db)
        factor_result = factor_analyzer.analyze(days_back=days_back)
        
        if "error" in factor_result:
            # Return minimal response if not enough data
            raise HTTPException(status_code=400, detail=factor_result["error"])
        
        factor_importance = FactorImportanceResponse(**factor_result)
        
        # Correlations (top 7)
        corr_analyzer = CorrelationAnalyzer(db)
        corr_result = corr_analyzer.analyze(days_back=days_back)
        top_correlations = corr_result.get("correlations", [])[:7]
        
        # Weekly insights
        insight_generator = InsightGenerator(db)
        insights_result = insight_generator.generate_weekly_insights(weeks=1)
        weekly_insights = InsightResponse(**insights_result)
        
        # Trends
        trend_analyzer = TimeSeriesAnalyzer(db)
        recovery_trend_result = trend_analyzer.analyze_metric('recovery', days=30)
        hrv_trend_result = trend_analyzer.analyze_metric('hrv', days=30)
        
        recovery_trend = PatternDetectionResponse(**recovery_trend_result)
        hrv_trend = PatternDetectionResponse(**hrv_trend_result)
        
        return AnalyticsSummaryResponse(
            factor_importance=factor_importance,
            top_correlations=top_correlations,
            weekly_insights=weekly_insights,
            recovery_trend=recovery_trend,
            hrv_trend=hrv_trend,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating analytics summary: {str(e)}"
        )
