"""Advanced analytics module for health data insights.

This module provides:
- Feature importance analysis (what drives recovery?)
- Correlation analysis (how metrics relate)
- Predictive models (recovery & sleep predictions)
- Automated insight generation
- Time series analysis
"""

from .engine import (
    RecoveryFactorAnalyzer,
    CorrelationAnalyzer,
    InsightGenerator,
    TimeSeriesAnalyzer,
)
from .models import RecoveryPredictor, SleepPredictor
from .data_prep import (
    get_recovery_with_features,
    get_sleep_with_features,
    get_training_data,
)

__all__ = [
    "RecoveryFactorAnalyzer",
    "CorrelationAnalyzer",
    "InsightGenerator",
    "TimeSeriesAnalyzer",
    "RecoveryPredictor",
    "SleepPredictor",
    "get_recovery_with_features",
    "get_sleep_with_features",
    "get_training_data",
]
