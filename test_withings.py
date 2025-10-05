#!/usr/bin/env python3
"""
Test script for Withings authentication and data retrieval
Run this to test the Withings integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.withings_client import WithingsClient
import json

def main():
    print("🏥 Testing Withings Integration")
    print("=" * 50)
    
    try:
        # Initialize client
        print("1. Initializing Withings client...")
        client = WithingsClient()
        
        # Authenticate
        print("2. Authenticating with Withings...")
        client.authenticate()
        
        # Get body measurements
        print("3. Fetching body measurements...")
        response = client.get_body_measurements()
        
        print(f"✅ Success! Status: {response.get('status')}")
        
        # Check if we got data
        body = response.get('body', {})
        measuregrps = body.get('measuregrps', [])
        
        print(f"📊 Retrieved {len(measuregrps)} measurement groups")
        
        if measuregrps:
            print("\n📋 Sample measurement group:")
            sample = measuregrps[0]
            print(f"   Group ID: {sample.get('grpid')}")
            print(f"   Date: {sample.get('date')}")
            print(f"   Measures: {len(sample.get('measures', []))}")
            
            # Show first measure
            measures = sample.get('measures', [])
            if measures:
                first_measure = measures[0]
                measure_type = first_measure.get('type')
                value = first_measure.get('value')
                unit = first_measure.get('unit', 0)
                actual_value = value * (10 ** unit)
                
                measurement_names = {
                    1: "Weight (kg)",
                    4: "Height (m)",
                    5: "Fat Free Mass (kg)",
                    6: "Fat Ratio (%)",
                    8: "Fat Mass Weight (kg)"
                }
                
                measure_name = measurement_names.get(measure_type, f"Type {measure_type}")
                print(f"   First measure: {measure_name} = {actual_value}")
        
        # Test DataFrame transformation
        print("\n4. Testing DataFrame transformation...")
        df = client.transform_to_dataframe(response)
        print(f"✅ DataFrame created with {len(df)} rows and {len(df.columns)} columns")
        
        if not df.empty:
            print("\n📊 DataFrame info:")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Measurement types: {df['measure_type_name'].unique().tolist()}")
            
            # Show latest measurements
            latest_by_type = df.groupby('measure_type_name')['datetime'].max()
            print(f"\n🕒 Latest measurements by type:")
            for measure_type, latest_date in latest_by_type.items():
                latest_row = df[(df['measure_type_name'] == measure_type) & (df['datetime'] == latest_date)]
                if not latest_row.empty:
                    value = latest_row.iloc[0]['actual_value']
                    print(f"   {measure_type}: {value} (on {latest_date.strftime('%Y-%m-%d %H:%M')})")
        
        print("\n✅ All tests passed! Withings integration is working.")
        
        # Test simple client
        print("\n5. Testing simple client...")
        from analysis.withings_simple import get_body_measurements
        simple_response = get_body_measurements()
        print(f"✅ Simple client works! Status: {simple_response.get('status')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())