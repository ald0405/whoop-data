from whoop_client import Whoop
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()


whoop = Whoop(username=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))

whoop.authenticate()

recovery_url = whoop.get_endpoint_url("recovery")
sleep_url = whoop.get_endpoint_url("sleep")


stg_recovery = whoop.make_paginated_request(recovery_url)
stg_sleep = whoop.make_paginated_request(
    "https://api.prod.whoop.com/developer/v1/activity/sleep/"
)


stg_sleep.info()

# stg_sleep["sleep_id"] = stg_sleep["id"].rename("sleep_id")
# stg_sleep["sleep_start_ts"] = pd.to_datetime(stg_sleep["start"])
# stg_sleep["sleep_end_ts"] = pd.to_datetime(stg_sleep["end"])
# recovery_cols = stg_recovery[["sleep_id", "score.recovery_score"]]

# stg_sleep = stg_sleep[stg_sleep["nap"] == False]
# df = stg_sleep.merge(recovery_cols, left_on="sleep_id", right_on="sleep_id")


# # Impute missing values with median
# # imputer = SimpleImputer(strategy='median')
# # df['score_sleep_consistency_percentage'] = imputer.fit_transform(df[['score_sleep_consistency_percentage']])
# # Check unique values in 'score_state'

# print(df["score_state"].unique())

# from datetime import datetime

# df["sleep_time_hr"] = df["sleep_end_ts"] - df["sleep_start_ts"]
# df["sleep_time_hr"].astype("timedelta64[s]")


# df["total_sleep_time_hrs"] = df["sleep_time_hr"].dt.total_seconds() / 3600


# df[["total_sleep_time_hrs", "score.recovery_score"]].corr()




# # Creating Relevant Groups
# df["is_high_recovery"] = df["score.recovery_score"] >= 80.0


# df["is_pre_eleven"] = df["sleep_start_ts"].dt.time < pd.to_datetime("23:00").time()


# df["is_pre_ten"] = df["sleep_start_ts"].dt.time < pd.to_datetime("22:00").time()


# df["is_pre_half_ten"] = df["sleep_start_ts"].dt.time < pd.to_datetime("22:30").time()


# group_a = df[df["is_pre_eleven"] == True]["score.recovery_score"]

# group_b = df[df["is_pre_eleven"] == False]["score.recovery_score"]


import seaborn as sns

from stats_utils import IndependentGroupsAnalysis


analyser = IndependentGroupsAnalysis()

import numpy as np 

group_a= np.random.normal(10,2,100)
group_b= np.random.normal(12,3,100)

analyser.load_data(group_a=group_b, group_b=group_a)
analyser.test_non_parametric_groups()
# analyser.test_groups()
analyser.describe()
analyser.summarise()
analyser.results()
analyser.plot_distributions(
    label_a="is_pre_eleven0", label_b="Other", xlabel="Recovery (%)"
)


# df[["total_sleep_time_hrs", "score.recovery_score", "sleep_start_ts", "sleep_end_ts"]]



from dotenv import load_dotenv
import os 
from openai import OpenAI
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

import json 
results_to_pass = analyser.results()
analyser.results_mu()


# Call GPT-4
response = client.chat.completions.create(
    model="gpt-4",
    temperature=0.5,
    messages=[
        {
            "role": "system",
            "content": "You are a statistical whiz who explains test results in a casual and easy  to understand method. Be sure to explain what the numbers mean to give the user intuition about the results and numbers."
        },
        {
            "role": "user",
            "content": f"Here are the statistical test results:\n\n{results_to_pass}\n\n"
        }
    ]
)

# Show response
print(response.choices[0].message.content)