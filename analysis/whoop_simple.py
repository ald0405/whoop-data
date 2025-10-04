import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

class WhoopSimple:
    """
    Ultra-simple Whoop client - just hits endpoints and returns raw JSON
    
    Note: This requires initial authentication via the main whoop_client.py
    to create the .whoop_tokens.json file. After that, this handles token refresh.
    """
    
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_file = ".whoop_tokens.json"

    def authenticate(self):
        """Get valid access token, return it"""
        # Load existing tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                expires_str = token_data.get('expires_at')
                if expires_str:
                    self.token_expires_at = datetime.fromisoformat(expires_str)
        
        # Check if token is valid
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
            
        # Refresh if needed
        if self.refresh_token:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            r = requests.post("https://api.prod.whoop.com/oauth/oauth2/token", data=data)
            if r.status_code == 200:
                response_data = r.json()
                self.access_token = response_data["access_token"]
                if "refresh_token" in response_data:
                    self.refresh_token = response_data["refresh_token"]
                if "expires_in" in response_data:
                    expires_in = int(response_data["expires_in"])
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Save tokens
                token_data = {
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None
                }
                with open(self.token_file, 'w') as f:
                    json.dump(token_data, f)
                os.chmod(self.token_file, 0o600)
                
                return self.access_token
        
        raise Exception("No valid authentication. Please authenticate with the main client first.")

    def get_recovery_data(self):
        """Fetches recovery data"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.prod.whoop.com/developer/v2/recovery"
        return requests.get(url, headers=headers).json()["records"]

    def get_sleep_data(self):
        """Fetches sleep data"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.prod.whoop.com/developer/v2/activity/sleep"
        return requests.get(url, headers=headers).json()["records"]

    def get_workout_data(self):
        """Fetches workout data"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.prod.whoop.com/developer/v2/activity/workout"
        return requests.get(url, headers=headers).json()["records"]

    def get_strain_data(self):
        """Fetches strain/cycle data"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.prod.whoop.com/developer/v2/cycle"
        return requests.get(url, headers=headers).json()["records"]

    def get_body_data(self):
        """Fetches body measurement data"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.prod.whoop.com/developer/v2/user/measurement/body"
        return requests.get(url, headers=headers).json()["records"]


# Standalone functions for even simpler usage
def get_recovery():
    """Get recovery data records"""
    client = WhoopSimple()
    return client.get_recovery_data()

def get_sleep():
    """Get sleep data records"""
    client = WhoopSimple()
    return client.get_sleep_data()

def get_workouts():
    """Get workout data records"""
    client = WhoopSimple()
    return client.get_workout_data()

def get_strain():
    """Get strain/cycle data records"""
    client = WhoopSimple()
    return client.get_strain_data()

def get_body():
    """Get body measurement data records"""
    client = WhoopSimple()
    return client.get_body_data()