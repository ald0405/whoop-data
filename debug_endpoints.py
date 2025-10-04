#!/usr/bin/env python3
from analysis.whoop_client import Whoop

# Check what endpoints are being used
whoop = Whoop()

print("Available endpoints:")
for name in whoop.available_endpoints:
    url = whoop.get_endpoint_url(name)
    print(f"  {name}: {url}")

print("\nTesting endpoint URLs:")
import requests

whoop.authenticate()

for name in whoop.available_endpoints:
    url = whoop.get_endpoint_url(name)
    print(f"\nTesting {name}: {url}")
    
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {whoop.access_token}"})
        print(f"  Status: {response.status_code}")
        if response.status_code != 200:
            print(f"  Error: {response.text}")
        else:
            data = response.json()
            print(f"  Success: Found {len(data.get('records', []))} records")
    except Exception as e:
        print(f"  Exception: {e}")
