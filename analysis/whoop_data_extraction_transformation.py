from dotenv import load_dotenv

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from whoop_functions import (
    whoop_authentication,
    make_paginated_request,
    transform_sleep,
    replace_periods,
    transform_workouts,
    transform_cycles,
    transform_recovery
)

# Load variables
load_dotenv()
# Load credential for authentication
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
# Access token
access_token = whoop_authentication(username=username, password=password)
headers = {"Authorization": f"Bearer {access_token}"}
# API Endpoints
url_sleep = f"https://api.prod.whoop.com/developer/v1/activity/sleep/"
url_recovery = f"https://api.prod.whoop.com/developer/v1/recovery/"
url_cycle = f"https://api.prod.whoop.com/developer/v1/cycle/"
url_workout = f"https://api.prod.whoop.com/developer/v1/activity/workout/"

# Get Request for Cycle data
cycle = make_paginated_request(url=url_cycle, headers=headers)

# Get Request for sleep data
sleep = make_paginated_request(url=url_sleep, headers=headers)


# Get Request for recovery data
recovery = make_paginated_request(url=url_recovery, headers=headers)

# Get Request for workout data
workout = make_paginated_request(url=url_workout, headers=headers)

# Workout look up table
# whoop work out sports id
dim_workout_sports_id_look_up = {
    -1: "Activity",
    0: "Running",
    1: "Cycling",
    16: "Baseball",
    17: "Basketball",
    18: "Rowing",
    19: "Fencing",
    20: "Field Hockey",
    21: "Football",
    22: "Golf",
    24: "Ice Hockey",
    25: "Lacrosse",
    27: "Rugby",
    28: "Sailing",
    29: "Skiing",
    30: "Soccer",
    31: "Softball",
    32: "Squash",
    33: "Swimming",
    34: "Tennis",
    35: "Track & Field",
    36: "Volleyball",
    37: "Water Polo",
    38: "Wrestling",
    39: "Boxing",
    42: "Dance",
    43: "Pilates",
    44: "Yoga",
    45: "Weightlifting",
    47: "Cross Country Skiing",
    48: "Functional Fitness",
    49: "Duathlon",
    51: "Gymnastics",
    52: "Hiking/Rucking",
    53: "Horseback Riding",
    55: "Kayaking",
    56: "Martial Arts",
    57: "Mountain Biking",
    59: "Powerlifting",
    60: "Rock Climbing",
    61: "Paddleboarding",
    62: "Triathlon",
    63: "Walking",
    64: "Surfing",
    65: "Elliptical",
    66: "Stairmaster",
    70: "Meditation",
    71: "Other",
    73: "Diving",
    74: "Operations - Tactical",
    75: "Operations - Medical",
    76: "Operations - Flying",
    77: "Operations - Water",
    82: "Ultimate",
    83: "Climber",
    84: "Jumping Rope",
    85: "Australian Football",
    86: "Skateboarding",
    87: "Coaching",
    88: "Ice Bath",
    89: "Commuting",
    90: "Gaming",
    91: "Snowboarding",
    92: "Motocross",
    93: "Caddying",
    94: "Obstacle Course Racing",
    95: "Motor Racing",
    96: "HIIT",
    97: "Spin",
    98: "Jiu Jitsu",
    99: "Manual Labor",
    100: "Cricket",
    101: "Pickleball",
    102: "Inline Skating",
    103: "Box Fitness",
    104: "Spikeball",
    105: "Wheelchair Pushing",
    106: "Paddle Tennis",
    107: "Barre",
    108: "Stage Performance",
    109: "High Stress Work",
    110: "Parkour",
    111: "Gaelic Football",
    112: "Hurling/Camogie",
    113: "Circus Arts",
    121: "Massage Therapy",
    125: "Watching Sports",
    126: "Assault Bike",
    127: "Kickboxing",
    128: "Stretching",
    230: "Table Tennis",
    231: "Badminton",
    232: "Netball",
    233: "Sauna",
    234: "Disc Golf",
    235: "Yard Work",
    236: "Air Compression",
    237: "Percussive Massage",
    238: "Paintball",
    239: "Ice Skating",
    240: "Handball",
}

# Map sports id to name of sport
workout["sport_name"] = workout["sport_id"].map(dim_workout_sports_id_look_up)

recovery.info()

recovery[['created_at','score.recovery_score','score.resting_heart_rate']]


# ==============================================================================
# Transform dataframes
# ==============================================================================
stg_sleep = transform_sleep(sleep)
stg_workouts = transform_workouts(workout)
stg_cycles = transform_cycles(cycle)
stg_recovery = transform_recovery(recovery)
stg_recovery = stg_recovery[stg_recovery['user_calibrating'] == False]

stg_cycles.info()
stg_recovery.info()
stg_workouts.info()
stg_sleep.info()


# Model

# Ensure necessary datetime conversions for stg_workouts and stg_sleep
stg_workouts['workout_start_ts'] = pd.to_datetime(stg_workouts['workout_start_ts'])
stg_workouts['workout_end_ts'] = pd.to_datetime(stg_workouts['workout_end_ts'])
stg_sleep['sleep_start_ts'] = pd.to_datetime(stg_sleep['sleep_start_ts'])
stg_sleep['sleep_end_ts'] = pd.to_datetime(stg_sleep['sleep_end_ts'])

# Step 1: Check for missing values in 'score_strain'
missing_strain = stg_workouts['score_strain'].isnull().sum()
print(f"Missing values in 'score_strain': {missing_strain}")

# Step 2: Handle missing values (if any) in 'score_strain'
# Option 1: Fill missing values with 0
stg_workouts['score_strain'].fillna(0, inplace=True)

# Option 2: Drop rows with missing 'score_strain' (optional)
# stg_workouts = stg_workouts.dropna(subset=['score_strain'])

# Step 3: Filter stg_workouts to include only records that fall within the cycle's start and end times
df_workouts_filtered = pd.merge(stg_cycles, stg_workouts, how='left', on='user_id')


# Debugging: Check the merge result before filtering
print("Merged DataFrame (before filtering):")
print(df_workouts_filtered.head())

# Apply the filtering condition
df_workouts_filtered = df_workouts_filtered.query(
    'workout_start_ts >= cycle_start_ts and workout_end_ts <= cycle_end_ts'
)

# Debugging: Check the filtered DataFrame to ensure `score_strain` is still present
print("Filtered DataFrame (after time-based filtering):")
print(df_workouts_filtered[['cycle_id', 'score_strain_y', 'workout_id']].head())
# Step 4: Aggregate the workout data by cycle_id
df_workouts_aggregated = df_workouts_filtered.groupby('cycle_id').agg({
    'score_strain_y': 'sum',        # Sum of strain scores for the cycle
    'workout_id': 'count'         # Count of workouts in the cycle
}).reset_index().rename(columns={
    'score_strain_y': 'total_strain', 
    'workout_id': 'num_workouts'
})

# Step 5: Merge the aggregated workout data back to the cycles + recovery DataFrame
df_cycles_recovery = pd.merge(stg_cycles, stg_recovery, on='cycle_id', how='left')
df_cycles_recovery_workouts = pd.merge(df_cycles_recovery, df_workouts_aggregated, on='cycle_id', how='left')

# Step 6: Filter stg_sleep to include only records that fall within the cycle's start and end times
df_sleep_filtered = pd.merge(stg_cycles, stg_sleep, how='left', on='user_id').query(
    'sleep_start_ts >= cycle_start_ts and sleep_end_ts <= cycle_end_ts'
)

# Step 7: Aggregate the sleep data by cycle_id
df_sleep_aggregated = df_sleep_filtered.groupby('cycle_id').agg({
    'score_stage_summary_total_in_bed_time_hrs': 'sum',           # Total time in bed
    'score_sleep_performance_percentage': 'mean',                 # Average sleep performance
    'score_stage_summary_total_light_sleep_time_hrs': 'sum',      # Total light sleep time
    'score_stage_summary_total_rem_sleep_time_hrs': 'sum',        # Total REM sleep time
    'score_stage_summary_total_slow_wave_sleep_time_hrs': 'sum',  # Total slow wave sleep time
    'score_respiratory_rate': 'mean'                              # Average respiratory rate
}).reset_index().rename(columns={
    'score_stage_summary_total_in_bed_time_hrs': 'total_in_bed_time_hrs',
    'score_sleep_performance_percentage': 'avg_sleep_performance',
    'score_stage_summary_total_light_sleep_time_hrs': 'total_light_sleep_time_hrs',
    'score_stage_summary_total_rem_sleep_time_hrs': 'total_rem_sleep_time_hrs',
    'score_stage_summary_total_slow_wave_sleep_time_hrs': 'total_slow_wave_sleep_time_hrs',
    'score_respiratory_rate': 'avg_respiratory_rate'
})

# Step 8: Merge the aggregated sleep data back to the cycles + recovery + workouts DataFrame
df_final_fact_table = pd.merge(df_cycles_recovery_workouts, df_sleep_aggregated, on='cycle_id', how='left')

# Step 9: Final check of the merged DataFrame
print("Final fact table with cycles, recovery, workouts, and sleep data:")
print(df_final_fact_table.info())

df_final_fact_table.info()


df_final_fact_table.to_csv("data/whoop.csv")

