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


# A cycle end is the the same as when a sleep starts.
cycle.iloc[1]["end"] == sleep.head(2)["start"][0]

# Recovery doesn't have a time, but it it has cycle_id
recovery.head(3)["created_at"]


sleep.head(2)["end"]
recovery.info()

workout.info()
sleep.info()
cycle.info()

# Slim down to the most needed columns
# Format dates, times and needed deltas into useful columns
# create a centralised fact table based on cycle, fct_cycles_extended, allocate workout based on cycle start dates
sleep["end"] = pd.to_datetime(sleep["end"])
sleep["start"] = pd.to_datetime(sleep["start"])

sleep["sleep_time"] = sleep["end"] - sleep["start"]

# Convert time delta to seconds
sleep["sleep_hrs"] = np.round(sleep["sleep_time"].dt.total_seconds() / 3600, 2)

# Not sure if I need this
sleep["sleep_end_dt"] = sleep["end"].dt.to_period("D")

sleep.sort_values(by="sleep_end_dt", ascending=True, inplace=True)
sleep[
    [
        "score.sleep_needed.baseline_milli",
        "score.sleep_needed.need_from_sleep_debt_milli",
        "score.sleep_needed.need_from_recent_strain_milli",
    ]
]


# Convert milli seconds to hours
sleep_trans = transform_sleep(sleep)

sleep_trans.info()

workout.info()
workout = transform_workouts(workout)

weights.info()

weights = workout[workout["workout_sport_name"] == "Weightlifting"]


weights["start_hr"] = pd.to_datetime(weights["workout_start_ts"]).dt.strftime("%H")

import seaborn as sns
import matplotlib.pyplot as plt

#  count and plot weights['start_hr'] to show distribution of when weights are done
sns.countplot(x="start_hr", data=weights)
plt.show()

weights["start_hr"] = weights["start_hr"].astype(int)

weights.columns
weights["start_name"] = weights["start_hr"] + 1
# for each value is weights['start_name']  add 'before_' to reach row
weights["start_name_formatted"] = "before_" + weights["start_name"].astype(str)

sns.countplot(x="start_name_formatted", data=weights)
plt.show()


# for weights, create a plot weight 'start_name_formatted' on x axis and score_kilojoule as as y1 and score_strain as y2 on a combined plot
sns.lineplot(x="start_name_formatted", y="score_kilojoule", data=weights)
sns.lineplot(x="start_name_formatted", y="score_strain", data=weights)
plt.show()

# create a plot weight 'start_name_formatted' on x axis and score_kilojoule as as y1 and score_strain as y2


# fct_cycle transformations
cycle.info()


cyles_transformed = transform_cycles(cycle)

cyles_transformed.info()


# Convert to date
cyles_transformed["cycle_day"] = pd.to_datetime(
    cyles_transformed["cycle_end_ts"]
).dt.date

import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (15, 5)
sns.lineplot(x="cycle_day", y="score_strain", data=cyles_transformed)
plt.show()

sns.lineplot(x="cycle_day", y="score_kilojoule", data=cyles_transformed)
plt.show()

sns.lineplot(x="cycle_day", y="cycle_length_hours", data=cyles_transformed)
plt.show()

corr_matrix = cyles_transformed[
    ["score_strain", "score_kilojoule", "cycle_length_hours","score_avg_heart_rate"]
].corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))

sns.heatmap(corr_matrix,
            annot=True, 
            cmap="plasma",
            mask= mask,
            fmt=".2f",
            linewidths=0.5,
            linecolor='white')
plt.show()


# 7 Day Moving Average of Cycle Length
# Compute the 7-day rolling mean of 'cycle_length_hours'
cyles_transformed["rolling_mean"] = (
    cyles_transformed["cycle_length_hours"].rolling(window=7).mean()
)

# Plot the original data and the rolling mean
plt.figure(figsize=(10, 8))  # Set the figure size
sns.lineplot(
    x="cycle_day", y="cycle_length_hours", data=cyles_transformed, label="Cycle Length"
)
sns.lineplot(
    x="cycle_day", y="rolling_mean", data=cyles_transformed, label="7-Day Rolling Mean"
)

ax2 = plt.twinx()
sns.lineplot(
    x="cycle_day",
    y="score_strain",
    data=cyles_transformed,
    label="Strain",
    ax=ax2,
    color="r",
)

plt.xlabel("Cycle Day")  # Set the x-axis label
plt.ylabel("Cycle Length (Hours)")  # Set the y-axis label
ax2.set_ylabel("Cycle Strain Score")
plt.title("Cycle Length with 7-Day Rolling Mean")  # Set the title
plt.show()  # Show the plot


#  How to plot with smooth lines 

from scipy.interpolate import make_interp_spline
X_Y_Spline = make_interp_spline(x = cyles_transformed['cycle_day'], y = cyles_transformed['score_strain'] )
 
# Returns evenly spaced numbers
# over a specified interval.
X_ = np.linspace(cyles_transformed['cycle_day'].min(), cyles_transformed['cycle_day'].max(), 500)
Y_ = X_Y_Spline(X_)
 
# Plotting the Graph
plt.plot(X_, Y_)
plt.title("Plot Smooth Curve Using the scipy.interpolate.make_interp_spline() Class")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()
sns.lineplot(x="cycle_day", y="score_strain", data=cyles_transformed)
plt.show()



sleep_trans.info()
workout.info()
cyles_transformed.info()

recovery




transformed_recovery = transform_recovery(recovery)

transformed_recovery.info()

transformed_recovery['created_dt'] = pd.to_datetime(transformed_recovery['created_ts']).dt.date


# Calculate rolling mean
transformed_recovery["rolling_mean"] = transformed_recovery["recovery_score"].rolling(window=7).mean()
import matplotlib.pyplot as plt
import seaborn as sns



import matplotlib.pyplot as plt
import seaborn as sns

# Calculate rolling mean
transformed_recovery["rolling_mean"] = transformed_recovery["recovery_score"].rolling(window=7).mean()

# Plot the original data and the rolling mean
plt.figure(figsize=(10, 8))  # Set the figure size

# Define the colors for shading based on recovery score ranges
colors = ['red', 'yellow', 'lime']
ranges = [(0, 34), (34, 67), (67, 100)]

# Plot shaded areas for each recovery score range
for i, (start, end) in enumerate(ranges):
    plt.fill_between(transformed_recovery["created_dt"],
                     transformed_recovery["recovery_score"],
                     where=((transformed_recovery["recovery_score"] >= start) & 
                            (transformed_recovery["recovery_score"] < end)),
                     color=colors[i], alpha=0.3, label=f'{start}-{end}%')

# Plot the original data and rolling mean lines
sns.lineplot(
    x="created_dt", y="recovery_score", data=transformed_recovery, label="Recovery Score", color='blue', alpha=0.5
)
sns.lineplot(
    x="created_dt", y="rolling_mean", data=transformed_recovery, label="7-Day Rolling Mean", color='orange', alpha=0.5
)

# Create a twin y-axis for recovery score
ax2 = plt.twinx()
sns.lineplot(
    x="created_dt",
    y="recovery_score",
    data=transformed_recovery,
    label="Recovery Score",
    ax=ax2,
    color="r", alpha=0.8
)

plt.xlabel("Cycle Day")  # Set the x-axis label
plt.ylabel("Recovery Score")  # Set the y-axis label
ax2.set_ylabel("Cycle Strain Score")
plt.title("Recovery Score with 7-Day Rolling Mean")  # Set the title
plt.legend()  # Show the legend
plt.show()  # Show the plot
