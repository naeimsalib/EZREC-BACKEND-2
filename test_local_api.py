#!/usr/bin/env python3
"""
Simple test script to verify local API endpoints are working
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Local API base URL
API_BASE = "http://localhost:9000"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        
        print(f"✅ {method} {endpoint}: {response.status_code}")
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
            except:
                print(f"   Response: {response.text}")
        else:
            print(f"   Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ {method} {endpoint}: {e}")
        return False

def create_test_booking():
    """Create a test booking"""
    start_time = (datetime.now() + timedelta(seconds=30)).isoformat()
    end_time = (datetime.now() + timedelta(seconds=90)).isoformat()
    
    booking_data = {
        "id": f"test-booking-{int(time.time())}",
        "user_id": f"test-user-{int(time.time())}",
        "start_time": start_time,
        "end_time": end_time,
        "status": "confirmed"
    }
    
    return test_endpoint("/bookings", "POST", booking_data)

def main():
    print("🧪 Testing Local EZREC API")
    print("=" * 40)
    
    # Test basic endpoints
    print("\n1. Testing Basic Endpoints:")
    test_endpoint("/test-alive")
    test_endpoint("/status")
    test_endpoint("/health")
    
    # Test booking endpoints
    print("\n2. Testing Booking Endpoints:")
    test_endpoint("/bookings")
    test_endpoint("/status/is_recording")
    test_endpoint("/status/next_booking")
    
    # Create a test booking
    print("\n3. Creating Test Booking:")
    if create_test_booking():
        print("✅ Test booking created successfully")
        
        # Monitor recording status
        print("\n4. Monitoring Recording Status (30 seconds):")
        for i in range(6):
            time.sleep(5)
            current_time = datetime.now().strftime("%H:%M:%S")
            is_recording = test_endpoint("/status/is_recording")
            print(f"   [{current_time}] Recording status checked")
    else:
        print("❌ Failed to create test booking")
    
    print("\n🎯 Local API Test Complete!")

if __name__ == "__main__":
    main() 