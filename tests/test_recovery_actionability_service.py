from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from whoopdata.services.recovery_actionability_service import RecoveryActionabilityService


class _SleepObj:
    def __init__(self, dt: datetime):
        self.start = dt


def test_personalized_bedtime_window_returns_window_when_enough_data():
    service = RecoveryActionabilityService.__new__(RecoveryActionabilityService)
    service.db = None

    sleeps = [_SleepObj(datetime(2026, 3, 1, 22, 0)) for _ in range(12)]
    sleeps += [_SleepObj(datetime(2026, 3, 1, 22, 15)) for _ in range(4)]

    with patch("whoopdata.services.recovery_actionability_service.get_sleep", return_value=sleeps):
        window = service._personalized_bedtime_window()

    assert window is not None
    assert window["start"] <= window["end"]
    assert window["start"] in {"21:45", "22:00"}


def test_best_sleep_hours_threshold_extracts_rule_threshold():
    service = RecoveryActionabilityService.__new__(RecoveryActionabilityService)
    service.db = None

    with patch(
        "whoopdata.services.recovery_actionability_service.results_loader.load_result",
        return_value={
            "rules": [
                {"feature": "strain_3d_sum", "threshold": 34.0},
                {"feature": "sleep_hours", "threshold": 7.0},
            ]
        },
    ):
        threshold = service._best_sleep_hours_threshold()

    assert threshold == 7.0
