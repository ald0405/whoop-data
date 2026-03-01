from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Cycle(Base):
    __tablename__ = "cycles"
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
    __tablename__ = "sleep"

    id = Column(Integer, primary_key=True, autoincrement=True)
    whoop_id = Column(String, unique=True, nullable=False)  # WHOOP API string ID
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
    __tablename__ = "recovery"
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
            return "Green"
        elif 34 <= self.recovery_score < 67:
            return "Yellow"
        else:
            return "Red"

    def is_weekend(self) -> bool:
        if self.created_at:
            return self.created_at.weekday() > 4  # 5 = Saturday, 6 = Sunday
        return False


class Workout(Base):
    __tablename__ = "workout"

    id = Column(Integer, primary_key=True, autoincrement=True)
    whoop_id = Column(String, unique=True, nullable=False)  # WHOOP API string ID
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


class WithingsWeight(Base):
    __tablename__ = "withings_weight"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    grpid = Column(Integer)  # Withings group ID
    deviceid = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    date = Column(Integer)  # Unix timestamp from Withings
    datetime = Column(DateTime)  # Converted datetime
    timezone = Column(String)
    comment = Column(String)
    category = Column(Integer)  # 1 for real measures, 2 for objectives

    # Weight measurements
    weight_kg = Column(Float)
    height_m = Column(Float)
    fat_free_mass_kg = Column(Float)
    fat_ratio_percent = Column(Float)
    fat_mass_kg = Column(Float)

    # Additional body composition (optional)
    muscle_mass_kg = Column(Float)
    bone_mass_kg = Column(Float)
    hydration_kg = Column(Float)
    visceral_fat = Column(Float)

    def __repr__(self):
        return f"<WithingsWeight(user_id='{self.user_id}', weight={self.weight_kg}kg, date='{self.datetime}')>"

    def bmi(self):
        """Calculate BMI if both weight and height are available"""
        if self.weight_kg and self.height_m and self.height_m > 0:
            return round(self.weight_kg / (self.height_m**2), 1)
        return None

    def weight_category(self):
        """BMI-based weight category"""
        bmi = self.bmi()
        if bmi is None:
            return "Unknown"
        elif bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 25:
            return "Normal"
        elif 25 <= bmi < 30:
            return "Overweight"
        else:
            return "Obese"


class WithingsHeartRate(Base):
    __tablename__ = "withings_heart_rate"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    grpid = Column(Integer)  # Withings group ID
    deviceid = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    date = Column(Integer)  # Unix timestamp
    datetime = Column(DateTime)  # Converted datetime
    timezone = Column(String)
    category = Column(Integer)

    # Heart rate and blood pressure measurements
    heart_rate_bpm = Column(Float)
    systolic_bp_mmhg = Column(Float)
    diastolic_bp_mmhg = Column(Float)

    def __repr__(self):
        return f"<WithingsHeartRate(user_id='{self.user_id}', hr={self.heart_rate_bpm}bpm, date='{self.datetime}')>"

    def bp_category(self):
        """Blood pressure category based on AHA guidelines"""
        if not self.systolic_bp_mmhg or not self.diastolic_bp_mmhg:
            return "Unknown"

        systolic = self.systolic_bp_mmhg
        diastolic = self.diastolic_bp_mmhg

        if systolic < 120 and diastolic < 80:
            return "Normal"
        elif systolic < 130 and diastolic < 80:
            return "Elevated"
        elif (130 <= systolic < 140) or (80 <= diastolic < 90):
            return "Stage 1 High"
        elif (140 <= systolic < 180) or (90 <= diastolic < 120):
            return "Stage 2 High"
        else:
            return "Crisis"


class Recommendation(Base):
    """Daily recommendations generated by the daily engine."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)  # Date the recommendation was for
    action_text = Column(String, nullable=False)
    category = Column(String, nullable=False)  # training, sleep, recovery, lifestyle
    target_metric = Column(String)  # e.g. "sleep_hours", "recovery_score"
    target_value = Column(Float)  # e.g. 8.0 for sleep hours
    created_at = Column(DateTime, default=datetime.utcnow)

    outcomes = relationship(
        "RecommendationOutcome", back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationOutcome(Base):
    """Tracks whether recommendations were followed and their outcomes."""
    __tablename__ = "recommendation_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False)
    actual_metric = Column(String)  # Same as target_metric
    actual_value = Column(Float)  # What actually happened
    followed = Column(Boolean)  # Was the recommendation followed?
    outcome_delta = Column(Float)  # Difference from target
    recovery_score = Column(Float)  # Recovery score on the outcome day
    recorded_at = Column(DateTime, default=datetime.utcnow)

    recommendation = relationship("Recommendation", back_populates="outcomes")
