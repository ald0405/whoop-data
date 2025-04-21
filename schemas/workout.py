from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Workouts(BaseModel):
    user_id: Optional[str]
    created_at: datetime 
    start: datetime
    end: datetime
    sport_id : int
    strain: Optional[float]
    average_heart_rate: Optional[float ]
    max_heart_rate: Optional[float ]
    zone_zero_minutes: Optional[float]
    zone_one_minutes: Optional[float]
    zone_two_minutes: Optional[float]
    zone_three_minutes: Optional[float]
    zone_four_minutes: Optional[float]
    zone_five_minutes: Optional[float]
    class Config:
        from_attributes = True 


