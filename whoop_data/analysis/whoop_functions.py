from __future__ import annotations

from typing import Any
import pandas as pd
import requests


def whoop_authentication(username: str, password: str) -> str:
    """
    Authenticates a user with the `WHOOP API` using `OAuth` and retrieves an access token.

    This function sends a `POST` request to the `WHOOP API` with the user's credentials.
    Upon successful authentication,it returns an access token that can be used for subsequent API requests. This function is specifically designed
    for `OAuth` password grant type authentication.

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
    r = requests.post(
        "https://api-7.whoop.com/oauth/token",
        json={
            "issueRefresh": False,
            "password": password,
            "username": username,
            "grant_type": "password",
        },
    )

    if r.status_code != 200:
        raise Exception(
            f"Authentication Failed. {r.text} Please Check Username & Password"
        )
    response_data = r.json()
    print("User Authenticated")
    # user_id = response_data['user']['id']
    access_token = response_data["access_token"]
    return access_token


def make_paginated_request(url: str, headers: dict[str, Any]) -> pd.DataFrame:
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
    params = {}
    while True:
        response = requests.get(url, headers=headers, params=params).json()
        response_data += response["records"]

        if "next_token" in response and response["next_token"]:
            next_token = response["next_token"]
            # Update the params for the next request
            params["nextToken"] = next_token
            print(f"next_token: {next_token}")
        else:
            break
    print(f"Returning {len(response_data)} records")
    return pd.json_normalize(response_data)


def replace_periods(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replaces periods with underscores in the column names of a dataframe.

    Returns:
        A dataframe where all column's periods have been replaced with underscores
    """
    df.rename(columns=lambda x: x.replace(".", "_"), inplace=True)
    return df


def transform_sleep(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames, transforms and processes the `sleep` table


    Args:
        df (pd.DataFrame): The dataframe to convert.

    Returns:
        pd.DataFrame: The converted dataframe.
    """
    milli_cols = [col for col in df.columns if "milli" in col]
    # This was 30% faster than writing a function and using .apply
    for col in milli_cols:
        # Convert to hours
        df[col] = df[col] / 36e3
    df.rename(columns=lambda x: x.replace("milli", "hrs"), inplace=True)
    df = replace_periods(df)
    df.rename(
        columns={
            "id": "sleep_id",
            "created_at": "created_ts",
            "updated_at": "updated_ts",
            "start": "sleep_start_ts",
            "end": "sleep_end_ts",
        },
        inplace=True,
    )
    return df


def transform_workouts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames, transforms and processes the `workout` table


    Args:
        df (pd.DataFrame): The dataframe to convert.

    Returns:
        pd.DataFrame: The converted dataframe.
    """
    milli_cols = [col for col in df.columns if "milli" in col]
    # This was 30% faster than writing a function and using .apply
    for col in milli_cols:
        # Convert to hours
        df[col] = df[col] / 60e3
    df.rename(columns=lambda x: x.replace("milli", "mins"), inplace=True)
    df = replace_periods(df)
    # df["calories_burned"] = (df["score_kilojoule"] / 4.184)
    df.rename(
        columns={
            "id": "workout_id",
            "created_at": "created_ts",
            "updated_at": "updated_ts",
            "start": "workout_start_ts",
            "end": "workout_end_ts",
        },
        inplace=True,
    )
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
    df["workout_sport_name"] = df["sport_id"].map(dim_workout_sports_id_look_up)
    return df


def transform_cycles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames, transforms, and processes the 'cycle' table.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        pd.DataFrame: The converted DataFrame.
    """

    # df["end"] = pd.to_datetime(df["end"]).dt.strftime("%Y-%m-%d %H:%M")
    # df["start"] = pd.to_datetime(df["start"]).dt.strftime("%Y-%m-%d %H:%M")
    # df["updated_at"] = pd.to_datetime(df["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")

    df.rename(
        columns={
            "id": "cycle_id",
            "start": "cycle_start_ts",
            "end": "cycle_end_ts",
            "created_at": "created_ts",
            "updated_at": "updated_ts",
            "score.strain": "score_strain",
            "score.kilojoule": "score_kilojoule",
            "score.average_heart_rate": "score_avg_heart_rate",
            "score.max_heart_rate": "score_max_heart_rate",
        },
        inplace=True,
    )
    # format timestamp columns
    cols_ts = [col for col in df.columns if "_ts" in col]
    for col in cols_ts:
        df[col] = pd.to_datetime(df[col])

    # Calculate the cycle length as a timedelta
    df["cycle_length_timedelta"] = df["cycle_end_ts"] - df["cycle_start_ts"]

    # Convert the timedelta duration to hours
    df["cycle_length_hours"] = df["cycle_length_timedelta"] / pd.Timedelta(hours=1)

    return df

def transform_recovery(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames, transforms, and processes the 'recovery' table.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        pd.DataFrame: The converted DataFrame.
    """
    # Rename columns
    df = df.rename(columns={
        "created_at": "created_ts",
        "updated_at": "updated_ts",
        "score.user_calibrating": "user_calibrating",
        "score.recovery_score": "recovery_score",
        "score.resting_heart_rate": "resting_heart_rate",
        "score.hrv_rmssd_milli": "hrv_rmssd_milli",
        "score.spo2_percentage": "spo2_percentage",
        "score.skin_temp_celsius": "skin_temp_celsius"
    })
    
    # Format timestamp columns
    cols_ts = ['created_ts', 'updated_ts']
    for col in cols_ts:
        df[col] = pd.to_datetime(df[col])
    
    return df
