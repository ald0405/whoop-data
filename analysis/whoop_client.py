import numpy as np
import requests
import logging
import pandas as pd
import os 
from dotenv import load_dotenv
load_dotenv()

class Whoop:
    """
    Authenticate & Process Data w/Whoop
    """

    # Set up logging
    logging.basicConfig(
        filename="whoops_log.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    AUTH_URL = "https://api-7.whoop.com/oauth/token"  # Class attribute

    ENDPOINTS = {
        "recovery": "https://api.prod.whoop.com/developer/v1/recovery/",
        "sleep": "https://api.prod.whoop.com/developer/v1/activity/sleep/",
        "workout": "https://api.prod.whoop.com/developer/v1/workout/",
        "strain": "https://api.prod.whoop.com/developer/v1/strain/",
    }

    def __init__(self, 
                 username: str=None, 
                 password: str=None
                 ):
        self.username = username or os.getenv("USERNAME")
        self.password = password or os.getenv("PASSWORD")
        self.access_token = None
        self.logger = logging.getLogger(__name__)

    @property
    def available_endpoints(self):
        return list(self.ENDPOINTS.keys())

    def get_endpoint_url(self, endpoint_name: str) -> str:
        """Returns the full URL for a given endpoint name."""
        return self.ENDPOINTS.get(
            endpoint_name, f"'{endpoint_name}' not found in endpoints."
        )

    def authenticate(self, endpoint="https://api-7.whoop.com/oauth/token"):
        self.logger.info("Starting Authentication   ")
        self._endpoint = endpoint
        r = requests.post(
            self.AUTH_URL,
            json={
                "issueRefresh": False,
                "password": self.password,
                "username": self.username,
                "grant_type": "password",
            },
        )
        if r.status_code != 200:
            self.logger.error("Authentication failed")
            raise Exception(f"Authentication failed {r.text}")
        response_data = r.json()
        self.access_token = response_data["access_token"]
        print("User Authenticated")

    def make_paginated_request(self, data_endpoint: str):
        if not self.access_token:
            raise Exception("Authenticate before making API requests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.logger.info(f"Getting data from {data_endpoint}")
        print(f"Getting data from {data_endpoint}")

        self.data_endpoint = data_endpoint

        response_data = list()
        params = {}
        while True:
            response = requests.get(
                self.data_endpoint, headers=headers, params=params
            ).json()
            response_data += response["records"]

            # Handle pagination
            if "next_token" in response and response["next_token"]:
                params["nextToken"] = response["next_token"]
                self.logger.debug(f"Fetching next page: {response['next_token']}")
            else:
                break

        df = pd.json_normalize(response_data)
        self.logger.info(f"Retrieved {len(response_data)} records")
        print(f"Retrieved {len(response_data)} records")

        return df  # Return the DataFrame for immediate use



# whoops.authenticate()

# whoops.make_paginated_request(
#     data_endpoint="https://api.prod.whoop.com/developer/v1/recovery/"
# )


# whoops.available_endpoints[0]
# whoops.get_endpoint_url(whoops.available_endpoints[0])
