"""Model manager for loading and caching trained ML models.

This ensures models are loaded once and reused across requests.
"""

from pathlib import Path
from typing import Optional
import logging

from .models import RecoveryPredictor, SleepPredictor

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton manager for ML models."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize model manager."""
        if self._initialized:
            return

        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.models_dir.mkdir(exist_ok=True)

        self._recovery_predictor: Optional[RecoveryPredictor] = None
        self._sleep_predictor: Optional[SleepPredictor] = None
        self._factor_analyzer_model: Optional[RecoveryPredictor] = None

        self._initialized = True
        logger.info(f"ModelManager initialized. Models directory: {self.models_dir}")

    @property
    def recovery_predictor(self) -> Optional[RecoveryPredictor]:
        """Get recovery predictor model (loads if not cached)."""
        if self._recovery_predictor is None:
            model_path = self.models_dir / "recovery_predictor.pkl"
            if model_path.exists():
                logger.info("Loading recovery predictor from disk...")
                self._recovery_predictor = RecoveryPredictor(str(model_path))
                logger.info("✅ Recovery predictor loaded")
            else:
                logger.warning(f"Recovery predictor not found at {model_path}")
        return self._recovery_predictor

    @property
    def sleep_predictor(self) -> Optional[SleepPredictor]:
        """Get sleep predictor model (loads if not cached)."""
        if self._sleep_predictor is None:
            model_path = self.models_dir / "sleep_predictor.pkl"
            if model_path.exists():
                logger.info("Loading sleep predictor from disk...")
                self._sleep_predictor = SleepPredictor(str(model_path))
                logger.info("✅ Sleep predictor loaded")
            else:
                logger.warning(f"Sleep predictor not found at {model_path}")
        return self._sleep_predictor

    @property
    def factor_analyzer_model(self) -> Optional[RecoveryPredictor]:
        """Get factor analyzer model (loads if not cached)."""
        if self._factor_analyzer_model is None:
            model_path = self.models_dir / "factor_analyzer.pkl"
            if model_path.exists():
                logger.info("Loading factor analyzer from disk...")
                self._factor_analyzer_model = RecoveryPredictor(str(model_path))
                logger.info("✅ Factor analyzer loaded")
            else:
                logger.warning(f"Factor analyzer not found at {model_path}")
        return self._factor_analyzer_model

    def reload_models(self):
        """Force reload all models from disk."""
        logger.info("Reloading all models...")
        self._recovery_predictor = None
        self._sleep_predictor = None
        self._factor_analyzer_model = None

        # Trigger lazy loading
        _ = self.recovery_predictor
        _ = self.sleep_predictor
        _ = self.factor_analyzer_model

    def models_exist(self) -> bool:
        """Check if all required models exist."""
        return all(
            [
                (self.models_dir / "recovery_predictor.pkl").exists(),
                (self.models_dir / "sleep_predictor.pkl").exists(),
                (self.models_dir / "factor_analyzer.pkl").exists(),
            ]
        )


# Global instance
model_manager = ModelManager()
