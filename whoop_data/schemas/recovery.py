from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Recovery(BaseModel):
    user_id: str 
    created_at: datetime
    recovery_score: float
    resting_heart_rate: Optional[float]
    spo2_percentage: float
    spo2_percentage: float 

    class Config:
        from_attributes = True  # instead of orm_mode in Pydantic v2


class AvgRecovery(BaseModel):
    week:str 
    avg_recovery_score: float
    avg_resting_heart_rate: float
    
    class Config:
        from_attributes = True

