import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()


class WhoopNodes:
    """
    Ultra-lightweight Whoop client for LangGraph nodes
    Pure data retrieval without database operations or heavy transformations
    """

    TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

    ENDPOINTS = {
        "recovery": "https://api.prod.whoop.com/developer/v2/recovery",
        "sleep": "https://api.prod.whoop.com/developer/v2/activity/sleep",
        "workout": "https://api.prod.whoop.com/developer/v2/activity/workout",
        "strain": "https://api.prod.whoop.com/developer/v2/cycle",
        "body": "https://api.prod.whoop.com/developer/v2/user/measurement/body",
    }

    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_file = ".whoop_tokens.json"
        self._load_tokens()

    def _load_tokens(self) -> bool:
        """Load saved tokens from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    expires_str = token_data.get("expires_at")
                    if expires_str:
                        self.token_expires_at = datetime.fromisoformat(expires_str)
                    return True
        except Exception:
            pass
        return False

    def _save_tokens(self):
        """Save tokens to file"""
        try:
            token_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            }
            with open(self.token_file, "w") as f:
                json.dump(token_data, f)
            os.chmod(self.token_file, 0o600)
        except Exception:
            pass

    def _is_token_valid(self) -> bool:
        """Check if the current access token is valid and not expired"""
        if not self.access_token:
            return False
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            return False
        return True

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            r = requests.post(self.TOKEN_URL, data=data, headers=headers)
            if r.status_code == 200:
                response_data = r.json()
                self.access_token = response_data["access_token"]
                if "refresh_token" in response_data:
                    self.refresh_token = response_data["refresh_token"]
                if "expires_in" in response_data:
                    expires_in = int(response_data["expires_in"])
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                self._save_tokens()
                return True
        except Exception:
            pass
        return False

    def _ensure_auth(self) -> bool:
        """Ensure we have a valid access token"""
        if self._is_token_valid():
            return True
        if self.refresh_token and self._refresh_access_token():
            return True
        raise Exception("No valid authentication. Please authenticate with the main client first.")

    def _make_request(self, endpoint: str, limit: int = 25) -> Dict[str, Any]:
        """Make a single API request and return raw response"""
        self._ensure_auth()

        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"limit": limit}

        response = requests.get(endpoint, headers=headers, params=params)

        # Handle rate limiting
        if response.status_code == 429:
            reset_time = int(response.headers.get("X-RateLimit-Reset", 60))
            import time

            time.sleep(reset_time + 1)
            response = requests.get(endpoint, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

        return response.json()

    # LangGraph Node Functions - Pure Data Retrieval

    def get_recovery_data(self, limit: int = 25) -> Dict[str, Any]:
        """
        LangGraph Node: Get recovery data
        Returns: Dict with 'records', 'count', and 'has_more' keys
        """
        try:
            response = self._make_request(self.ENDPOINTS["recovery"], limit)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "recovery",
                "records": records,
                "count": len(records),
                "has_more": bool(response.get("next_token")),
                "next_token": response.get("next_token"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "recovery",
                "records": [],
                "count": 0,
            }

    def get_sleep_data(self, limit: int = 25) -> Dict[str, Any]:
        """
        LangGraph Node: Get sleep data
        Returns: Dict with 'records', 'count', and 'has_more' keys
        """
        try:
            response = self._make_request(self.ENDPOINTS["sleep"], limit)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "sleep",
                "records": records,
                "count": len(records),
                "has_more": bool(response.get("next_token")),
                "next_token": response.get("next_token"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "sleep",
                "records": [],
                "count": 0,
            }

    def get_workout_data(self, limit: int = 25) -> Dict[str, Any]:
        """
        LangGraph Node: Get workout data
        Returns: Dict with 'records', 'count', and 'has_more' keys
        """
        try:
            response = self._make_request(self.ENDPOINTS["workout"], limit)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "workout",
                "records": records,
                "count": len(records),
                "has_more": bool(response.get("next_token")),
                "next_token": response.get("next_token"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "workout",
                "records": [],
                "count": 0,
            }

    def get_strain_data(self, limit: int = 25) -> Dict[str, Any]:
        """
        LangGraph Node: Get strain/cycle data
        Returns: Dict with 'records', 'count', and 'has_more' keys
        """
        try:
            response = self._make_request(self.ENDPOINTS["strain"], limit)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "strain",
                "records": records,
                "count": len(records),
                "has_more": bool(response.get("next_token")),
                "next_token": response.get("next_token"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "strain",
                "records": [],
                "count": 0,
            }

    def get_body_data(self, limit: int = 25) -> Dict[str, Any]:
        """
        LangGraph Node: Get body measurement data
        Returns: Dict with 'records', 'count', and 'has_more' keys
        """
        try:
            response = self._make_request(self.ENDPOINTS["body"], limit)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "body",
                "records": records,
                "count": len(records),
                "has_more": bool(response.get("next_token")),
                "next_token": response.get("next_token"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "body",
                "records": [],
                "count": 0,
            }

    def get_latest_recovery(self) -> Dict[str, Any]:
        """
        LangGraph Node: Get just the most recent recovery record
        Returns: Single record or None
        """
        try:
            response = self._make_request(self.ENDPOINTS["recovery"], limit=1)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "recovery_latest",
                "record": records[0] if records else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "recovery_latest",
                "record": None,
            }

    def get_latest_sleep(self) -> Dict[str, Any]:
        """
        LangGraph Node: Get just the most recent sleep record
        Returns: Single record or None
        """
        try:
            response = self._make_request(self.ENDPOINTS["sleep"], limit=1)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "sleep_latest",
                "record": records[0] if records else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data_type": "sleep_latest", "record": None}

    def get_latest_workout(self) -> Dict[str, Any]:
        """
        LangGraph Node: Get just the most recent workout record
        Returns: Single record or None
        """
        try:
            response = self._make_request(self.ENDPOINTS["workout"], limit=1)
            records = response.get("records", [])

            return {
                "success": True,
                "data_type": "workout_latest",
                "record": records[0] if records else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data_type": "workout_latest",
                "record": None,
            }

    def get_summary_data(self, limit: int = 5) -> Dict[str, Any]:
        """
        LangGraph Node: Get summary of all data types
        Returns: Dict with recent records from all endpoints
        """
        try:
            results = {
                "success": True,
                "data_type": "summary",
                "timestamp": datetime.now().isoformat(),
            }

            # Get recent data from each endpoint
            for data_type, endpoint in self.ENDPOINTS.items():
                try:
                    response = self._make_request(endpoint, limit)
                    records = response.get("records", [])
                    results[data_type] = {
                        "count": len(records),
                        "records": records,
                        "has_more": bool(response.get("next_token")),
                    }
                except Exception as e:
                    results[data_type] = {"error": str(e), "count": 0, "records": []}

            return results
        except Exception as e:
            return {"success": False, "error": str(e), "data_type": "summary"}


# Standalone utility functions for LangGraph nodes
def create_whoop_nodes() -> WhoopNodes:
    """Factory function to create WhoopNodes instance"""
    return WhoopNodes()


def recovery_node(state: Dict[str, Any], limit: int = 25) -> Dict[str, Any]:
    """Standalone LangGraph node function for recovery data"""
    client = WhoopNodes()
    result = client.get_recovery_data(limit)
    return {**state, "whoop_recovery": result}


def sleep_node(state: Dict[str, Any], limit: int = 25) -> Dict[str, Any]:
    """Standalone LangGraph node function for sleep data"""
    client = WhoopNodes()
    result = client.get_sleep_data(limit)
    return {**state, "whoop_sleep": result}


def workout_node(state: Dict[str, Any], limit: int = 25) -> Dict[str, Any]:
    """Standalone LangGraph node function for workout data"""
    client = WhoopNodes()
    result = client.get_workout_data(limit)
    return {**state, "whoop_workout": result}


def latest_recovery_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Standalone LangGraph node function for latest recovery"""
    client = WhoopNodes()
    result = client.get_latest_recovery()
    return {**state, "whoop_latest_recovery": result}


def latest_sleep_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Standalone LangGraph node function for latest sleep"""
    client = WhoopNodes()
    result = client.get_latest_sleep()
    return {**state, "whoop_latest_sleep": result}


def summary_node(state: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
    """Standalone LangGraph node function for summary data"""
    client = WhoopNodes()
    result = client.get_summary_data(limit)
    return {**state, "whoop_summary": result}
