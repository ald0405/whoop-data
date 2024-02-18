
from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from typing import Any
import pandas as pd 

from authlib.common.urls import extract_params
from authlib.integrations.requests_client import OAuth2Session
import requests
###############################################
REQUEST_URL = f"https://api.prod.whoop.com/developer"

# Auth




###############################################
# Define the function for token
###############################################
def whoop_authentication(username: str,password: str) -> str:
    """
    Authenticates a user with the `WHOOP API` using `OAuth2` and retrieves an access token.

    This function sends a `POST` request to the `WHOOP API` with the user's credentials. 
    Upon successful authentication,it returns an access token that can be used for subsequent API requests. This function is specifically designed
    for `OAuth2` password grant type authentication.

    Parameters:
    - username (str): The username of the WHOOP account.
    - password (str): The password of the WHOOP account.

    Returns:
    - str: An access token string for authenticated API access.

    Raises:
    - Exception: If the authentication fails or the API response is invalid.

    Example:
    >>> username = 'user@example.com'
    >>> password = 'yourpassword'
    >>> access_token = whoop_authentication(username, password)
    >>> print(access_token)
    """
    r = requests.post("https://api-7.whoop.com/oauth/token", json={
    "issueRefresh": False,
    "password": password,
    "username": username, 
    "grant_type": "password",
    }
    )

    if r.status_code != 200: 
        raise Exception('Authentication Failed. Please Check Username & Password')
    response_data = r.json()
    print('User Authenticated')
    # user_id = response_data['user']['id']
    access_token =response_data['access_token']
    return access_token

# Authenticate & get access token
        
USERNAME = "laldin.asif@gmail.com"
PASSWORD = "Laldin10!"


access_token = whoop_authentication(username=USERNAME,password=PASSWORD)

headers = {'Authorization': f'Bearer {access_token}'}
###############################################

cycle_id = f'468407287' # for extracting a single record
slug_url = f'/v1/cycle/'
slug_url_id = f'/v1/cycle/{cycle_id}' # If you an an ID you only get back 1 record
url = f'https://api.prod.whoop.com/developer/v1/sleep/'
url = f'https://api.prod.whoop.com/developer/v1/activity/sleep/'

url = f'https://api.prod.whoop.com/developer/v1/recovery/'
url = f'https://api.prod.whoop.com/developer/v1/activity/workout'

url = REQUEST_URL + slug_url
url_cycle_id = REQUEST_URL + slug_url_id

[i for i in range(0,10)]
gen_dict = {i: i for i in range(0,10)}










###############################################
#  Making paginated requests
###############################################
# Create a unified function 
def make_paginated_request(url: str,headers: dict[str,Any]) -> pd.DataFrame:
    """
    Makes a paginated `GET` request to a specified URL and returns the aggregated data as a pandas DataFrame.

    This function is designed to handle APIs that use pagination with a `'next_token'` mechanism. It will continuously 
    make `GET` requests to the specified URL, aggregating the data from each response, until no 'next_token' is provided 
    by the API. The data from each 'records' field in the JSON response is collected.

    Parameters:
    - `url` (str): The URL endpoint for the GET request.
    - `headers` (dict[str, Any]): A dictionary of headers to send along with the GET request.

    Returns:
    - `pd.DataFrame`: A pandas DataFrame containing the aggregated data from all paginated responses.

    Notes:
    - The function expects the API response to be in JSON format with a key named 'records' that contains the relevant data.
    - The `'next_token'` for pagination is expected to be in the root of the JSON response.
    - It prints the `'next_token'` of each request and the total number of records returned for debugging purposes.

    Example:
    >>> url = 'https://api.prod.whoop.com/developer/v1/recovery/'
    >>> headers = {'Authorization': 'Bearer your_access_token'}
    >>> df = make_paginated_request(url, headers)
    >>> print(df.head())
    """
    response_data = list()
    params={}
    while True:
        response = requests.get(url, 
                                headers=headers, 
                                params=params
                                ).json()
        response_data += response['records']

        if 'next_token' in response and response['next_token']:
            next_token = response['next_token']
            params["nextToken"] = next_token  # Update the params for the next request
            print(f'next_token: {next_token}')
        else:
            break
    print (f'Returning {len(response_data)} records')
    return pd.json_normalize(response_data)

# Extract sleep 
import numpy as np
url_sleep = f'https://api.prod.whoop.com/developer/v1/activity/sleep/'
url_recovery = f'https://api.prod.whoop.com/developer/v1/recovery/'
url_cycle = f'https://api.prod.whoop.com/developer/v1/cycle/'
url_workout = f'https://api.prod.whoop.com/developer/v1/activity/workout/'
#############################################
# We always reference a member's activity in the context of a Physiological Cycle (known as Cycle for short) rather than calendar days. 
# When you request a member's latest Cycle, the member's current Cycle will only have a Start Time. Cycles in the past have both a start and end time.
# What defines a physiological day on WHOOP?
# WHOOP does not define a physiological day as 12:00 AM - 11:59 PM. 
# Instead of running on a 24-hour clock, a physiological day with WHOOP begins when you fall asleep 
# one night and ends when you fall asleep the following night. 
# This allows WHOOP to calculate all metrics during an entire Sleep/Wake cycle.
cycle = make_paginated_request(url=url_cycle,headers=headers)
#############################################
# WHOOP Recovery is a daily measure of how prepared your body is to perform. 
# When you wake up in the morning, WHOOP calculates a Recovery score as a percentage between 0 - 100%. 
# The higher the score, the more primed your body is to take on Strain that day.

# WHOOP calculates Recovery scores using measurements from the previous day and your sleep, 
# such as resting heart rate (RHR), heart rate variability (HRV), respiratory rate, sleep duration/quality, skin temperature, and blood oxygen. 
# Unlike Strain, a Recovery score does not change over the day (unless you edit your sleep which triggers a Recovery score re-calculation).
# GREEN (67-100%): You are well recovered and primed to perform. Whether at home, at work, or in the gym, your body is signaling that it can handle a strenuous day.
# YELLOW (34-66%): Your body is maintaining and ready to take on moderate amounts of strain.
# RED (0-33%): Rest is likely what your body needs. Your body is working hard to recover. Some reasons could include overtraining, 
# sickness, stress, lack of sleep, or other lifestyle factors.
#############################################
recovery = make_paginated_request(url=url_recovery,headers=headers)
#############################################
# WHOOP tracks your sleep, including how long you slept and the stages of your sleep - Light, REM, and Slow Wave Sleep (Deep). 
# WHOOP also calculates how much sleep you need based on your Sleep Debt and your previous day's activity
sleep = make_paginated_request(url=url,headers=headers)
#############################################

# WHOOP Strain is a measurement of the amount of stress on your body. The Strain score is a number on a 0 to 21 scale, 
# based on the Borg Scale of Perceived Exertion. 
# WHOOP scores Strain continuously for members throughout the day and every workout.
# WHOOP tracks workouts for you and how much Strain accumulated over the workout
workout = make_paginated_request(url=url_workout,headers=headers)

sleep['score.sleep_needed.baseline_milli','score.sleep_needed.need_from_sleep_debt_milli','score.sleep_needed.need_from_recent_strain_milli']
#############################################

###############################################
# Data Processing 
###############################################
sleep['end'] = pd.to_datetime(sleep['end'])
sleep['start'] = pd.to_datetime(sleep['start'])

sleep['sleep_time'] = sleep['end'] - sleep['start']

# Convert time delta to seconds 
sleep['sleep_hrs'] = np.round(sleep['sleep_time'].dt.total_seconds()/3600,2)

sleep['sleep_end_dt'] = sleep['end'].dt.to_period('D')

sleep.sort_values(by='sleep_end_dt',ascending=True,inplace=True)
sleep[['score.sleep_needed.baseline_milli','score.sleep_needed.need_from_sleep_debt_milli','score.sleep_needed.need_from_recent_strain_milli']]

# Select all columns in milli seconds
milli_cols = [col for col in sleep.columns if "milli" in col]

# change all milli seconds to hours 
# This was 30% faster than writing a function and using .apply 
for col in milli_cols:
    sleep[col] = sleep[col] / 36e5

sleep.info()



# Lets find weekends 
is_weekend = lambda x: x.dayofweek >= 5 

sleep['is_weekend'] = sleep['sleep_end_dt'].apply(is_weekend)

sleep['sleep_end_dt'].dt.dayofweek

import matplotlib.pyplot as plt 
import seaborn as sns 
sleep.info()
sns.set_style('darkgrid')
plt.figure(figsize=(12,6))


sns.barplot(x = 'sleep_end_dt',y = 'score.sleep_performance_percentage',data = sleep, hue = 'is_weekend')
plt.show()

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
    240: "Handball"
}


# Tables are already normalised 
# Can create multiple individual fct tables 
# A single dimension table for user profile & sports_id
# Design main fct table fct_daily_scores
# Will be daily level of grain 
# # Each day will have a 
# recovery score - how well you are recovered for today 
# sleep score - how well you slept the night before
# work out information - What sports you played on a given day 
# strain score - how much you pushed your self today/given day
# Daily fct_pollen 
# Daily fct_


###############################################
#  Define the class for Whoop API
###############################################
class MyWhoopClient:
    
    def __init__(self,username,password) -> None:
        self.username = username 
        self.password = password 
        # This will be used in subsequent methods 
        self.access_token = None 
        

    def authenticate(self) -> None:
        response_auth = requests.post(
            url="https://api-7.whoop.com/oauth/token",json = {
                "issueRefresh": False, 
                "password": self.password,
                "username": self.username,
                "grant_type": "password"
            })
        response_data = response_auth.json()
        self.access_token = response_data['access_token']
        if response_auth.status_code != 200: 
            raise Exception('Authentication Failed. Please Check Username & Password')
        else: 
            print('User Authenticated')
    def make_requests(self, url: str) -> pd.DataFrame:
        response_data = list()
        params={}
        # Token from previous auth request
        headers = {'Authorization': f'Bearer {self.access_token}'}
        while True:
            response = requests.get(url, 
                                    headers=headers, 
                                    params=params
                                    ).json()
            response_data += response['records']
            # Each response contains a record and a next_token to allow
            # us to go to the next page of records
            if 'next_token' in response and response['next_token']:
                next_token = response['next_token']
                # Update the params with token for the next request
                params["nextToken"] = next_token  
                # print(f'next_token: {next_token}')
            else:
                break
        print (f'Returning {len(response_data)} records')
        return pd.json_normalize(response_data) 
    

        
username = "laldin.asif@gmail.com"
password = "Laldin10!"

my_client = MyWhoopClient(username=username,password=password)
url = f'https://api.prod.whoop.com/developer/v1/activity/sleep/'
my_client.authenticate()

my_client.make_requests(url=url)

