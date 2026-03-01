"""Machine learning models for health predictions.

Includes recovery and sleep prediction models with explainability.
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import cross_val_score
import xgboost as xgb

# Try to import SHAP for explainability (optional dependency)
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class RecoveryPredictor:
    """Predict recovery scores from health metrics with explainability."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize recovery predictor.

        Args:
            model_path: Path to saved model (if loading existing)
        """
        self.model = None
        self.feature_names = [
            "hrv_rmssd_milli",
            "resting_heart_rate",
            "sleep_hours",
            "sleep_efficiency_percentage",
            "rem_sleep_hours",
            "slow_wave_sleep_hours",
            "strain",
            "sleep_quality_score",
        ]
        self.scaler = None
        self.imputer = None
        self.model_accuracy = None
        self.mae = None

        if model_path and Path(model_path).exists():
            self.load(model_path)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        feature_names: Optional[list] = None,
    ):
        """Train the recovery prediction model.

        Args:
            X_train: Training features
            y_train: Training targets (recovery scores)
            X_test: Test features
            y_test: Test targets
            feature_names: Names of features (must match X_train columns)
        """
        if feature_names is not None:
            self.feature_names = feature_names
        # Use RandomForest for interpretability and performance
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        self.model.fit(X_train, y_train)

        # Calculate accuracy metrics
        y_pred = self.model.predict(X_test)
        self.model_accuracy = r2_score(y_test, y_pred)
        self.mae = mean_absolute_error(y_test, y_pred)

    def predict(
        self, features: Dict[str, float]
    ) -> Tuple[float, Tuple[float, float], Dict[str, float]]:
        """Predict recovery score with confidence interval and explanation.

        Args:
            features: Dictionary of feature values

        Returns:
            Tuple of (predicted_score, confidence_interval, feature_contributions)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Create feature array in correct order
        X = np.array([[features.get(feat, 0) for feat in self.feature_names]])

        # Get prediction from all trees for confidence interval
        predictions = np.array([tree.predict(X) for tree in self.model.estimators_])
        predicted_recovery = predictions.mean()

        # 95% confidence interval
        confidence_lower = np.percentile(predictions, 2.5)
        confidence_upper = np.percentile(predictions, 97.5)

        # Feature importance as contributions
        feature_importance = self.model.feature_importances_
        contributions = {
            feat: float(importance * 100)
            for feat, importance in zip(self.feature_names, feature_importance)
        }

        return (
            float(predicted_recovery),
            (float(confidence_lower), float(confidence_upper)),
            contributions,
        )

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance percentages.

        Returns:
            Dictionary of feature names to importance percentages
        """
        if self.model is None:
            raise ValueError("Model not trained")

        importance = self.model.feature_importances_
        return {feat: float(imp * 100) for feat, imp in zip(self.feature_names, importance)}

    def explain_prediction(self, features: Dict[str, float]) -> str:
        """Generate plain English explanation of prediction.

        Args:
            features: Feature values used for prediction

        Returns:
            Plain English explanation
        """
        contributions = self.get_feature_importance()
        top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]

        explanation_parts = []
        for feat, contrib in top_factors:
            # Friendly feature names
            friendly_names = {
                "sleep_hours": "Sleep duration",
                "sleep_efficiency_percentage": "Sleep efficiency",
                "hrv_rmssd_milli": "HRV",
                "resting_heart_rate": "Resting heart rate",
                "rem_sleep_hours": "REM sleep",
                "slow_wave_sleep_hours": "Deep sleep",
                "strain": "Strain level",
                "sleep_quality_score": "Sleep quality",
            }
            friendly = friendly_names.get(feat, feat)
            explanation_parts.append(f"{friendly} +{contrib:.0f}%")

        return ", ".join(explanation_parts)

    def save(self, path: str):
        """Save model to disk."""
        model_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "model_accuracy": self.model_accuracy,
            "mae": self.mae,
        }
        with open(path, "wb") as f:
            pickle.dump(model_data, f)

    def load(self, path: str):
        """Load model from disk."""
        with open(path, "rb") as f:
            model_data = pickle.load(f)
        self.model = model_data["model"]
        self.feature_names = model_data["feature_names"]
        self.model_accuracy = model_data.get("model_accuracy")
        self.mae = model_data.get("mae")


class SleepPredictor:
    """Predict sleep efficiency from comprehensive sleep metrics using XGBoost."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize sleep predictor.

        Args:
            model_path: Path to saved model (if loading existing)
        """
        self.model = None
        # Expanded feature set with temporal and contextual factors
        self.feature_names = [
            "total_sleep_hours",
            "rem_sleep_hours",
            "slow_wave_sleep_hours",
            "awake_time_hours",
            "bedtime_hour",
            "day_of_week",
            "respiratory_rate",
            "prev_strain",
            "prev_recovery_score",
            "sleep_debt_hours",
            "sleep_deficit",
            "disturbance_count",
            "bedtime_consistency_score",
        ]
        self.model_accuracy = None
        self.mae = None

        if model_path and Path(model_path).exists():
            self.load(model_path)

    def train(
        self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray
    ):
        """Train the sleep efficiency prediction model.

        Args:
            X_train: Training features
            y_train: Training targets (sleep efficiency %)
            X_test: Test features
            y_test: Test targets
        """
        self.model = xgb.XGBRegressor(
            objective="reg:squarederror",
            n_estimators=150,
            learning_rate=0.08,
            max_depth=7,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        )

        self.model.fit(X_train, y_train)

        # Calculate accuracy
        y_pred = self.model.predict(X_test)
        self.model_accuracy = r2_score(y_test, y_pred)
        self.mae = mean_absolute_error(y_test, y_pred)

    def predict(
        self, features: Dict[str, float]
    ) -> Tuple[float, Tuple[float, float], Dict[str, float]]:
        """Predict sleep efficiency with confidence interval.

        Args:
            features: Dictionary of feature values

        Returns:
            Tuple of (predicted_efficiency, confidence_interval, feature_contributions)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        X = np.array([[features.get(feat, 0) for feat in self.feature_names]])
        predicted_efficiency = float(self.model.predict(X)[0])

        # Simple confidence interval based on MAE
        confidence_lower = max(0, predicted_efficiency - (self.mae * 1.96))
        confidence_upper = min(100, predicted_efficiency + (self.mae * 1.96))

        # Feature importance
        feature_importance = self.model.feature_importances_
        contributions = {
            feat: float(importance * 100)
            for feat, importance in zip(self.feature_names, feature_importance)
        }

        return predicted_efficiency, (confidence_lower, confidence_upper), contributions

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance percentages."""
        if self.model is None:
            raise ValueError("Model not trained")

        importance = self.model.feature_importances_
        return {feat: float(imp * 100) for feat, imp in zip(self.feature_names, importance)}

    def explain_prediction(self, features: Dict[str, float]) -> str:
        """Generate plain English explanation."""
        contributions = self.get_feature_importance()
        top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]  # Top 3

        explanation_parts = []
        for feat, contrib in top_factors:
            friendly_names = {
                "total_sleep_hours": "Sleep duration",
                "rem_sleep_hours": "REM sleep",
                "slow_wave_sleep_hours": "Deep sleep",
                "awake_time_hours": "Time awake",
                "bedtime_hour": "Bedtime",
                "day_of_week": "Day of week",
                "respiratory_rate": "Respiratory rate",
                "prev_strain": "Previous day strain",
                "prev_recovery_score": "Previous recovery",
                "sleep_debt_hours": "Sleep debt",
                "sleep_deficit": "Sleep deficit",
                "disturbance_count": "Disturbances",
                "bedtime_consistency_score": "Bedtime consistency",
            }
            friendly = friendly_names.get(feat, feat)
            explanation_parts.append(f"{friendly} ({contrib:.0f}%)")

        return ", ".join(explanation_parts)

    def save(self, path: str):
        """Save model to disk."""
        model_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "model_accuracy": self.model_accuracy,
            "mae": self.mae,
        }
        with open(path, "wb") as f:
            pickle.dump(model_data, f)

    def load(self, path: str):
        """Load model from disk."""
        with open(path, "rb") as f:
            model_data = pickle.load(f)
        self.model = model_data["model"]
        self.feature_names = model_data["feature_names"]
        self.model_accuracy = model_data.get("model_accuracy")
        self.mae = model_data.get("mae")
