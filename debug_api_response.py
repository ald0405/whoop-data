#!/usr/bin/env python3
import json
import pandas as pd
import requests
from analysis.whoop_client import Whoop

def examine_api_response():
    """Examine the structure of data returned by the Whoop API"""
    
    print("🔍 Examining Whoop API Response Structure...\n")
    
    # Initialize and authenticate
    whoop = Whoop()
    whoop.authenticate()
    
    # Test different endpoints
    endpoints_to_test = {
        "recovery": "https://api.prod.whoop.com/developer/v1/recovery",
        "sleep": "https://api.prod.whoop.com/developer/v1/activity/sleep", 
        "workout": "https://api.prod.whoop.com/developer/v1/activity/workout",
        "strain": "https://api.prod.whoop.com/developer/v1/cycle"
    }
    
    for endpoint_name, endpoint_url in endpoints_to_test.items():
        print(f"\n{'='*50}")
        print(f"📊 EXAMINING {endpoint_name.upper()} ENDPOINT")
        print(f"{'='*50}")
        print(f"URL: {endpoint_url}")
        
        try:
            # Get just first page of data to examine structure
            headers = {"Authorization": f"Bearer {whoop.access_token}"}
            response = requests.get(endpoint_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n✅ Status: {response.status_code}")
                print(f"📄 Response Keys: {list(data.keys())}")
                
                if "records" in data and len(data["records"]) > 0:
                    print(f"📊 Total Records Available: {len(data['records'])}")
                    
                    # Examine first record
                    first_record = data["records"][0]
                    print(f"\n🔍 FIRST RECORD STRUCTURE:")
                    print(f"📝 Fields: {list(first_record.keys())}")
                    
                    # Pretty print first record with indentation
                    print(f"\n📋 SAMPLE RECORD ({endpoint_name}):")
                    print(json.dumps(first_record, indent=2, default=str))
                    
                    # If there are nested objects, examine them
                    for key, value in first_record.items():
                        if isinstance(value, dict):
                            print(f"\n🔗 NESTED OBJECT '{key}':")
                            print(f"   Fields: {list(value.keys())}")
                            for nested_key, nested_value in value.items():
                                print(f"   {nested_key}: {type(nested_value).__name__} = {nested_value}")
                else:
                    print("❌ No records found in response")
                    
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception occurred: {e}")
    
    print(f"\n{'='*50}")
    print("✅ EXAMINATION COMPLETE")
    print(f"{'='*50}")

if __name__ == "__main__":
    examine_api_response()
