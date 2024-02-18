from whoop import WhoopClient
import os 
import json 
import requests
import whoop
#  Documentation https://github.com/hedgertronic/whoop/blob/main/whoop.py
# ReadME https://github.com/hedgertronic/whoop?tab=readme-ov-file#installation
# Project 
# 1. Extract data for each domain: sleep, recovery, strain 
# 2. Model data into normalised data frames with cleaned labels and correct data type formatting
# 3. Load data into Google Cloud Storage Bucket or into Bigquery 
# 4. Model data into one big fact table that allows for data analysis where everything is floored to date


# WHOOP credentials
username="laldin.asif@gmail.com"
password="Laldin10!"


# Using a traditional constructor
client = WhoopClient(username, password)
client.authenticate()
profile = client.get_profile()

print(json.dumps(profile,indent = 3))

body = client.get_body_measurement()

print(json.dumps(body,indent = 3))

start_date = "2022-11-01"
end_date = "2022-12-22"


sleep = client.get_sleep_collection()


print(json.dumps(sleep[0],indent=3))

sleep[0]['score']['sleep_performance_percentage']

# wake up time if you remove this by 1 day it will tell you when you went to sleep
sleep[0]['end']



recovery = client.get_recovery_collection()

print(json.dumps(recovery[0],indent =3 ))

recovery[0]['recovery_score']
recovery[0]['']


workout = client.get_workout_collection()


print(json.dumps(workout[0],indent=3))

# How does recommended sleep correlate with recovery 

import pandas as pd 
import numpy as np 
df = pd.json_normalize(sleep)
df.info()
df[['end','start','score.sleep_performance_percentage','score.sleep_efficiency_percentage']]

df['end'] = pd.to_datetime(df['end'])
df['start'] = pd.to_datetime(df['start'])

df['sleep_time'] = df['end'] - df['start']

# Convert time delta to seconds 
df['sleep_hrs'] = np.round(df['sleep_time'].dt.total_seconds()/3600,2)

df['sleep_end_dt'] = df['end'].dt.to_period('D')

import matplotlib.pyplot as plt 
import seaborn as sns 

sns.set_style('darkgrid')
plt.figure(figsize=(12,6))

df['sleep_end_dt'].value_counts().plot(kind='bar')

sns.barplot(x = 'sleep_end_dt',y = 'sleep_hrs',data = df)
plt.show()






dfw = pd.json_normalize(workout)
df.info()


import requests  # for getting URL
import json  # for parsing json
from datetime import datetime  # datetime parsing
import pytz  # timezone adjusting
import csv  # for making csv files
import os

#################################################################
# USER VARIABLES

username = "laldin.asif@gmail.com"
password = "Laldin10!"
save_directory = "~/" # keep trailing slash

#################################################################
# GET ACCESS TOKEN
# Post credentials
r = requests.post("https://api-7.whoop.com/oauth/token", json={
    "issueRefresh": False,
    "password": password,
    "username": username
    "grant_type": "password",
    }
)


#  Lets do this in an objected oriented way that utilises the session object

session = requests.Session()

r = session.post("https://api-7.whoop.com/oauth/token", json={
    "grant_type": "password",
    "issueRefresh": False,
    "password": password,
    "username": username
    }
)
session
if r.status_code == 200:
     f"let's go"
# Get user_id 
user_id = r.json()['user']['id']
# Get access token 
access_token = r.json()['access_token']

# url = f'https://api-7.whoop.com/users/{user_id}/cycles'

# headers = {'Authorization': f'bearer {access_token}'}

# requests.get(url=url,headers=headers)

# The below can be done using the session object. 
REQUEST_URL = f"https://api.prod.whoop.com/developer"
slug_url = f'/v1/cycle/'
url = REQUEST_URL + slug_url 

response = session.get(f'{url}')

data = response.json()
#############################################
#  Make Requests for Cycles Data 
#############################################
cycle_id = 'some_cycle_id'  # Replace with the actual cycle ID you want to query

REQUEST_URL = f"https://api.prod.whoop.com/developer"
cycle_id = f'468407287' # for extracting a single record
slug_url = f'/v1/cycle/'
slug_url_id = f'/v1/cycle/{cycle_id}' # If you an an ID you only get back 1 record
url = f'https://api.prod.whoop.com/developer/v1/cycle/'
url = REQUEST_URL + slug_url 

headers = {'Authorization': f'Bearer {access_token}'}

response = requests.get(url=url, headers=headers)

data = response.json()

print(json.dumps(data['records'],indent=3))
#############################################
#  Get data for recovery 
#############################################
slug_url_recovery = f'/v1/recovery/'

url_recovery = REQUEST_URL + slug_url_recovery

r_reovery = requests.get(url= url_recovery,headers=headers).json()

print(json.dumps(r_reovery,indent=3))

def _make_paginated_request(self, method, url_slug, **kwargs) -> list[dict[str, Any]]:
       params = kwargs.pop("params", {})
       response_data: list[dict[str, Any]] = []
       while True:
           response = self._make_request(
               method=method,
               url_slug=url_slug,
               params=params,
               **kwargs,
           )
           response_data += response["records"]
           if next_token := response["next_token"]:
               params["nextToken"] = next_token
           else:
               break
       return response_data





def make_request(method: str, url_slug: str, **kwargs: Any) -> dict[str, Any]:
        response = request(method=method,url=f"{REQUEST_URL}/{url_slug}",**kwargs,
        )

        response.raise_for_status()

        return response.json()
