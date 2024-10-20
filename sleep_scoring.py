from dotenv import load_dotenv

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score,root_mean_squared_error

# For handling missing values
from sklearn.impute import SimpleImputer
import seaborn as sns 
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
from whoop_functions import (
    whoop_authentication,
    make_paginated_request,
    transform_sleep,
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



# Get recovery data 

recovery = make_paginated_request(url=url_recovery,headers=headers)
stg_recovery = transform_recovery(recovery)

recovery_cols = stg_recovery[['sleep_id','recovery_score']]


# Get Request for sleep data
sleep = make_paginated_request(url=url_sleep, headers=headers)

stg_sleep = transform_sleep(sleep)

stg_sleep['sleep_start_ts'] = pd.to_datetime(stg_sleep['sleep_start_ts'])
stg_sleep['sleep_end_ts'] = pd.to_datetime(stg_sleep['sleep_end_ts'])


stg_sleep = stg_sleep[stg_sleep['nap'] == False]

df = stg_sleep.merge(recovery_cols,left_on='sleep_id',right_on = 'sleep_id')

df.info()

# Check missing values
print(df['score_sleep_consistency_percentage'].isnull().sum())

# Impute missing values with median
imputer = SimpleImputer(strategy='median')
df['score_sleep_consistency_percentage'] = imputer.fit_transform(df[['score_sleep_consistency_percentage']])
# Check unique values in 'score_state'

print(df['score_state'].unique())

from datetime import datetime
df['sleep_time_hr'] = df['sleep_end_ts'] - df['sleep_start_ts'] 

df['sleep_time_hr'].astype('timedelta64[s]')

df['total_sleep_time_hrs'] = df['sleep_time_hr'].dt.total_seconds() / 3600


feature_cols = [
    'score_stage_summary_total_rem_sleep_time_hrs',
    'total_sleep_time_hrs',
    'score_stage_summary_total_awake_time_hrs',
    'score_sleep_efficiency_percentage',
    'score_sleep_consistency_percentage',
]
# Define X and y
X = df[feature_cols]
y = df['score_sleep_performance_percentage'] 

df.info()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"Training set size: {X_train.shape}")
print(f"Testing set size: {X_test.shape}")

scaler = StandardScaler()

# Fit on training data
X_train_scaled = scaler.fit_transform(X_train)

# Transform test data
X_test_scaled = scaler.transform(X_test)


scaler = StandardScaler()

# Fit on training data
X_train_scaled = scaler.fit_transform(X_train)

# Transform test data
X_test_scaled = scaler.transform(X_test)


# Initialize the model
rf = RandomForestRegressor(random_state=42)

# Train the model
rf.fit(X_train_scaled, y_train)


# Define parameter grid
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10]
}

# Initialize GridSearchCV
grid_search = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    cv=5,
    scoring='neg_mean_absolute_error',
    n_jobs=-1,
    verbose=True
)

# Fit GridSearchCV
grid_search.fit(X_train_scaled, y_train)

# Best parameters
print(f"Best parameters: {grid_search.best_params_}")

# Best estimator
best_rf = grid_search.best_estimator_

# Predictions using the best model
y_pred = best_rf.predict(X_test_scaled)

# Calculate evaluation metrics
mae = mean_absolute_error(y_test, y_pred)
rmse = root_mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Absolute Error (MAE): {mae:.2f}")
print(f"Root Mean Squared Error (RMSE): {rmse:.2f}")
print(f"R-squared (R2): {r2:.2f}")

import matplotlib.pyplot as plt
import seaborn as sns

sns.histplot(df['sleep_time_hr_float'], bins=20, kde=True)
plt.title('Distribution of Sleep Time in Hours')
plt.xlabel('Sleep Time (Hours)')
plt.ylabel('Frequency')
plt.show()
