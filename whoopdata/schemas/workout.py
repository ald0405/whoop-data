from pydantic import BaseModel, field_serializer, Field, computed_field
from typing import Optional
from datetime import datetime


class Workouts(BaseModel):
    user_id: Optional[str]
    created_at: datetime
    start: datetime
    end: datetime
    sport_id: int
    strain: Optional[float]
    average_heart_rate: Optional[float]
    max_heart_rate: Optional[float]
    distance_meter: Optional[float]
    altitude_gain_meter: Optional[float]
    altitude_change_meter: Optional[float]
    zone_zero_minutes: Optional[float]
    zone_one_minutes: Optional[float]
    zone_two_minutes: Optional[float]
    zone_three_minutes: Optional[float]
    zone_four_minutes: Optional[float]
    zone_five_minutes: Optional[float]
    trimp_score: Optional[float] = None

    @computed_field
    @property
    def sport_name(self) -> str:
        """Get human-readable sport name from sport_id."""
        from whoopdata.utils.sport_mapping import get_sport_name
        return get_sport_name(self.sport_id)

    @computed_field
    @property
    def sport_category(self) -> str:
        """Get sport category (Cardio, Strength, etc.)."""
        from whoopdata.utils.sport_mapping import get_sport_category
        return get_sport_category(self.sport_id)

    class Config:
        from_attributes = True
