from dotenv import load_dotenv

import seaborn as sns 
import matplotlib.pyplot as plt
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


# ============================================================================================================
# TODO Still being worked on
# ============================================================================================================
#? Added data from google export
# read in google fit export data 
df_g = pd.read_csv("data/Daily activity metrics.csv")


df_g[['Date','Distance (m)', 'Average weight (kg)', 'Max weight (kg)','Tennis duration (ms)']]


df_g[['Date','Distance (m)', 'Average weight (kg)', 'Max weight (kg)','Tennis duration (ms)']]

df_g[['Tennis duration (mins)']] = df_g[['Tennis duration (ms)']]/(1000 * 60)

df_g.info()
import seaborn as sns 
df_g['Date'] = pd.to_datetime(df_g['Date'], errors='coerce')
df_g['year_month'] = df_g['Date'].dt.to_period('M').dt.to_timestamp()
df_final_fact_table['cycle_start_dt'] = pd.to_datetime(df_final_fact_table['cycle_start_ts']).dt.date
df_g['start_dt'] = pd.to_datetime(df_g['Date']).dt.date

# select and rename columns to match format 
df_gfit = df_g[['start_dt','Distance (m)', 'Max weight (kg)','Step count']]
df_gfit.columns = ['start_dt','total_distance_m','weight_kg','step_count']


# Combine Whoop and Google Fit Data 
df_combined = pd.merge(left=df_final_fact_table, right=df_gfit, left_on= 'cycle_start_dt', right_on= 'start_dt',how='inner')

# ==================================================================

# Convert 'cycle_start_ts' to datetime if it's not already
df_final_fact_table['cycle_start_ts'] = pd.to_datetime(df_final_fact_table['cycle_start_ts'])

# Extract the month and year from the 'cycle_start_ts'
df_final_fact_table['year_month'] = df_final_fact_table['cycle_start_ts'].dt.to_period('M')

# Calculate monthly average HRV and Resting Heart Rate
monthly_avg_hrv = df_final_fact_table.groupby('year_month')['hrv_rmssd_milli'].mean()
monthly_avg_rhr = df_final_fact_table.groupby('year_month')['resting_heart_rate'].mean()

# Plotting side by side
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot for HRV
axes[0].plot(monthly_avg_hrv.index.astype(str), monthly_avg_hrv, marker='o', linestyle='-', color='blue')
axes[0].set_title('Monthly Average HRV (RMSSD)')
axes[0].set_xlabel('Month')
axes[0].set_ylabel('HRV (RMSSD in milliseconds)')
axes[0].tick_params(axis='x', rotation=45)

# Plot for Resting Heart Rate
axes[1].plot(monthly_avg_rhr.index.astype(str), monthly_avg_rhr, marker='o', linestyle='-', color='green')
axes[1].set_title('Monthly Average Resting Heart Rate')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Resting Heart Rate (bpm)')
axes[1].tick_params(axis='x', rotation=45)

# Adjust layout for better spacing
plt.tight_layout()

# Show the plots
plt.show()
# =================================================================================
import pandas as pd
import matplotlib.pyplot as plt

# Assuming 'df_final_fact_table' is the final DataFrame

# Convert 'cycle_start_ts' to datetime if it's not already
df_final_fact_table['cycle_start_ts'] = pd.to_datetime(df_final_fact_table['cycle_start_ts'])

# Extract the month and year from the 'cycle_start_ts'
df_final_fact_table['year_month'] = df_final_fact_table['cycle_start_ts'].dt.to_period('M')

# Calculate monthly average Cycle Length and Time in Bed
monthly_avg_cycle_length = df_final_fact_table.groupby('year_month')['cycle_length_hours'].mean()
monthly_avg_time_in_bed = df_final_fact_table.groupby('year_month')['total_in_bed_time_hrs'].mean()

# Plotting side by side
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot for Cycle Length
axes[0].plot(monthly_avg_cycle_length.index.astype(str), monthly_avg_cycle_length, marker='o', linestyle='-', color='purple')
axes[0].set_title('Monthly Average Cycle Length')
axes[0].set_xlabel('Month')
axes[0].set_ylabel('Cycle Length (hours)')
axes[0].tick_params(axis='x', rotation=45)

# Plot for Time in Bed
axes[1].plot(monthly_avg_time_in_bed.index.astype(str), monthly_avg_time_in_bed, marker='o', linestyle='-', color='orange')
axes[1].set_title('Monthly Average Time in Bed')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Time in Bed (hours)')
axes[1].tick_params(axis='x', rotation=45)

# Adjust layout for better spacing
plt.tight_layout()

# Show the plots
plt.show()






# =================================================================================
df_final_fact_table['cycle_start_ts'] = pd.to_datetime(df_final_fact_table['cycle_start_ts'])

# Extract the month and year from the 'cycle_start_ts'
df_final_fact_table['year_month'] = df_final_fact_table['cycle_start_ts'].dt.to_period('M')

# Calculate monthly average Strain and Average Heart Rate
monthly_avg_strain = df_final_fact_table.groupby('year_month')['score_strain'].mean()
monthly_avg_avg_hr = df_final_fact_table.groupby('year_month')['score_avg_heart_rate'].mean()

# Plotting side by side
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot for Strain
axes[0].plot(monthly_avg_strain.index.astype(str), monthly_avg_strain, marker='o', linestyle='-', color='red')
axes[0].set_title('Monthly Average Strain Score')
axes[0].set_xlabel('Month')
axes[0].set_ylabel('Strain Score')
axes[0].tick_params(axis='x', rotation=45)

# Plot for Average Heart Rate
axes[1].plot(monthly_avg_avg_hr.index.astype(str), monthly_avg_avg_hr, marker='o', linestyle='-', color='blue')
axes[1].set_title('Monthly Average Heart Rate')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Average Heart Rate (bpm)')
axes[1].tick_params(axis='x', rotation=45)

# Adjust layout for better spacing
plt.tight_layout()

# Show the plots
plt.show()



import seaborn as sns
import matplotlib.pyplot as plt

# Filter the relevant columns from your dataframe
df = df_final_fact_table[['cycle_start_ts', 'total_in_bed_time_hrs', 'score_strain', 'recovery_score', 'hrv_rmssd_milli', 'cycle_length_hours', 'resting_heart_rate']].copy()

# Create a seaborn style plot with subplots for each metric
sns.set(style="whitegrid")
fig, axes = plt.subplots(6, 1, figsize=(15, 25), sharex=True)

# Define metrics and their corresponding labels
metrics = {
    'Total Sleep Time (hrs)': 'total_in_bed_time_hrs',
    'Strain Score': 'score_strain',
    'Recovery Score': 'recovery_score',
    'HRV RMSSD (ms)': 'hrv_rmssd_milli',
    'Cycle Length (hrs)': 'cycle_length_hours',
    'Resting Heart Rate (bpm)': 'resting_heart_rate'
}

# Define color palette
colors = sns.color_palette("husl", len(metrics))

# Plot each metric in a separate subplot
for i, (label, column) in enumerate(metrics.items()):
    sns.lineplot(ax=axes[i], x=df['cycle_start_ts'], y=df[column], color=colors[i], lw=2)
    axes[i].set_ylabel(label, fontsize=12)
    axes[i].grid(True)

# Final plot adjustments
plt.xlabel('Cycle Start Date', fontsize=14)
plt.tight_layout()

# Show the plot
plt.show()





# ===============================================================

# Monthly
# ===============================================================
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# Ensure 'cycle_start_ts' is in datetime format


# Extract the month and year from the 'cycle_start_ts'
df_combined['year_month'] = df_combined['cycle_start_ts'].dt.to_period('M')

# Select only the numeric columns for aggregation
numeric_cols = df_combined.select_dtypes(include=[float, int, float]).columns

# Group by 'year_month' and calculate the mean for each group
df_monthly_avg = df_combined.groupby('year_month')[numeric_cols].mean()

# Check if the monthly average DataFrame has data
print(df_monthly_avg.info())

# Create a seaborn style plot with subplots for each metric
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(7, 1, figsize=(15, 25), sharex=True)

# Define metrics and their corresponding labels for monthly averages
metrics = {
    'Avg Sleep': 'total_in_bed_time_hrs',
    'Avg Strain': 'score_strain',
    'Avg Recovery': 'recovery_score',
    'Avg HRV': 'hrv_rmssd_milli',
    'Avg Distance': 'total_distance_m',
    'Avg RHR': 'resting_heart_rate',
    'Weight Kg': 'weight_kg'
}

# Define color palette
colors = sns.color_palette("husl", len(metrics))

# Plot each metric in a separate subplot
for i, (label, column) in enumerate(metrics.items()):
    if column in df_monthly_avg.columns:
        sns.lineplot(ax=axes[i], x=df_monthly_avg.index.astype(str), y=df_monthly_avg[column], color=colors[i], lw=2)
        axes[i].set_ylabel(label, fontsize=12)
        axes[i].grid(True)
    else:
        print(f"Warning: Column '{column}' not found in the DataFrame!")

# Final plot adjustments
plt.xlabel('Month', fontsize=14)

# Add a title for the entire figure
fig.suptitle('Monthly Averages of Key Health Metrics', fontsize=16, y=1.02)

# Adjust the layout so that the title fits
plt.tight_layout()

# Show the plot
plt.show()



df_combined.info()

interesting_cols = ['score_strain',
       'score_avg_heart_rate', 'score_max_heart_rate', 'cycle_length_hours', 'recovery_score', 'resting_heart_rate',
       'hrv_rmssd_milli', 'spo2_percentage', 'skin_temp_celsius',
       'total_strain', 'num_workouts', 'total_in_bed_time_hrs',
       'avg_sleep_performance', 'total_light_sleep_time_hrs',
       'avg_respiratory_rate', 'total_distance_m', 'weight_kg', 'step_count']
df_corr = df_combined[interesting_cols].corr()


sns.heatmap(df_corr, annot=True, linecolor='white',linewidths=0.5,cmap='viridis')
plt.show()


stg_recovery = stg_recovery[stg_recovery['user_calibrating'] == False]

stg_recovery['created_dt'] = stg_recovery['created_ts'].dt.date

stg_recovery.info()


stg_recovery['created_month'] = pd.to_datetime(stg_recovery['created_dt']).dt.to_period('M')

import numpy as np

stg_recovery.groupby(['created_month'])['resting_heart_rate'].agg('mean',np.median,np.size)




# ==============================================================================
# Workout Analysis
# ==============================================================================


stg_workouts['workout_start_week'] = pd.to_datetime(stg_workouts['workout_start_ts']).dt.to_period('W')

stg_tennis = stg_workouts[stg_workouts['workout_sport_name'] == 'Tennis'] 
stg_tennis.info()
stg_tennis.groupby(['workout_start_week'])['score_zone_duration_zone_two_mins'].agg('mean',np.size).plot()
plt.show()

stg_workouts.groupby(['workout_sport_name'])[['score_average_heart_rate','score_max_heart_rate']].agg(['mean','std','median',np.size]).round()


sns.histplot(x = 'score_average_heart_rate', data =stg_tennis)
plt.show()

sns.histplot(x = 'score_max_heart_rate', data =stg_tennis)
plt.show()



# Tennis heart rate overtime
sns.lineplot(x= 'created_dt', y = 'score_avg_heart_rate', data = stg_tennis)

stg_cycles.info()


# ==============================================================================
# Recovery Analysis
# ==============================================================================

stg_sleep.info()
sns.lineplot(x = 'created_dt', y = 'hrv_rmssd_milli', data = stg_recovery)
plt.show()

sns.heatmap(stg_recovery[['hrv_rmssd_milli','skin_temp_celsius','spo2_percentage']].corr())
plt.show()
# Analysis
import scipy.stats as stats

x = stg_recovery['hrv_rmssd_milli']
y = stg_recovery['skin_temp_celsius']
y = stg_recovery['recovery_score']

corr_coef, p_value = stats.pearsonr(x,y)
print(f'Correlation Coeff: {corr_coef:.2f}\n p_value : {p_value:.4f}')
# Linear Regression Model
from scipy.stats import linregress
import matplotlib.pyplot as plt
import numpy as np
x_arary = np.array(x)
y_arary = np.array(y)

lm_model = linregress(x,y)

print(f"Sxlope: {lm_model.slope}")
print(f"Intercept: {lm_model.intercept}")
print(f"R-squared: {lm_model.rvalue**2}")
print(f"P-value: {lm_model.pvalue}")
print(f"Standard error: {lm_model.stderr}")
plt.scatter(x, y, color='blue', label='Data points')  # plot data points
plt.plot(x, lm_model.intercept + lm_model.slope * x, color='red', label='Fit line')  # plot line of fit
plt.xlabel('HRV RMSSD Milli ')
plt.ylabel('Recovery Score ')
plt.title('Linear Regression Analysis')
plt.legend()
plt.show()

stg_recovery.info()
# Machine learning approach 

# Assuming daily granularity

from sklearn.svm import SVR
from sklearn.model_selection import GridSearchCV, cross_val_score,r2_score
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split


# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(np.array(X_train).reshape(-1, 1))
X_test_scaled = scaler.transform(np.array(X_test).reshape(-1, 1))

# Define SVR model with linear kernel
svr = SVR(kernel='linear')

# Define hyperparameter grid for GridSearchCV
param_grid = {'C': [0.1, 1, 10], 'epsilon': [0.1, 1, 10]}

# Perform GridSearchCV to find optimal hyperparameters
grid_search = GridSearchCV(svr, param_grid, cv=5)
grid_search.fit(X_train_scaled, y_train)

# Print best hyperparameters and cross-validation scores
print("Best parameters:", grid_search.best_params_)
print("Cross-validation scores:", cross_val_score(grid_search.best_estimator_, X_train_scaled, y_train, cv=5))

# Train the model with the best hyperparameters
best_svr = grid_search.best_estimator_
best_svr.fit(X_train_scaled, y_train)

# Evaluate the model on the test set
y_pred = best_svr.predict(X_test_scaled)

# Calculate and print evaluation metrics
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print("Mean Squared Error:", mse)
print("Root Mean Squared Error:", rmse)
print("R-squared:", r2)

# Visualize predicted vs. actual recovery scores
plt.bar(y_test, y_pred)
plt.xlabel("Actual Recovery Score")
plt.ylabel("Predicted Recovery Score")
plt.show()

import matplotlib.pyplot as plt
import seaborn as sns

# Calculate absolute error
error = abs(y_test - y_pred)

# Create scatter plot with color-coded error
plt.scatter(y_test, y_pred, c=error, cmap='viridis')
plt.xlabel("Actual Recovery Score")
plt.ylabel("Predicted Recovery Score")
plt.colorbar(label="Absolute Error")
plt.title("Actual vs. Predicted Recovery Scores with Color-Coded Error")
plt.show()



# How does cycle length change with recovery score or HRV
stg_daily_performance = pd.merge(stg_cycles,stg_recovery, on='cycle_id', how='inner')
stg_daily_performance.info()
key_metrics = stg_daily_performance[['cycle_length_hours','spo2_percentage','skin_temp_celsius','score_avg_heart_rate','score_max_heart_rate','recovery_score','hrv_rmssd_milli']]
key_metrics.dropna(inplace=True)


stg_sleep.info()

sns.heatmap(key_metrics.corr(),cmap = 'viridis')
plt.show()

# A cycle end is the the same as when a sleep starts.
cycle.iloc[1]["end"] == sleep.head(2)["start"][0]


# Recovery doesn't have a time, but it it has cycle_id
recovery.head(3)["created_at"]


sleep.head(2)["end"]
recovery.info()

stg_workouts.info()
sleep.info()
cycle.info()

# Slim down to the most needed columns
# Format dates, times and needed deltas into useful columns
# create a centralised fact table based on cycle, fct_cycles_extended, allocate stg_workouts based on cycle start dates
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
stg_sleep = transform_sleep(sleep)

stg_sleep.info()

stg_workouts.info()
stg_workouts = transform_workouts(workout)

weights.info()

weights = stg_workouts[stg_workouts["workout_sport_name"] == "Weightlifting"]


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


stg_cycles = transform_cycles(cycle)

stg_cycles.info()


# Convert to date
stg_cycles["cycle_day"] = pd.to_datetime(
    stg_cycles["cycle_end_ts"]
).dt.date

import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (15, 5)
sns.lineplot(x="cycle_day", y="score_strain", data=stg_cycles)
plt.show()

sns.lineplot(x="cycle_day", y="score_kilojoule", data=stg_cycles)
plt.show()

sns.lineplot(x="cycle_day", y="cycle_length_hours", data=stg_cycles)
plt.show()

corr_matrix = stg_cycles[
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
stg_cycles["rolling_mean"] = (
    stg_cycles["cycle_length_hours"].rolling(window=7).mean()
)

# Plot the original data and the rolling mean
plt.figure(figsize=(10, 8))  # Set the figure size
sns.lineplot(
    x="cycle_day", y="cycle_length_hours", data=stg_cycles, label="Cycle Length"
)
sns.lineplot(
    x="cycle_day", y="rolling_mean", data=stg_cycles, label="7-Day Rolling Mean"
)

ax2 = plt.twinx()
sns.lineplot(
    x="cycle_day",
    y="score_strain",
    data=stg_cycles,
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
X_Y_Spline = make_interp_spline(x = stg_cycles['cycle_day'], y = stg_cycles['score_strain'] )
 
# Returns evenly spaced numbers
# over a specified interval.
X_ = np.linspace(stg_cycles['cycle_day'].min(), stg_cycles['cycle_day'].max(), 500)
Y_ = X_Y_Spline(X_)
 
# Plotting the Graph
plt.plot(X_, Y_)
plt.title("Plot Smooth Curve Using the scipy.interpolate.make_interp_spline() Class")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()
sns.lineplot(x="cycle_day", y="score_strain", data=stg_cycles)
plt.show()



stg_sleep.info()
stg_workouts.info()
stg_cycles.info()

recovery




stg_recovery = transform_recovery(recovery)

stg_recovery.info()

stg_recovery['created_dt'] = pd.to_datetime(stg_recovery['created_ts']).dt.date


# Calculate rolling mean
stg_recovery["rolling_mean"] = stg_recovery["recovery_score"].rolling(window=7).mean()
import matplotlib.pyplot as plt
import seaborn as sns



import matplotlib.pyplot as plt
import seaborn as sns

# Calculate rolling mean
stg_recovery["rolling_mean"] = stg_recovery["recovery_score"].rolling(window=7).mean()

# Plot the original data and the rolling mean
plt.figure(figsize=(10, 8))  # Set the figure size

# Define the colors for shading based on recovery score ranges
colors = ['red', 'yellow', 'lime']
ranges = [(0, 34), (34, 67), (67, 100)]

# Plot shaded areas for each recovery score range
for i, (start, end) in enumerate(ranges):
    plt.fill_between(stg_recovery["created_dt"],
                     stg_recovery["recovery_score"],
                     where=((stg_recovery["recovery_score"] >= start) & 
                            (stg_recovery["recovery_score"] < end)),
                     color=colors[i], alpha=0.3, label=f'{start}-{end}%')

# Plot the original data and rolling mean lines
sns.lineplot(
    x="created_dt", y="recovery_score", data=stg_recovery, label="Recovery Score", color='blue', alpha=0.5
)
sns.lineplot(
    x="created_dt", y="rolling_mean", data=stg_recovery, label="7-Day Rolling Mean", color='orange', alpha=0.5
)

# Create a twin y-axis for recovery score
ax2 = plt.twinx()
sns.lineplot(
    x="created_dt",
    y="recovery_score",
    data=stg_recovery,
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


