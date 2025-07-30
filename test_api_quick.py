#!/usr/bin/env python3
"""
Quick API test script for EZREC backend
"""

import requests
import time
import sys

def test_api_status():
    """Test the API status endpoint"""
    try:
        print("🧪 Testing API status...")
        response = requests.get("http://localhost:8000/status", timeout=5)
        if response.status_code == 200:
            print("✅ API status endpoint working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ API status failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API server not running (Connection refused)")
        return False
    except Exception as e:
        print(f"❌ API status error: {e}")
        return False

def test_simple_booking():
    """Test creating a simple booking"""
    try:
        print("🧪 Testing booking creation...")
        booking = {
            "id": "test_quick_123",
            "user_id": "test_user",
            "camera_id": "test_camera",
            "start_time": "2024-01-15T10:00:00",
            "end_time": "2024-01-15T10:02:00",
            "status": "STARTED"
        }
        
        response = requests.post(
            "http://localhost:8000/bookings",
            json=booking,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Booking creation working")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Booking creation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Booking creation error: {e}")
        return False

def check_service_status():
    """Check if services are running"""
    import subprocess
    
    services = ["dual_recorder.service", "video_worker.service", "ezrec-api.service"]
    
    print("🔍 Checking service status...")
    for service in services:
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5
            )
            status = result.stdout.strip()
            if status == "active":
                print(f"✅ {service}: {status}")
            else:
                print(f"❌ {service}: {status}")
        except Exception as e:
            print(f"❌ {service}: error checking status - {e}")

def main():
    """Run quick tests"""
    print("🚀 EZREC Quick API Test")
    print("=======================")
    print()
    
    # Check service status first
    check_service_status()
    print()
    
    # Wait a moment for services to start
    print("⏳ Waiting 10 seconds for services to start...")
    time.sleep(10)
    
    # Test API
    tests = [
        ("API Status", test_api_status),
        ("Booking Creation", test_simple_booking),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("📊 Quick Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All quick tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed")
        print("\n🔧 Troubleshooting:")
        print("1. Check service status: sudo systemctl status ezrec-api.service")
        print("2. Check logs: sudo journalctl -u ezrec-api.service -f")
        print("3. Restart API: sudo systemctl restart ezrec-api.service")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 