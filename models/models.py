from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime 
Base = declarative_base()

class Cycle(Base):
    __tablename__ = 'cycles'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    start = Column(DateTime)
    end = Column(DateTime)
    timezone_offset = Column(String)
    score_state = Column(String)
    strain = Column(Float)
    kilojoule = Column(Float)
    average_heart_rate = Column(Float)
    max_heart_rate = Column(Float)

    # relationships
    recoveries = relationship("Recovery", back_populates="cycle", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="cycle", cascade="all, delete-orphan")

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import relationship

class Sleep(Base):
    __tablename__ = 'sleep'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    start = Column(DateTime)
    end = Column(DateTime)
    timezone_offset = Column(String)
    nap = Column(Boolean)
    score_state = Column(String)

    respiratory_rate = Column(Float)
    sleep_performance_percentage = Column(Float)
    sleep_consistency_percentage = Column(Float)
    sleep_efficiency_percentage = Column(Float)

    # --- Stage summary fields ---
    total_time_in_bed_time_milli = Column(Integer)
    total_awake_time_milli = Column(Integer)
    total_no_data_time_milli = Column(Integer)
    total_slow_wave_sleep_time_milli = Column(Integer)
    total_rem_sleep_time_milli = Column(Integer)
    sleep_cycle_count = Column(Integer)
    disturbance_count = Column(Integer)

    # --- Sleep needed fields ---
    baseline_sleep_needed_milli = Column(Integer)
    need_from_sleep_debt_milli = Column(Integer)
    need_from_recent_strain_milli = Column(Integer)
    need_from_recent_nap_milli = Column(Integer)

    # Relationships
    recoveries = relationship("Recovery", back_populates="sleep", cascade="all, delete-orphan")

class Recovery(Base):
    __tablename__ = 'recovery'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    cycle_id = Column(Integer, ForeignKey("cycles.id"))
    sleep_id = Column(Integer, ForeignKey("sleep.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    score_state = Column(String)
    user_calibrating = Column(Boolean)
    recovery_score = Column(Float)
    resting_heart_rate = Column(Float)
    hrv_rmssd_milli = Column(Float)
    spo2_percentage = Column(Float)
    skin_temp_celsius = Column(Float)
    # relationships
    cycle = relationship("Cycle", back_populates="recoveries")
    sleep = relationship("Sleep", back_populates="recoveries")

    def recovery_category(self):
        if self.recovery_score >= 67:
            return 'Green'
        elif 34 <= self.recovery_score < 67:
            return 'Yellow'
        else:
            return 'Red'
    
    def is_weekend(self) -> bool:
        if self.created_at:
            return self.created_at.weekday() > 4  # 5 = Saturday, 6 = Sunday
        return False

class Workout(Base):
    __tablename__ = 'workout'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    cycle_id = Column(Integer, ForeignKey("cycles.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    start = Column(DateTime)
    end = Column(DateTime)
    timezone_offset = Column(String)
    sport_id = Column(Integer)
    score_state = Column(String)
    strain = Column(Float)
    average_heart_rate = Column(Float)
    max_heart_rate = Column(Float)
    kilojoule = Column(Float)
    percent_recorded = Column(Float)
    distance_meter = Column(Float)
    altitude_gain_meter = Column(Float)
    altitude_change_meter = Column(Float)

    # New zone duration fields (in minutes)
    zone_zero_minutes = Column(Float)
    zone_one_minutes = Column(Float)
    zone_two_minutes = Column(Float)
    zone_three_minutes = Column(Float)
    zone_four_minutes = Column(Float)
    zone_five_minutes = Column(Float)

    cycle = relationship("Cycle", back_populates="workouts")

