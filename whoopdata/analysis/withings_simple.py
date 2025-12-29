import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class WithingsSimple:
    """
    Ultra-simple Withings client - just hits endpoints and returns raw JSON

    Note: This requires initial authentication via the main WithingsClient
    to create the .withings_tokens.json file. After that, this handles token refresh.
    """

    def __init__(self):
        self.client_id = os.getenv("WITHINGS_CLIENT_ID")
        self.client_secret = os.getenv("WITHINGS_CLIENT_SECRET")
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.user_id = None
        self.token_file = ".withings_tokens.json"
        self.measure_url = "https://wbsapi.withings.net/measure"
        self.token_url = "https://wbsapi.withings.net/v2/oauth2"

    def authenticate(self):
        """Get valid access token, return it"""
        # Load existing tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                token_data = json.load(f)
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.user_id = token_data.get("user_id")
                expires_str = token_data.get("expires_at")
                if expires_str:
                    self.token_expires_at = datetime.fromisoformat(expires_str)

        # Check if token is valid
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token

        # Refresh if needed
        if self.refresh_token:
            data = {
                "action": "requesttoken",
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            }

            r = requests.post(self.token_url, data=data)
            if r.status_code == 200:
                response_data = r.json()
                if response_data.get("status") == 0:
                    body = response_data.get("body", {})
                    self.access_token = body.get("access_token")
                    if "refresh_token" in body:
                        self.refresh_token = body.get("refresh_token")
                    if "expires_in" in body:
                        expires_in = int(body.get("expires_in"))
                        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    if "userid" in body:
                        self.user_id = body.get("userid")

                    # Save tokens
                    token_data = {
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "user_id": self.user_id,
                        "expires_at": (
                            self.token_expires_at.isoformat() if self.token_expires_at else None
                        ),
                    }
                    with open(self.token_file, "w") as f:
                        json.dump(token_data, f)
                    os.chmod(self.token_file, 0o600)

                    return self.access_token

        raise Exception(
            "No valid authentication. Please authenticate with the main WithingsClient first."
        )

    def get_body_measurements(self):
        """Fetches body measurements (weight, height, fat measurements)"""
        token = self.authenticate()
        params = {
            "action": "getmeas",
            "meastypes": "1,4,5,6,8",  # Weight, Height, Fat Free Mass, Fat Ratio, Fat Mass Weight
            "access_token": token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(self.measure_url, data=params, headers=headers)
        return response.json()

    def get_weight_data(self):
        """Fetches weight measurements only"""
        token = self.authenticate()
        params = {"action": "getmeas", "meastypes": "1", "access_token": token}  # Weight only
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(self.measure_url, data=params, headers=headers)
        return response.json()

    def get_heart_data(self):
        """Fetches heart-related measurements"""
        token = self.authenticate()
        params = {
            "action": "getmeas",
            "meastypes": "9,10,11",  # Diastolic, Systolic, Heart Rate
            "access_token": token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(self.measure_url, data=params, headers=headers)
        return response.json()

    def get_all_measurements(self):
        """Fetches all available measurements"""
        token = self.authenticate()
        # All measurement types from documentation
        all_types = "1,4,5,6,8,9,10,11,12,54,71,73,76,77,88,91,123,130,135,136,137,138,139,155,167,168,169,170,173,174,175,196,226,227,229"
        params = {"action": "getmeas", "meastypes": all_types, "access_token": token}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(self.measure_url, data=params, headers=headers)
        return response.json()


# Standalone functions for even simpler usage
def get_body_measurements():
    """Get body measurement records"""
    client = WithingsSimple()
    return client.get_body_measurements()


def get_weight():
    """Get weight data records"""
    client = WithingsSimple()
    return client.get_weight_data()


def get_heart_data():
    """Get heart measurement records"""
    client = WithingsSimple()
    return client.get_heart_data()


def get_all_data():
    """Get all measurement records"""
    client = WithingsSimple()
    return client.get_all_measurements()
