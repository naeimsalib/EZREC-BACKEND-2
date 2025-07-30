#!/usr/bin/env python3
"""
Simple API test script for EZREC backend
"""

import requests
import json
from datetime import datetime, timedelta

def test_api_status():
    """Test the API status endpoint"""
    try:
        response = requests.get("http://localhost:8000/status")
        if response.status_code == 200:
            print("✅ API status endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ API status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API status error: {e}")
        return False

def test_single_booking():
    """Test creating a single booking"""
    try:
        # Create a test booking
        booking = {
            "id": "test_single_123",
            "user_id": "test_user",
            "camera_id": "test_camera",
            "start_time": "2024-01-15T10:00:00",
            "end_time": "2024-01-15T10:02:00",
            "status": "STARTED"
        }
        
        response = requests.post(
            "http://localhost:8000/bookings",
            json=booking,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Single booking creation working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Single booking failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Single booking error: {e}")
        return False

def test_list_bookings():
    """Test creating multiple bookings"""
    try:
        # Create test bookings
        bookings = [
            {
                "id": "test_list_1",
                "user_id": "test_user",
                "camera_id": "test_camera",
                "start_time": "2024-01-15T11:00:00",
                "end_time": "2024-01-15T11:02:00",
                "status": "STARTED"
            },
            {
                "id": "test_list_2",
                "user_id": "test_user",
                "camera_id": "test_camera",
                "start_time": "2024-01-15T12:00:00",
                "end_time": "2024-01-15T12:02:00",
                "status": "STARTED"
            }
        ]
        
        response = requests.post(
            "http://localhost:8000/bookings",
            json=bookings,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ List booking creation working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ List booking failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ List booking error: {e}")
        return False

def test_get_bookings():
    """Test getting all bookings"""
    try:
        response = requests.get("http://localhost:8000/bookings")
        if response.status_code == 200:
            bookings = response.json()
            print(f"✅ Get bookings working: {len(bookings)} bookings found")
            return True
        else:
            print(f"❌ Get bookings failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get bookings error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 EZREC API Test Suite")
    print("=======================")
    print()
    
    tests = [
        ("API Status", test_api_status),
        ("Single Booking", test_single_booking),
        ("List Bookings", test_list_bookings),
        ("Get Bookings", test_get_bookings),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🧪 Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("📊 Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")

if __name__ == "__main__":
    main() 