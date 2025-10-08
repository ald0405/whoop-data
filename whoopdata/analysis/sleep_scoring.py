from dotenv import load_dotenv

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

# For handling missing values
from sklearn.impute import SimpleImputer
# Configure matplotlib for headless operation before importing pyplot
import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
plt.ioff()  # Turn off interactive mode
import seaborn as sns
import os
from datetime import datetime, timedelta
from whoop_functions import (
    whoop_authentication,
    make_paginated_request,
    transform_sleep,
    transform_recovery,
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

recovery = make_paginated_request(url=url_recovery, headers=headers)
stg_recovery = transform_recovery(recovery)

recovery_cols = stg_recovery[["sleep_id", "recovery_score"]]


# Get Request for sleep data
sleep = make_paginated_request(url=url_sleep, headers=headers)

stg_sleep = transform_sleep(sleep)

stg_sleep["sleep_start_ts"] = pd.to_datetime(stg_sleep["sleep_start_ts"])
stg_sleep["sleep_end_ts"] = pd.to_datetime(stg_sleep["sleep_end_ts"])


stg_sleep = stg_sleep[stg_sleep["nap"] == False]

df = stg_sleep.merge(recovery_cols, left_on="sleep_id", right_on="sleep_id")


# Check missing values
print(df["score_sleep_consistency_percentage"].isnull().sum())

# Impute missing values with median
imputer = SimpleImputer(strategy="median")
df["score_sleep_consistency_percentage"] = imputer.fit_transform(
    df[["score_sleep_consistency_percentage"]]
)
# Check unique values in 'score_state'

print(df["score_state"].unique())

from datetime import datetime

df["sleep_time_hr"] = df["sleep_end_ts"] - df["sleep_start_ts"]

df["sleep_time_hr"].astype("timedelta64[s]")

df["total_sleep_time_hrs"] = df["sleep_time_hr"].dt.total_seconds() / 3600

feature_cols = [
    "score_stage_summary_total_rem_sleep_time_hrs",
    "total_sleep_time_hrs",
    "score_stage_summary_total_awake_time_hrs",
    # 'score_sleep_efficiency_percentage',
    # 'score_sleep_consistency_percentage',
]
# Define X and y
X = df[feature_cols]
y = df["score_sleep_performance_percentage"]

df.info()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"Training set size: {X_train.shape}")
print(f"Testing set size: {X_test.shape}")

scaler = StandardScaler()


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
    "n_estimators": [100, 200, 300],
    "max_depth": [None, 10, 20, 30],
    "min_samples_split": [2, 5, 10],
}

# Initialize GridSearchCV
grid_search = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    cv=5,
    scoring="neg_mean_absolute_error",
    n_jobs=-1,
    verbose=True,
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

# matplotlib and seaborn already imported above

sns.histplot(df["sleep_time_hr_float"], bins=20, kde=True)
plt.title("Distribution of Sleep Time in Hours")
plt.xlabel("Sleep Time (Hours)")
plt.ylabel("Frequency")
plt.show()
# ========================================================================
# Linear Regression
# ========================================================================
# Machine Learning
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

# Initialize the Linear Regression model
lin_reg = LinearRegression()

# Train the model on the training data
lin_reg.fit(X_train, y_train)

# Display the coefficients
coefficients = pd.Series(lin_reg.coef_, index=X_train.columns)
print("Linear Regression Coefficients:")
print(coefficients)
# Make predictions on the test set
y_pred = lin_reg.predict(X_test)

# Calculate evaluation metrics
mae = mean_absolute_error(y_test, y_pred)
rmse = root_mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

# Print the evaluation metrics
print("\nLinear Regression Model Evaluation:")
print(f"Mean Absolute Error (MAE): {mae:.2f}")
print(f"Root Mean Squared Error (RMSE): {rmse:.2f}")
print(f"R-squared (R²): {r2:.2f}")

# ===============================================================================================
# XGBoost
# ===============================================================================================
import xgboost as xgb

# Initialize the XGBoost Regressor
xgb_reg = xgb.XGBRegressor(
    objective="reg:squarederror",  # For regression tasks
    n_estimators=100,  # Number of trees
    learning_rate=0.1,  # Step size shrinkage
    max_depth=6,  # Maximum tree depth for base learners
    random_state=42,  # For reproducibility
    n_jobs=-1,  # Use all available cores
)

# Train the model
xgb_reg.fit(X_train, y_train)

# Display the parameters
print("XGBoost Regressor Parameters:")
print(xgb_reg.get_params())
# Make predictions on the test set
y_pred_xgb = xgb_reg.predict(X_test)
# Calculate evaluation metrics
mae_xgb = mean_absolute_error(y_test, y_pred_xgb)
rmse_xgb = root_mean_squared_error(y_test, y_pred_xgb)
r2_xgb = r2_score(y_test, y_pred_xgb)

# Print the evaluation metrics
print("\nXGBoost Regression Model Evaluation:")
print(f"Mean Absolute Error (MAE): {mae_xgb:.2f}")
print(f"Root Mean Squared Error (RMSE): {rmse_xgb:.2f}")
print(f"R-squared (R²): {r2_xgb:.2f}")


# =====================================
# Define the number of samples to display
n_samples = 30

# Create a DataFrame for easier plotting
comparison_df = pd.DataFrame(
    {
        "Sample": range(1, n_samples + 1),
        "Actual": y_test.iloc[:n_samples].values,
        "Predicted": y_pred_xgb[:n_samples],
    }
)

# Set the aesthetic style of the plots
sns.set_theme(style="whitegrid")

# Define the position of bars on the x-axis
x = np.arange(n_samples)  # the label locations
width = 0.35  # the width of the bars

# Create the plot
plt.figure(figsize=(14, 7))
plt.bar(x - width / 2, comparison_df["Actual"], width, label="Actual", color="#32D9D5")
plt.bar(
    x + width / 2, comparison_df["Predicted"], width, label="Predicted", color="black"
)

# Add labels, title, and custom x-axis tick labels
plt.xlabel("Sample Number", fontsize=14)
plt.ylabel("Sleep Score (%)", fontsize=14)
plt.title("Actual vs. Predicted Sleep Scores", fontsize=16)
plt.xticks(x, comparison_df["Sample"])

# Add a legend
plt.legend(fontsize=12)

# Add gridlines for better readability
plt.grid(axis="y", linestyle="--", alpha=0.7)

# Display the plot
plt.tight_layout()
plt.show()
# =============
