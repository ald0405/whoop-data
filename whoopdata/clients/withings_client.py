import requests
import json
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class WithingsClient:
    """
    Withings API client with OAuth 2.0 authentication
    Based on official Withings API documentation
    """

    # Set up logging
    logging.basicConfig(
        filename="withings_log.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Withings API URLs
    BASE_URL = "https://wbsapi.withings.net"
    AUTH_URL = "https://account.withings.com/oauth2_user/authorize2"
    TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
    MEASURE_URL = f"{BASE_URL}/measure"

    # Complete measurement types from documentation
    MEASUREMENT_TYPES = {
        1: "Weight (kg)",
        4: "Height (meter)",
        5: "Fat Free Mass (kg)",
        6: "Fat Ratio (%)",
        8: "Fat Mass Weight (kg)",
        9: "Diastolic Blood Pressure (mmHg)",
        10: "Systolic Blood Pressure (mmHg)",
        11: "Heart Pulse (bpm)",
        12: "Temperature (celsius)",
        54: "SP02 (%)",
        71: "Body Temperature (celsius)",
        73: "Skin Temperature (celsius)",
        76: "Muscle Mass (kg)",
        77: "Hydration (kg)",
        88: "Bone Mass (kg)",
        91: "Pulse Wave Velocity (m/s)",
        123: "VO2 max (ml/min/kg)",
        130: "Atrial fibrillation result",
        135: "QRS interval duration",
        136: "PR interval duration",
        137: "QT interval duration",
        138: "Corrected QT interval duration",
        139: "Atrial fibrillation result from PPG",
        155: "Vascular age",
        167: "Nerve Health Score Conductance",
        168: "Extracellular Water (kg)",
        169: "Intracellular Water (kg)",
        170: "Visceral Fat",
        173: "Fat Free Mass for segments",
        174: "Fat Mass for segments",
        175: "Muscle Mass for segments",
        196: "Electrodermal activity feet",
        226: "Basal Metabolic Rate (BMR)",
        227: "Metabolic Age",
        229: "Electrochemical Skin Conductance (ESC)",
    }

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv("WITHINGS_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("WITHINGS_CLIENT_SECRET")
        self.callback_url = os.getenv("WITHINGS_CALLBACK_URL", "http://localhost:8766/callback")

        if not self.client_id or not self.client_secret:
            raise ValueError("Withings Client ID and Client Secret must be provided")

        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.user_id = None
        self.token_file = ".withings_tokens.json"
        self.logger = logging.getLogger(__name__)

    def _load_tokens(self):
        """Load saved tokens from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    self.user_id = token_data.get("user_id")
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
                "user_id": self.user_id,
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "updated_at": datetime.now().isoformat(),
                "token_issuer": "withings",
            }
            with open(self.token_file, "w") as f:
                json.dump(token_data, f)
            # Make file readable only by user for security
            os.chmod(self.token_file, 0o600)
        except Exception as e:
            self.logger.warning(f"Failed to save tokens: {e}")

    def _is_token_valid(self):
        """Check if the current access token is valid and not expired.
        Treat missing/unknown expiry as invalid so we reauth/refresh.
        """
        if not self.access_token:
            return False
        if not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at

    def _refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            return False

        data = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        try:
            r = requests.post(self.TOKEN_URL, data=data)
            if r.status_code == 200:
                response_data = r.json()
                if response_data.get("status") == 0:  # Withings uses status 0 for success
                    body = response_data.get("body", {})
                    self.access_token = body.get("access_token")
                    if "refresh_token" in body:
                        self.refresh_token = body.get("refresh_token")
                    if "expires_in" in body:
                        expires_in = int(body.get("expires_in"))
                        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    if "userid" in body:
                        self.user_id = body.get("userid")

                    self._save_tokens()
                    self.logger.info("Access token refreshed successfully")
                    print("🔄 Withings access token refreshed")
                    return True
        except Exception as e:
            self.logger.warning(f"Failed to refresh token: {e}")
        return False

    def authenticate(self, force_reauth: bool = False):
        """Authenticate using OAuth 2.0 authorization code flow.
        If force_reauth is True, bypass cache and run full OAuth.
        """
        # First, try to load existing tokens
        if not force_reauth and self._load_tokens():
            if self._is_token_valid():
                print("✅ Using existing Withings access token")
                return
            elif self.refresh_token and self._refresh_access_token():
                return
            else:
                print("⚠️ Existing tokens invalid/expired, starting new authorization")

        # If no valid tokens, proceed with OAuth flow
        self._authenticate_authorization_code()

    def _authenticate_authorization_code(self):
        """Authenticate using authorization code flow with local callback server"""
        self.logger.info("Starting Withings Authorization Code Flow Authentication")

        import urllib.parse
        import webbrowser
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        import time
        import secrets

        auth_code = None
        state = secrets.token_urlsafe(32)

        print(f"\n🔐 Generated state: '{state}' (length: {len(state)})")
        print(f"🌐 Callback URL: {self.callback_url}")

        # Parse callback URL to get port
        from urllib.parse import urlparse

        parsed_url = urlparse(self.callback_url)
        port = parsed_url.port or 8766

        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                nonlocal auth_code
                if self.path.startswith("/callback"):
                    query = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(query)

                    if "error" in params:
                        error = params.get("error", ["Unknown error"])[0]
                        error_desc = params.get("error_description", ["No description"])[0]
                        print(f"\n❌ OAuth Error: {error}")
                        print(f"Description: {urllib.parse.unquote(error_desc)}")
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            f"<html><body><h1>Authorization failed!</h1><p>Error: {error}</p></body></html>".encode()
                        )
                    elif "code" in params:
                        received_state = params.get("state", [""])[0]
                        if received_state == state:
                            auth_code = params["code"][0]
                            self.send_response(200)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(
                                b"<html><body><h1>Withings Authorization successful!</h1><p>You can close this window.</p></body></html>"
                            )
                        else:
                            print(
                                f"\n⚠️ State mismatch! Expected: {state}, Received: {received_state}"
                            )
                            self.send_response(400)
                            self.send_header("Content-type", "text/html")
                            self.end_headers()
                            self.wfile.write(
                                b"<html><body><h1>Authorization failed!</h1><p>State parameter mismatch</p></body></html>"
                            )

        # Start callback server (bind explicitly to loopback)
        # Try desired port, then increment a few times if unavailable
        server = None
        for try_port in [port] + [port + i for i in range(1, 6)]:
            try:
                server = HTTPServer(("127.0.0.1", try_port), CallbackHandler)
                port = try_port
                break
            except OSError:
                continue
        if server is None:
            raise Exception("Unable to bind local callback server on 127.0.0.1")
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Create authorization URL (update redirect to actual bound port)
        actual_redirect = f"http://127.0.0.1:{port}/callback"
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": actual_redirect,
            "scope": "user.metrics",
            "state": state,
        }

        auth_url = f"{self.AUTH_URL}?" + urllib.parse.urlencode(auth_params)

        print(f"\n🌐 Please visit this URL to authorize the Withings application:")
        print(f"🔗 {auth_url}")
        print("🌐 Opening browser...")
        try:
            opened = webbrowser.open(auth_url)
            if not opened:
                print("⚠️ Could not open browser automatically. Copy the URL above into your browser.")
        except Exception:
            print("⚠️ Could not open browser automatically. Copy the URL above into your browser.")

        # Wait for authorization
        timeout = 300
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
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": self.callback_url,
        }

        r = requests.post(self.TOKEN_URL, data=data)

        if r.status_code != 200:
            self.logger.error(f"Token exchange failed: {r.status_code} - {r.text}")
            raise Exception(f"Token exchange failed: {r.status_code} - {r.text}")

        response_data = r.json()

        if response_data.get("status") != 0:
            self.logger.error(f"Withings API error: {response_data}")
            raise Exception(f"Withings API error: {response_data}")

        # Extract tokens from response
        body = response_data.get("body", {})
        self.access_token = body.get("access_token")
        self.refresh_token = body.get("refresh_token")
        self.user_id = body.get("userid")

        # Calculate expiration time
        if "expires_in" in body:
            expires_in = int(body.get("expires_in"))
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Save tokens to file for future use
        self._save_tokens()

        self.logger.info("User Authenticated successfully with Withings")
        print("✅ Withings Authentication successful!")
        print(f"👤 User ID: {self.user_id}")

    def _make_api_request(self, params: dict = None):
        """Make authenticated API request to Withings /measure endpoint"""
        if not self.access_token:
            raise Exception("Authenticate before making API requests")

        # Ensure token is valid
        if not self._is_token_valid():
            if self.refresh_token and self._refresh_access_token():
                pass
            else:
                raise Exception("No valid authentication. Please re-authenticate.")

        # Add authentication to params
        if params is None:
            params = {}

        params.update({"access_token": self.access_token})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(self.MEASURE_URL, data=params, headers=headers)

        if response.status_code == 401:
            # Try to refresh token and retry once
            if self.refresh_token and self._refresh_access_token():
                params["access_token"] = self.access_token
                response = requests.post(self.MEASURE_URL, data=params, headers=headers)

        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

        return response.json()

    def _parse_measurement_value(self, measure):
        """Parse measurement value considering the unit multiplier"""
        value = measure.get("value", 0)
        unit = measure.get("unit", 0)
        # Withings uses unit as a power of 10 multiplier
        actual_value = value * (10**unit)
        return actual_value

    def get_measurements(
        self,
        meastypes: str = "1,4,5,6,8",
        category: int = None,
        startdate: int = None,
        enddate: int = None,
        lastupdate: int = None,
        offset: int = None,
    ):
        """
        Get measurements from Withings API

        Args:
            meastypes: Comma-separated measurement types (default: weight, height, fat measurements)
            category: 1 for real measures, 2 for user objectives
            startdate: Data start date as unix timestamp
            enddate: Data end date as unix timestamp
            lastupdate: Timestamp for data updated after this date
            offset: Offset for pagination when more data available
        """
        params = {"action": "getmeas", "meastypes": meastypes}

        if category:
            params["category"] = category
        if startdate:
            params["startdate"] = startdate
        if enddate:
            params["enddate"] = enddate
        if lastupdate:
            params["lastupdate"] = lastupdate
        if offset:
            params["offset"] = offset

        response = self._make_api_request(params)

        if response.get("status") != 0:
            raise Exception(f"Withings API error: {response}")

        return response

    def get_body_measurements(self, startdate: int = None, enddate: int = None):
        """Get your preferred body measurements (weight, height, fat measurements)"""
        return self.get_measurements(
            meastypes="1,4,5,6,8",  # Weight, Height, Fat Free Mass, Fat Ratio, Fat Mass Weight
            startdate=startdate,
            enddate=enddate,
        )

    def get_all_measurements(self, startdate: int = None, enddate: int = None):
        """Get all available measurement types"""
        all_types = ",".join(map(str, self.MEASUREMENT_TYPES.keys()))
        return self.get_measurements(meastypes=all_types, startdate=startdate, enddate=enddate)

    def get_heart_measurements(self, startdate: int = None, enddate: int = None):
        """Get heart-related measurements (blood pressure, heart rate)"""
        return self.get_measurements(
            meastypes="9,10,11",  # Diastolic, Systolic, Heart Rate
            startdate=startdate,
            enddate=enddate,
        )

    def transform_to_dataframe(self, response):
        """Transform Withings API response into pandas DataFrame"""
        body = response.get("body", {})
        measuregrps = body.get("measuregrps", [])

        records = []
        for grp in measuregrps:
            base_record = {
                "grpid": grp.get("grpid"),
                "date": grp.get("date"),
                "created": grp.get("created"),
                "modified": grp.get("modified"),
                "category": grp.get("category"),
                "deviceid": grp.get("deviceid"),
                "timezone": grp.get("timezone"),
                "comment": grp.get("comment"),
                "datetime": datetime.fromtimestamp(grp.get("date", 0)),
            }

            measures = grp.get("measures", [])
            for measure in measures:
                record = base_record.copy()
                measure_type = measure.get("type")
                record.update(
                    {
                        "measure_type": measure_type,
                        "measure_type_name": self.MEASUREMENT_TYPES.get(
                            measure_type, f"Type {measure_type}"
                        ),
                        "raw_value": measure.get("value"),
                        "unit_multiplier": measure.get("unit"),
                        "actual_value": self._parse_measurement_value(measure),
                        "algo": measure.get("algo"),
                        "fm": measure.get("fm"),
                        "position": measure.get("position"),
                    }
                )
                records.append(record)

        return pd.DataFrame(records)

    # Simple convenience methods that return DataFrames
    def get_body_data_df(self, startdate: int = None, enddate: int = None):
        """Get body measurements as DataFrame"""
        response = self.get_body_measurements(startdate, enddate)
        return self.transform_to_dataframe(response)

    def get_latest_weight(self):
        """Get the most recent weight measurement as DataFrame"""
        response = self.get_measurements(meastypes="1", category=1)
        df = self.transform_to_dataframe(response)
        return df.head(1) if not df.empty else df

    def get_raw_response(self, meastypes: str = "1,4,5,6,8"):
        """Get raw JSON response (for debugging)"""
        return self.get_measurements(meastypes=meastypes)

    def validate_token(self) -> bool:
        """Perform a minimal authenticated request to validate token."""
        try:
            # Use a lightweight call
            resp = self.get_measurements(meastypes="1", category=1)
            return isinstance(resp, dict) and resp.get("status") == 0
        except Exception:
            return False
