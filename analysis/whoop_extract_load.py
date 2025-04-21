from sqlalchemy import create_engine, text
from whoop_client import Whoop
import pandas as pd





from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SleepRecord(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: datetime
    timezone_offset: Optional[int]
    nap: Optional[bool]
    score_state: Optional[str]

    # Stage summary (milliseconds)
    total_in_bed_time_milli: Optional[int] = Field(alias="score.stage_summary.total_in_bed_time_milli")
    total_awake_time_milli: Optional[int] = Field(alias="score.stage_summary.total_awake_time_milli")
    total_no_data_time_milli: Optional[int] = Field(alias="score.stage_summary.total_no_data_time_milli")
    total_light_sleep_time_milli: Optional[int] = Field(alias="score.stage_summary.total_light_sleep_time_milli")
    total_slow_wave_sleep_time_milli: Optional[int] = Field(alias="score.stage_summary.total_slow_wave_sleep_time_milli")
    total_rem_sleep_time_milli: Optional[int] = Field(alias="score.stage_summary.total_rem_sleep_time_milli")
    sleep_cycle_count: Optional[int] = Field(alias="score.stage_summary.sleep_cycle_count")
    disturbance_count: Optional[int] = Field(alias="score.stage_summary.disturbance_count")

    # Sleep needed (milliseconds)
    baseline_milli: Optional[int] = Field(alias="score.sleep_needed.baseline_milli")
    need_from_sleep_debt_milli: Optional[int] = Field(alias="score.sleep_needed.need_from_sleep_debt_milli")
    need_from_recent_strain_milli: Optional[int] = Field(alias="score.sleep_needed.need_from_recent_strain_milli")
    need_from_recent_nap_milli: Optional[int] = Field(alias="score.sleep_needed.need_from_recent_nap_milli")

    # Respiratory & performance
    respiratory_rate: Optional[float] = Field(alias="score.respiratory_rate")
    sleep_performance_percentage: Optional[float] = Field(alias="score.sleep_performance_percentage")
    sleep_consistency_percentage: Optional[float] = Field(alias="score.sleep_consistency_percentage")
    sleep_efficiency_percentage: Optional[float] = Field(alias="score.sleep_efficiency_percentage")



whoop = Whoop()

whoop.authenticate()

recovery_url = whoop.get_endpoint_url("recovery")
sleep_url = whoop.get_endpoint_url("sleep")


stg_recovery = whoop.make_paginated_request(recovery_url)
stg_sleep = whoop.make_paginated_request(
    "https://api.prod.whoop.com/developer/v1/activity/sleep/"
)


stg_sleep.info()

DATABASE_NAME = 'whoop_data'


class DataModeling:
    def __init__(
            self,
            database:str='whoop_data',
            database_host:str="postgresql://localhost/"
            ):
        self.database = database
        self.database_host = database_host

    def connect_db(self):
        print(f'connected {self.database_host+self.database}')
        self.engine = create_engine(self.database_host+self.database)

    def test_db(self):
        res = pd.read_sql("SELECT * FROM src_sleep LIMIT 10", con=self.engine)
        return res




model = DataModeling()

model.connect_db()

model.test_db()



engine = create_engine("postgresql://localhost/whoop_data")

stg_sleep.to_sql("src_sleep", engine, if_exists="append", index=False)


res = pd.read_sql("SELECT * FROM src_sleep LIMIT 10", con=engine)


res.columns

create_table_sql = """
CREATE TABLE stg_sleep(
    id SERIAL PRIMARY KEY, 
    user_id,
    created_at,
    updated_at,
    start,
    end,
    timezone_offset,
    nap,
    score_state,
    total_in_bed_time_milli,
    total_awake_time_milli,
    total_no_data_time_milli,
    total_light_sleep_time_milli,
    total_slow_wave_sleep_time_milli,
    total_rem_sleep_time_milli,
    sleep_cycle_count,
    disturbance_count,
    baseline_milli,
    need_from_sleep_debt_milli,
    need_from_recent_strain_milli,
    need_from_recent_nap_milli,
    respiratory_rate,
    sleep_performance_percentage,
    sleep_consistency_percentage,
    sleep_efficiency_percentag,
);

"""
with engine.connect() as conn:
    conn.execute(text(create_table_sql))

