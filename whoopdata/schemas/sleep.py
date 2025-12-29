from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SleepSchema(BaseModel):

    start: datetime
    end: datetime

    respiratory_rate: float
    sleep_performance_percentage: float
    sleep_consistency_percentage: float
    sleep_efficiency_percentage: float

    # --- Stage summary fields ---
    # total_time_in_bed_time_milli = Column(Integer)
    # total_awake_time_milli = Column(Integer)
    # total_no_data_time_milli = Column(Integer)
    # total_slow_wave_sleep_time_milli = Column(Integer)
    # total_rem_sleep_time_milli = Column(Integer)
    sleep_cycle_count: int
    disturbance_count: int

    # --- Sleep needed fields ---
    baseline_sleep_needed_milli: int
    need_from_sleep_debt_milli: int
    need_from_recent_strain_milli: int
    need_from_recent_nap_milli: int
