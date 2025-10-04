from sqlalchemy.orm import sessionmaker
from analysis.whoop_client import Whoop
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
from db.database import SessionLocal, engine


# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath("."))  # Adds current working directory to path

# DB setup
db = SessionLocal()

# Database loading
loader = DBLoader(db)

# Whoop Client


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
    
    # Get data as DataFrame (already transformed for database compatibility)
    df = whoop.make_paginated_request(
        whoop.get_endpoint_url(endpoint_name=whoop_endpoint),
        transform_for_db=True  # This ensures field mapping is applied
    )
    
    print(f"📊 Processing {len(df)} {whoop_endpoint} records...")
    
    # Convert DataFrame to records and process each one
    for index, row in df.iterrows():
        # Convert pandas Series to dict
        item_dict = row.to_dict()
        
        # Apply transformer (which now expects already-flattened fields)
        data = transformer(item_dict)
        
        # Load into database
        loader_fn(data)


print('Starting Recovery')
print("=" * 120)
model_etl_run(whoop_endpoint="recovery",
              transformer=transform_recovery,
              loader_fn=loader.load_recovery
              )

recoveries = db.query(Recovery).order_by(Recovery.created_at).limit(10).all()

for r in recoveries:
    print(f"User: {r.user_id}, Score: {r.recovery_score}, Date: {r.created_at}, RHR: {r.resting_heart_rate},RHR: {r.recovery_category()}")

print("Starting Workout")
print("=" * 120)
model_etl_run(
    whoop_endpoint="workout",
    transformer=transform_workout,
    loader_fn=loader.load_workout,
)



print("Starting Sleep")
print("=" * 120)
model_etl_run(
    whoop_endpoint="sleep",
    transformer=transform_sleep,
    loader_fn=loader.load_sleep,
)
