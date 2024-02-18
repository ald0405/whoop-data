# WHOOP API Data Summary

## Physiological Cycles
- Activity is referenced in the context of a Physiological Cycle (Cycle for short).
- <b>Current Cycle:</b> Only has a Start Time. Past Cycles have both start and end times.
- A physiological day on WHOOP begins when you fall asleep one night and ends when you fall asleep the following night.

## Recovery
- Daily measure of body preparedness to perform.
- <b>Recovery score:</b> Percentage between 0 - 100% calculated in the morning.
- Calculated using previous day's data including RHR, HRV, respiratory rate, sleep quality, etc.
- <span style="color:green;"><b>GREEN</b></span> (67-100%): Well recovered and primed to perform.
- <span style="color:yellow;"><b>YELLOW</b></span> (34-66%): Maintaining and ready for moderate strain.
- <span style="color:red;"><b>RED</b></span> (0-33%): Indicates the need for rest.

## Sleep Tracking
- Tracks sleep duration and stages: Light, REM, and Deep sleep.
- Calculates sleep need based on Sleep Debt and previous day's activity.

## Strain
- Measurement of stress on the body, scored on a 0 to 21 scale.
- Based on [Strain Borg Scale of Perceived Exertion](https://www.cdc.gov/physicalactivity/basics/measuring/exertion.htm).
- Strain scores tracked continuously throughout the day and during workouts.

## Workout Tracking
- WHOOP tracks workouts and measures accumulated Strain over each workout.


# How to

## Credentials

You must store credentials (username and password) in a `.env` file which should always be added to your `.gitignore`
Within your `.env` please define credentials in the following format

> `USERNAME=my_email@gmail.com`
> `PASSWORD=my_password`

All necessary modules have been defined in the `requirements.txt` file.
Which can be installed via `pip install -r requirements.txt`

## Functions

There are two types of function in this repo:
* Data extraction
* Data transformation & processing 

Extraction is done via paginated requests made via the `requests` module.
Currently this functions as a full load/extraction and has not been implemented in an incremental manner.
Even for long term users this is a small dataset so there are no serious performance considerations here

Transformation is done via the `pandas` module, by default all times are measured in milliseconds and are parsed to hours or minutes depending on the context.




