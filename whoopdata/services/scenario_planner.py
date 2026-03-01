"""Scenario planner for what-if recovery predictions.

Wraps the existing RecoveryPredictor with user-friendly framing:
- Plain-English verdicts
- Baseline comparisons
- Side-by-side scenario comparison
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from statistics import mean

from sqlalchemy.orm import Session

import pandas as pd

from whoopdata.crud.recovery import get_recoveries
from whoopdata.analytics.model_manager import model_manager
from whoopdata.analytics.data_prep import get_recovery_with_features
from whoopdata.schemas.daily import (
    ScenarioInput,
    ScenarioResult,
    ScenarioResponse,
    CompareResponse,
)

logger = logging.getLogger(__name__)


class ScenarioPlanner:
    """Runs what-if scenarios against the recovery prediction model."""

    def __init__(self, db: Session):
        self.db = db
        self._baseline = None
        self._medians = None

    @property
    def baseline_recovery(self) -> float:
        """User's 28-day average recovery score."""
        if self._baseline is None:
            recoveries = get_recoveries(self.db, skip=0, limit=28)
            scores = [r.recovery_score for r in recoveries if r.recovery_score is not None]
            self._baseline = mean(scores) if scores else 50.0
        return self._baseline

    @property
    def feature_medians(self) -> Dict:
        """Median values for ALL model features (used as defaults).

        Computes medians from the same dataset the model was trained on,
        so every feature the model expects has a sensible fallback.
        """
        if self._medians is None:
            df = get_recovery_with_features(self.db, days_back=365)
            # Get the feature names the loaded model actually expects
            predictor = model_manager.recovery_predictor
            feature_names = predictor.feature_names if predictor else []

            if len(df) >= 10 and feature_names:
                self._medians = {}
                for feat in feature_names:
                    if feat in df.columns:
                        val = df[feat].median()
                        self._medians[feat] = float(val) if not pd.isna(val) else 0.0
                    else:
                        self._medians[feat] = 0.0
            else:
                # Hardcoded fallbacks for core features
                self._medians = {
                    "hrv_rmssd_milli": 50.0,
                    "resting_heart_rate": 60.0,
                    "sleep_efficiency_percentage": 85.0,
                    "rem_sleep_hours": 1.5,
                    "slow_wave_sleep_hours": 1.2,
                    "strain": 10.0,
                    "sleep_quality_score": 42.0,
                }
        return self._medians

    def predict_scenario(self, scenario: ScenarioInput) -> ScenarioResponse:
        """Run a single scenario prediction.

        Args:
            scenario: User-provided scenario inputs

        Returns:
            ScenarioResponse with prediction, confidence, and verdict

        Raises:
            ValueError: If recovery prediction model is not available
        """
        predictor = model_manager.recovery_predictor
        if predictor is None:
            raise ValueError(
                "Recovery prediction model not trained. "
                "Run the analytics pipeline first (option 6 in CLI)."
            )

        result = self._run_prediction(predictor, scenario)

        return ScenarioResponse(
            result=result,
            baseline_recovery=round(self.baseline_recovery, 1),
            generated_at=datetime.utcnow(),
        )

    def compare_scenarios(self, scenarios: List[ScenarioInput]) -> CompareResponse:
        """Compare multiple scenarios side-by-side.

        Args:
            scenarios: 2-5 scenario inputs to compare

        Returns:
            CompareResponse with all results and best option

        Raises:
            ValueError: If recovery prediction model is not available
        """
        predictor = model_manager.recovery_predictor
        if predictor is None:
            raise ValueError(
                "Recovery prediction model not trained. "
                "Run the analytics pipeline first (option 6 in CLI)."
            )

        results = []
        for i, scenario in enumerate(scenarios):
            # Auto-label if not provided
            if not scenario.label:
                scenario.label = f"Scenario {i + 1}"
            result = self._run_prediction(predictor, scenario)
            results.append(result)

        # Find best option
        best = max(results, key=lambda r: r.predicted_recovery)
        best_label = best.label or "Scenario 1"

        return CompareResponse(
            results=results,
            best_option=best_label,
            baseline_recovery=round(self.baseline_recovery, 1),
            generated_at=datetime.utcnow(),
        )

    def _run_prediction(self, predictor, scenario: ScenarioInput) -> ScenarioResult:
        """Run the prediction model for a single scenario.

        Starts from the median feature vector and overrides with
        user-provided scenario values + derived estimates.
        """
        medians = self.feature_medians

        # Start with median baseline for every feature the model expects
        features = dict(medians)

        # Override with user-provided values
        features["sleep_hours"] = scenario.sleep_hours
        if scenario.strain is not None:
            features["strain"] = scenario.strain
        if scenario.sleep_efficiency is not None:
            features["sleep_efficiency_percentage"] = scenario.sleep_efficiency
        if scenario.hrv is not None:
            features["hrv_rmssd_milli"] = scenario.hrv
        if scenario.rhr is not None:
            features["resting_heart_rate"] = scenario.rhr

        # Derive dependent features from user inputs
        sleep_h = features["sleep_hours"]
        features["rem_sleep_hours"] = sleep_h * 0.2
        features["slow_wave_sleep_hours"] = sleep_h * 0.15
        features["light_sleep_hours"] = sleep_h * 0.55
        eff = features.get("sleep_efficiency_percentage", 85.0)
        features["sleep_quality_score"] = eff * 0.5

        predicted, confidence, contributions = predictor.predict(features)

        # Clamp prediction to 0-100
        predicted = max(0.0, min(100.0, predicted))
        confidence = (max(0.0, confidence[0]), min(100.0, confidence[1]))

        # Category
        if predicted >= 67:
            category = "green"
        elif predicted >= 34:
            category = "yellow"
        else:
            category = "red"

        # Baseline comparison
        diff = predicted - self.baseline_recovery
        sign = "+" if diff > 0 else ""
        vs_baseline = f"{sign}{diff:.0f}% vs your 28-day average ({self.baseline_recovery:.0f}%)"

        # Plain-English verdict
        verdict = self._generate_verdict(predicted, category, diff)

        return ScenarioResult(
            label=scenario.label,
            predicted_recovery=round(predicted, 1),
            confidence_interval=(round(confidence[0], 1), round(confidence[1], 1)),
            recovery_category=category,
            vs_baseline=vs_baseline,
            verdict=verdict,
            contributing_factors=contributions,
        )

    def _generate_verdict(self, predicted: float, category: str, diff: float) -> str:
        """Generate a plain-English verdict for the scenario."""
        if category == "green":
            if diff > 10:
                return "You'd likely wake up well above your average — go for it"
            return "You'd likely wake up green — a good day ahead"
        elif category == "yellow":
            if diff > 0:
                return "You'd wake up yellow but still above average — moderate intensity is fine"
            return "You'd likely wake up yellow — keep it easy tomorrow"
        else:
            if diff < -10:
                return "This would put you deep in the red — strongly consider a different plan"
            return "You'd likely wake up red — prioritise recovery over training"
