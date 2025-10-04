from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.whoop_api import Whoop
from models.models import Recovery, Cycle, Workout, Sleep
from datetime import datetime
from utils.load_into_database import DBLoader
from utils.model_transformation import (
    transform_sleep,
    transform_recovery,
    transform_workout,
)
import sys
import os
from rich import print_json

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath("."))  # Adds current working directory to path

# DB setup
engine = create_engine("sqlite:///db/whoop.db")
Session = sessionmaker(bind=engine)
db = Session()

# Database loading
loader = DBLoader(db)

# Whoop Client


def recovery_etl():
    """
    Extract Transform & Load Whoop Recovery Data

    Args
        None
    """
    whoop = Whoop()
    whoop.authenticate()
    records = whoop.make_paginated_request(whoop.get_endpoint_url("recovery"))
    print_json(data=records[1])
    for item in records:
        data = transform_recovery(item)
        loader.load_recovery(data)

    print("✅ Recovery data loaded into DB")


def model_etl_run(whoop_endpoint, transformer, loader_fn):
    """
    Generic Extract-Transform-Load function for WHOOP API data.

    Args:
        whoop_endpoint (str): WHOOP API data type to pull. Must be one of:
            - "recovery"
            - "sleep"
            - "workout"
            - "strain" (optional)
        transformer (callable): Function to transform raw WHOOP records into DB-ready format.
        loader_fn (callable): Function that inserts a transformed record into the database.

    Returns:
        None
    """
    whoop = Whoop()
    whoop.authenticate()
    records = whoop.make_paginated_request(
        whoop.get_endpoint_url(endpoint_name=whoop_endpoint)
    )
    for item in records:
        data = transformer(item)
        loader_fn(data)


model_etl_run(
    whoop_endpoint="recovery",
    transformer=transform_recovery,
    loader_fn=loader.load_recovery,
)

from sqlalchemy import desc


recoveries = db.query(Recovery).order_by(desc(Recovery.created_at)).limit(10).all()

for r in recoveries:
    print(
        f"User: {r.user_id}, Score: {r.recovery_score}, Date: {r.created_at}, RHR: {r.resting_heart_rate},RHR: {r.recovery_category()}"
    )


print(type(Recovery))

print(dir(Recovery))


#  =========================
# Sleep
#  =========================
sleep_records = whoop.make_paginated_request(whoop.get_endpoint_url("sleep"))

print(json.dumps(sleep_records[0], indent=3))
from pprint import pprint

print_json(data=sleep_records[0].get("score"))


for sleep in sleep_records:
    data = transform_sleep(sleep)
    loader.load_sleep(data)

sleeps = db.query(Sleep).limit(5).all

import json

print(json.dumps(sleep_records[0], indent=2))


sleep_records = whoop.make_paginated_request(whoop.get_endpoint_url("sleep"))


# =================================================================


whoop = Whoop()
whoop.authenticate()

workout_records = whoop.make_paginated_request(whoop.get_endpoint_url("workout"))

print(len(workout_records))

all_workouts = []
for workout in workout_records:
    data = transform_workout(workout)
    all_workouts.append(data)
    loader.load_workout(data)

run = all_workouts[35]
pprint(run)


record = workout_records[25]


print(json.dumps(record, indent=3))

print_json(data=record)
print(json.dumps(record.get("score"), indent=3))


print(json.dumps(record.get("zone_duration"), indent=3))
print(json.dumps(record, indent=3))


print(json.dumps(record.get("score"), indent=3))


score = record.get("score")

zone = score.get("zone_duration")
zone.get("zone_one_milli") / 60e3
