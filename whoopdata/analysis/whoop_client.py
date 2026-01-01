import numpy as np
import requests
import logging
import pandas as pd
import os
import json
from datetime import datetime, timedelta
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
    TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"  # OAuth 2.0 token endpoint

    ENDPOINTS = {
        "recovery": "https://api.prod.whoop.com/developer/v2/recovery",
        "sleep": "https://api.prod.whoop.com/developer/v2/activity/sleep",
        "workout": "https://api.prod.whoop.com/developer/v2/activity/workout",
        "strain": "https://api.prod.whoop.com/developer/v2/cycle",
        "body": "https://api.prod.whoop.com/developer/v2/user/measurement/body",
    }

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        username: str = None,
        password: str = None,
    ):
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.username = username or os.getenv("USERNAME")
        self.password = password or os.getenv("PASSWORD")

        # Try OAuth 2.0 first, fall back to legacy if needed
        if not self.client_id or not self.client_secret:
            if not self.username or not self.password:
                raise ValueError(
                    "Either (Client ID and Client Secret) OR (Username and Password) must be provided"
                )

        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_file = ".whoop_tokens.json"  # Hidden file to store tokens
        self.logger = logging.getLogger(__name__)

    @property
    def available_endpoints(self):
        return list(self.ENDPOINTS.keys())

    def get_endpoint_url(self, endpoint_name: str) -> str:
        """Returns the full URL for a given endpoint name."""
        return self.ENDPOINTS.get(endpoint_name, f"'{endpoint_name}' not found in endpoints.")

    def _load_tokens(self):
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
        except Exception as e:
            self.logger.warning(f"Failed to load tokens: {e}")
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
            # Make file readable only by user for security
            os.chmod(self.token_file, 0o600)
        except Exception as e:
            self.logger.warning(f"Failed to save tokens: {e}")

    def _is_token_valid(self):
        """Check if the current access token is valid and not expired"""
        if not self.access_token:
            return False
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            return False
        return True

    def _refresh_access_token(self):
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
                self.logger.info("Access token refreshed successfully")
                print("Access token refreshed")
                return True
        except Exception as e:
            self.logger.warning(f"Failed to refresh token: {e}")
        return False

    def authenticate(self):
        """Authenticate using the most appropriate method"""
        # First, try to load existing tokens
        if self._load_tokens():
            if self._is_token_valid():
                print("Using existing access token")
                return
            elif self.refresh_token and self._refresh_access_token():
                return
            else:
                print("Existing tokens expired, need new authorization")

        # If no valid tokens, proceed with OAuth flow
        if self.client_id and self.client_secret:
            try:
                return self._authenticate_client_credentials()
            except Exception as e:
                self.logger.warning(f"Client credentials flow failed: {e}")
                if self.username and self.password:
                    self.logger.info("Falling back to authorization code flow")
                    return self._authenticate_authorization_code()
                else:
                    raise e
        elif self.username and self.password:
            return self._authenticate_authorization_code()
        else:
            raise ValueError("No valid authentication credentials provided")

    def _authenticate_client_credentials(self):
        """Authenticate using OAuth 2.0 client credentials flow"""
        self.logger.info("Starting OAuth 2.0 Client Credentials Authentication")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement",
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        r = requests.post(self.TOKEN_URL, data=data, headers=headers)

        if r.status_code != 200:
            self.logger.error(
                f"Client credentials authentication failed: {r.status_code} - {r.text}"
            )
            raise Exception(f"Client credentials authentication failed: {r.status_code} - {r.text}")

        response_data = r.json()
        self.access_token = response_data["access_token"]
        self.logger.info("User Authenticated successfully with client credentials")
        print("User Authenticated with OAuth 2.0")

    def _authenticate_authorization_code(self):
        """Authenticate using authorization code flow (requires user interaction)"""
        self.logger.info("Starting Authorization Code Flow Authentication")

        # For authorization code flow, we need to:
        # 1. Create authorization URL
        # 2. Get user to authorize
        # 3. Exchange code for token

        import urllib.parse
        import webbrowser
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        import time
        import secrets

        auth_code = None
        state = secrets.token_urlsafe(32)  # Generate secure random state
        callback_url = os.getenv("CALL_BACK_URL", "http://localhost:8765/callback")

        print(f"\nGenerated state: '{state}' (length: {len(state)})")
        print(f"Callback URL: {callback_url}")

        # Parse callback URL to get port
        from urllib.parse import urlparse

        parsed_url = urlparse(callback_url)
        port = parsed_url.port or 8765

        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress default logging to avoid cluttering output
                pass

            def do_GET(self):
                nonlocal auth_code
                if self.path.startswith("/callback"):
                    query = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(query)

                    if "error" in params:
                        error = params.get("error", ["Unknown error"])[0]
                        error_desc = params.get("error_description", ["No description"])[0]
                        print(f"\nOAuth Error: {error}")
                        print(f"Description: {urllib.parse.unquote(error_desc)}")
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            f"<html><body><h1>Authorization failed!</h1><p>Error: {error}</p><p>{urllib.parse.unquote(error_desc)}</p></body></html>".encode()
                        )
                    elif "code" in params:
                        # Verify state parameter
                        received_state = params.get("state", [""])[0]
                        if received_state == state:
                            auth_code = params["code"][0]
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(
                                b"<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>"
                            )
                        else:
                            print(
                                f"\nState mismatch! Expected: {state}, Received: {received_state}"
                            )
                            self.send_response(400)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(
                                b"<html><body><h1>Authorization failed!</h1><p>State parameter mismatch</p></body></html>"
                            )
                    else:
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            b"<html><body><h1>Authorization failed!</h1><p>No authorization code received</p></body></html>"
                        )

        # Start callback server
        server = HTTPServer(("localhost", port), CallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Create authorization URL - use the exact same callback_url format for both auth and token exchange
        auth_url = f"https://api.prod.whoop.com/oauth/oauth2/auth?response_type=code&client_id={self.client_id}&redirect_uri={urllib.parse.quote(callback_url, safe='')}&scope=read:recovery%20read:cycles%20read:sleep%20read:workout%20read:profile%20read:body_measurement&state={state}"

        print(f"\nPlease visit this URL to authorize the application: {auth_url}")
        print("Opening browser...")
        webbrowser.open(auth_url)

        # Wait for authorization
        timeout = 300  # 5 minutes
        start_time = time.time()
        while auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(1)

        server.shutdown()

        if auth_code is None:
            raise Exception(
                "Authorization timeout - user did not complete authorization within 5 minutes"
            )

        # Exchange code for token
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": callback_url,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        r = requests.post(self.TOKEN_URL, data=data, headers=headers)

        if r.status_code != 200:
            self.logger.error(f"Token exchange failed: {r.status_code} - {r.text}")
            raise Exception(f"Token exchange failed: {r.status_code} - {r.text}")

        response_data = r.json()
        self.access_token = response_data["access_token"]

        # Save refresh token if provided
        if "refresh_token" in response_data:
            self.refresh_token = response_data["refresh_token"]

        # Calculate expiration time
        if "expires_in" in response_data:
            expires_in = int(response_data["expires_in"])
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Save tokens to file for future use
        self._save_tokens()

        self.logger.info("User Authenticated successfully with authorization code")
        print("User Authenticated with Authorization Code Flow")

    def _flatten_nested_dict(self, data: dict, parent_key: str = "", sep: str = ".") -> dict:
        """Flatten nested dictionary structure (e.g., score.recovery_score)"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_nested_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))
        return dict(items)

    def _transform_for_database(self, records: list, endpoint_type: str) -> pd.DataFrame:
        """Transform API response to match database schema"""
        if not records:
            return pd.DataFrame()

        print(
            f"🔄 Transforming {len(records)} {endpoint_type} records for database compatibility..."
        )

        transformed_records = []
        for record in records:
            # Flatten nested structures
            flat_record = self._flatten_nested_dict(record)
            transformed_records.append(flat_record)

        df = pd.DataFrame(transformed_records)

        # Apply endpoint-specific transformations
        if "recovery" in endpoint_type.lower():
            df = self._transform_recovery_fields(df)
        elif "sleep" in endpoint_type.lower():
            df = self._transform_sleep_fields(df)
        elif "workout" in endpoint_type.lower():
            df = self._transform_workout_fields(df)
        elif "cycle" in endpoint_type.lower() or "strain" in endpoint_type.lower():
            df = self._transform_cycle_fields(df)

        print(f"✅ Transformation complete. Available fields: {list(df.columns)}")
        return df

    def _transform_recovery_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform recovery data fields to match database schema"""
        # Rename nested score fields to match database
        rename_map = {
            "score.user_calibrating": "user_calibrating",
            "score.recovery_score": "recovery_score",
            "score.resting_heart_rate": "resting_heart_rate",
            "score.hrv_rmssd_milli": "hrv_rmssd_milli",
            "score.spo2_percentage": "spo2_percentage",
            "score.skin_temp_celsius": "skin_temp_celsius",
        }
        return df.rename(columns=rename_map)

    def _transform_sleep_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform sleep data fields to match database schema"""
        rename_map = {
            # Main score fields
            "score.respiratory_rate": "respiratory_rate",
            "score.sleep_performance_percentage": "sleep_performance_percentage",
            "score.sleep_consistency_percentage": "sleep_consistency_percentage",
            "score.sleep_efficiency_percentage": "sleep_efficiency_percentage",
            # Stage summary fields
            "score.stage_summary.total_in_bed_time_milli": "total_time_in_bed_time_milli",
            "score.stage_summary.total_awake_time_milli": "total_awake_time_milli",
            "score.stage_summary.total_no_data_time_milli": "total_no_data_time_milli",
            "score.stage_summary.total_slow_wave_sleep_time_milli": "total_slow_wave_sleep_time_milli",
            "score.stage_summary.total_rem_sleep_time_milli": "total_rem_sleep_time_milli",
            "score.stage_summary.sleep_cycle_count": "sleep_cycle_count",
            "score.stage_summary.disturbance_count": "disturbance_count",
            # Sleep needed fields
            "score.sleep_needed.baseline_milli": "baseline_sleep_needed_milli",
            "score.sleep_needed.need_from_sleep_debt_milli": "need_from_sleep_debt_milli",
            "score.sleep_needed.need_from_recent_strain_milli": "need_from_recent_strain_milli",
            "score.sleep_needed.need_from_recent_nap_milli": "need_from_recent_nap_milli",
        }
        return df.rename(columns=rename_map)

    def _transform_cycle_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform cycle data fields to match database schema"""
        rename_map = {
            # Main score fields for cycles
            "score.strain": "strain",
            "score.kilojoule": "kilojoule",
            "score.average_heart_rate": "average_heart_rate",
            "score.max_heart_rate": "max_heart_rate",
        }
        return df.rename(columns=rename_map)

    def _transform_workout_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform workout data fields to match database schema"""
        rename_map = {
            # Main score fields
            "score.strain": "strain",
            "score.average_heart_rate": "average_heart_rate",
            "score.max_heart_rate": "max_heart_rate",
            "score.kilojoule": "kilojoule",
            "score.percent_recorded": "percent_recorded",
            "score.distance_meter": "distance_meter",
            "score.altitude_gain_meter": "altitude_gain_meter",
            "score.altitude_change_meter": "altitude_change_meter",
            # Zone duration fields (convert from milliseconds to minutes)
            "score.zone_durations.zone_zero_milli": "zone_zero_minutes",
            "score.zone_durations.zone_one_milli": "zone_one_minutes",
            "score.zone_durations.zone_two_milli": "zone_two_minutes",
            "score.zone_durations.zone_three_milli": "zone_three_minutes",
            "score.zone_durations.zone_four_milli": "zone_four_minutes",
            "score.zone_durations.zone_five_milli": "zone_five_minutes",
        }

        df = df.rename(columns=rename_map)

        # Convert zone durations from milliseconds to minutes
        zone_columns = [col for col in df.columns if col.endswith("_minutes")]
        for col in zone_columns:
            if col in df.columns:
                df[col] = df[col] / 60000.0  # Convert ms to minutes

        return df

    def make_paginated_request(
        self, data_endpoint: str, transform_for_db: bool = True, start: str = None, end: str = None
    ):
        """Make paginated request to WHOOP API with optional date filtering.

        Args:
            data_endpoint: WHOOP API endpoint URL
            transform_for_db: Whether to transform data for database compatibility
            start: Start date in ISO 8601 format (e.g. "2022-04-24T11:25:44.774Z")
            end: End date in ISO 8601 format (e.g. "2022-04-24T11:25:44.774Z")
        """
        if not self.access_token:
            raise Exception("Authenticate before making API requests")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.logger.info(f"Getting data from {data_endpoint}")

        # Log date filtering if used
        if start or end:
            date_info = f" (from {start or 'beginning'} to {end or 'now'})"
            print(f"📅 Getting data from {data_endpoint}{date_info}")
        else:
            print(f"Getting data from {data_endpoint}")

        self.data_endpoint = data_endpoint

        response_data = list()
        params = {}

        # Add date filters if provided
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        while True:
            raw_response = requests.get(self.data_endpoint, headers=headers, params=params)

            # Handle rate limiting
            if raw_response.status_code == 429:
                reset_time = int(raw_response.headers.get("X-RateLimit-Reset", 60))
                print(f"⚠️ Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
                import time

                time.sleep(reset_time + 1)  # Add 1 extra second buffer
                print("🔄 Retrying request after rate limit reset...")
                continue  # Retry the request

            # Debug information for other errors
            if raw_response.status_code != 200:
                print(f"❌ API request failed: {raw_response.status_code}")
                print(f"Response headers: {dict(raw_response.headers)}")
                print(f"Response text: {raw_response.text[:500]}...")  # First 500 chars
                raise Exception(
                    f"API request failed with status {raw_response.status_code}: {raw_response.text}"
                )

            try:
                response = raw_response.json()
            except Exception as e:
                print(f"❌ JSON decode failed. Status code: {raw_response.status_code}")
                print(f"Response headers: {dict(raw_response.headers)}")
                print(f"Response content: {raw_response.text[:1000]}...")  # First 1000 chars
                raise Exception(f"Failed to parse JSON response: {e}")

            response_data += response["records"]

            # Handle pagination
            if "next_token" in response and response["next_token"]:
                params["nextToken"] = response["next_token"]
                self.logger.debug(f"Fetching next page: {response['next_token']}")
            else:
                break

        self.logger.info(f"Retrieved {len(response_data)} records")
        print(f"Retrieved {len(response_data)} records")

        # Transform data for database compatibility if requested
        if transform_for_db and response_data:
            # Extract endpoint type, handling trailing slashes
            endpoint_parts = data_endpoint.rstrip("/").split("/")
            endpoint_type = endpoint_parts[-1] if endpoint_parts else ""
            print(f"🎯 Detected endpoint type: '{endpoint_type}'")
            return self._transform_for_database(response_data, endpoint_type)
        else:
            # Return raw data as DataFrame
            return pd.json_normalize(response_data)
