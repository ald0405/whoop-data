import numpy as np
import requests
import logging
import pandas as pd
import os 
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

class WhoopFast:
    """
    Fast Whoop client that makes single API requests (no pagination)
    Gets up to 25 records per request for rapid testing/development
    """

    # Set up logging
    logging.basicConfig(
        filename="whoops_fast_log.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

    ENDPOINTS = {
        "recovery": "https://api.prod.whoop.com/developer/v2/recovery",
        "sleep": "https://api.prod.whoop.com/developer/v2/activity/sleep",
        "workout": "https://api.prod.whoop.com/developer/v2/activity/workout",
        "strain": "https://api.prod.whoop.com/developer/v2/cycle",
        "body": "https://api.prod.whoop.com/developer/v2/user/measurement/body"
    }

    def __init__(self, 
                 client_id: str=None, 
                 client_secret: str=None,
                 username: str=None,
                 password: str=None
                 ):
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.username = username or os.getenv("USERNAME")
        self.password = password or os.getenv("PASSWORD")
        
        # Try OAuth 2.0 first, fall back to legacy if needed
        if not self.client_id or not self.client_secret:
            if not self.username or not self.password:
                raise ValueError("Either (Client ID and Client Secret) OR (Username and Password) must be provided")
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_file = ".whoop_tokens.json"  # Reuse same token file as main client
        self.logger = logging.getLogger(__name__)

    @property
    def available_endpoints(self):
        return list(self.ENDPOINTS.keys())

    def get_endpoint_url(self, endpoint_name: str) -> str:
        """Returns the full URL for a given endpoint name."""
        return self.ENDPOINTS.get(
            endpoint_name, f"'{endpoint_name}' not found in endpoints."
        )

    def _load_tokens(self):
        """Load saved tokens from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token')
                    expires_str = token_data.get('expires_at')
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
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None
            }
            with open(self.token_file, 'w') as f:
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
            "client_secret": self.client_secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
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
                print("⚡ Access token refreshed")
                return True
        except Exception as e:
            self.logger.warning(f"Failed to refresh token: {e}")
        return False
    
    def authenticate(self):
        """Authenticate using existing tokens (no new OAuth flow for fast client)"""
        print("⚡ Fast client - checking for existing tokens...")
        
        # Load existing tokens
        if self._load_tokens():
            if self._is_token_valid():
                print("⚡ Using existing access token")
                return
            elif self.refresh_token and self._refresh_access_token():
                return
            else:
                print("❌ Existing tokens expired and cannot refresh")
                print("💡 Please run the main whoop_client.py to re-authenticate first")
                raise Exception("No valid tokens available. Please authenticate with the main client first.")
        else:
            print("❌ No tokens found")
            print("💡 Please run the main whoop_client.py to authenticate first")
            raise Exception("No tokens found. Please authenticate with the main client first.")

    def _flatten_nested_dict(self, data: dict, parent_key: str = '', sep: str = '.') -> dict:
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
        
        print(f"⚡ Transforming {len(records)} {endpoint_type} records for database compatibility...")
        
        transformed_records = []
        for record in records:
            # Flatten nested structures
            flat_record = self._flatten_nested_dict(record)
            transformed_records.append(flat_record)
        
        df = pd.DataFrame(transformed_records)
        
        # Apply endpoint-specific transformations
        if 'recovery' in endpoint_type.lower():
            df = self._transform_recovery_fields(df)
        elif 'sleep' in endpoint_type.lower():
            df = self._transform_sleep_fields(df)
        elif 'workout' in endpoint_type.lower():
            df = self._transform_workout_fields(df)
        
        print(f"⚡ Transformation complete. Available fields: {list(df.columns)}")
        return df
    
    def _transform_recovery_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform recovery data fields to match database schema"""
        # Rename nested score fields to match database
        rename_map = {
            'score.user_calibrating': 'user_calibrating',
            'score.recovery_score': 'recovery_score', 
            'score.resting_heart_rate': 'resting_heart_rate',
            'score.hrv_rmssd_milli': 'hrv_rmssd_milli',
            'score.spo2_percentage': 'spo2_percentage',
            'score.skin_temp_celsius': 'skin_temp_celsius'
        }
        return df.rename(columns=rename_map)
    
    def _transform_sleep_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform sleep data fields to match database schema"""
        rename_map = {
            # Main score fields
            'score.respiratory_rate': 'respiratory_rate',
            'score.sleep_performance_percentage': 'sleep_performance_percentage',
            'score.sleep_consistency_percentage': 'sleep_consistency_percentage', 
            'score.sleep_efficiency_percentage': 'sleep_efficiency_percentage',
            
            # Stage summary fields
            'score.stage_summary.total_in_bed_time_milli': 'total_time_in_bed_time_milli',
            'score.stage_summary.total_awake_time_milli': 'total_awake_time_milli',
            'score.stage_summary.total_no_data_time_milli': 'total_no_data_time_milli',
            'score.stage_summary.total_slow_wave_sleep_time_milli': 'total_slow_wave_sleep_time_milli',
            'score.stage_summary.total_rem_sleep_time_milli': 'total_rem_sleep_time_milli',
            'score.stage_summary.sleep_cycle_count': 'sleep_cycle_count',
            'score.stage_summary.disturbance_count': 'disturbance_count',
            
            # Sleep needed fields
            'score.sleep_needed.baseline_milli': 'baseline_sleep_needed_milli',
            'score.sleep_needed.need_from_sleep_debt_milli': 'need_from_sleep_debt_milli',
            'score.sleep_needed.need_from_recent_strain_milli': 'need_from_recent_strain_milli',
            'score.sleep_needed.need_from_recent_nap_milli': 'need_from_recent_nap_milli'
        }
        return df.rename(columns=rename_map)
    
    def _transform_workout_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform workout data fields to match database schema"""
        rename_map = {
            # Main score fields
            'score.strain': 'strain',
            'score.average_heart_rate': 'average_heart_rate',
            'score.max_heart_rate': 'max_heart_rate',
            'score.kilojoule': 'kilojoule',
            'score.percent_recorded': 'percent_recorded',
            'score.distance_meter': 'distance_meter',
            'score.altitude_gain_meter': 'altitude_gain_meter',
            'score.altitude_change_meter': 'altitude_change_meter',
            
            # Zone duration fields (convert from milliseconds to minutes)
            'score.zone_durations.zone_zero_milli': 'zone_zero_minutes',
            'score.zone_durations.zone_one_milli': 'zone_one_minutes',
            'score.zone_durations.zone_two_milli': 'zone_two_minutes',
            'score.zone_durations.zone_three_milli': 'zone_three_minutes', 
            'score.zone_durations.zone_four_milli': 'zone_four_minutes',
            'score.zone_durations.zone_five_milli': 'zone_five_minutes'
        }
        
        df = df.rename(columns=rename_map)
        
        # Convert zone durations from milliseconds to minutes
        zone_columns = [col for col in df.columns if col.endswith('_minutes')]
        for col in zone_columns:
            if col in df.columns:
                df[col] = df[col] / 60000.0  # Convert ms to minutes
        
        return df

    def make_single_request(self, data_endpoint: str, transform_for_db: bool = True, limit: int = 25):
        """
        Make a single API request (no pagination) for fast results
        Gets up to 'limit' records (default 25)
        """
        if not self.access_token:
            raise Exception("Authenticate before making API requests")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.logger.info(f"⚡ Making fast single request to {data_endpoint}")
        print(f"⚡ Making fast single request to {data_endpoint} (limit: {limit})")

        self.data_endpoint = data_endpoint
        
        # Add limit parameter to request only specified number of records
        params = {"limit": limit}
        
        raw_response = requests.get(
            self.data_endpoint, headers=headers, params=params
        )
        
        # Handle rate limiting
        if raw_response.status_code == 429:
            reset_time = int(raw_response.headers.get('X-RateLimit-Reset', 60))
            print(f"⚠️ Rate limit exceeded. Waiting {reset_time} seconds before retrying...")
            import time
            time.sleep(reset_time + 1)  # Add 1 extra second buffer
            print("🔄 Retrying request after rate limit reset...")
            raw_response = requests.get(
                self.data_endpoint, headers=headers, params=params
            )
        
        # Debug information for other errors
        if raw_response.status_code != 200:
            print(f"❌ API request failed: {raw_response.status_code}")
            print(f"Response headers: {dict(raw_response.headers)}")
            print(f"Response text: {raw_response.text[:500]}...")  # First 500 chars
            raise Exception(f"API request failed with status {raw_response.status_code}: {raw_response.text}")
        
        try:
            response = raw_response.json()
        except Exception as e:
            print(f"❌ JSON decode failed. Status code: {raw_response.status_code}")
            print(f"Response headers: {dict(raw_response.headers)}")
            print(f"Response content: {raw_response.text[:1000]}...")  # First 1000 chars
            raise Exception(f"Failed to parse JSON response: {e}")
        
        response_data = response.get("records", [])
        
        self.logger.info(f"⚡ Retrieved {len(response_data)} records (single request)")
        print(f"⚡ Retrieved {len(response_data)} records (single request)")
        
        # Show pagination info if available
        if "next_token" in response and response["next_token"]:
            print(f"💡 More data available - next_token: {response['next_token'][:20]}...")
            print("💡 Use the full whoop_client.py for complete pagination")

        # Transform data for database compatibility if requested
        if transform_for_db and response_data:
            # Extract endpoint type, handling trailing slashes
            endpoint_parts = data_endpoint.rstrip('/').split('/')
            endpoint_type = endpoint_parts[-1] if endpoint_parts else ''
            print(f"⚡ Detected endpoint type: '{endpoint_type}'")
            return self._transform_for_database(response_data, endpoint_type)
        else:
            # Return raw data as DataFrame
            return pd.json_normalize(response_data)

    def get_recovery_fast(self, limit: int = 25, transform: bool = True):
        """Get recovery data with single request"""
        return self.make_single_request(self.ENDPOINTS["recovery"], transform_for_db=transform, limit=limit)
    
    def get_sleep_fast(self, limit: int = 25, transform: bool = True):
        """Get sleep data with single request"""
        return self.make_single_request(self.ENDPOINTS["sleep"], transform_for_db=transform, limit=limit)
    
    def get_workout_fast(self, limit: int = 25, transform: bool = True):
        """Get workout data with single request"""
        return self.make_single_request(self.ENDPOINTS["workout"], transform_for_db=transform, limit=limit)
    
    def get_strain_fast(self, limit: int = 25, transform: bool = True):
        """Get strain/cycle data with single request"""
        return self.make_single_request(self.ENDPOINTS["strain"], transform_for_db=transform, limit=limit)
    
    def get_body_fast(self, limit: int = 25, transform: bool = True):
        """Get body measurement data with single request"""
        return self.make_single_request(self.ENDPOINTS["body"], transform_for_db=transform, limit=limit)