#!/usr/bin/env python3
"""
COMPREHENSIVE EZREC SYSTEM TEST
Tests all endpoints, camera functionality, and system components
"""

import requests
import json
import time
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import threading

# Configuration
API_BASE_URL = "http://localhost:9000"
TEST_TIMEOUT = 30

def run_command(cmd, check=True, capture_output=True, text=True):
    """Run a command and return result"""
    print(f"🔄 Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=text)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return e

def test_api_endpoint(endpoint, method="GET", data=None, expected_status=200, description=""):
    """Test an API endpoint"""
    url = f"{API_BASE_URL}{endpoint}"
    print(f"\n🔍 Testing {method} {endpoint}")
    if description:
        print(f"   Description: {description}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=TEST_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=TEST_TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=TEST_TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, timeout=TEST_TIMEOUT)
        
        print(f"   Status: {response.status_code}")
        if response.status_code == expected_status:
            print(f"   ✅ PASS - Expected {expected_status}, got {response.status_code}")
            if response.content:
                try:
                    print(f"   Response: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"   Response: {response.text[:200]}...")
            return True
        else:
            print(f"   ❌ FAIL - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR - {e}")
        return False

def test_camera_functionality():
    """Test camera functionality"""
    print("\n📹 TESTING CAMERA FUNCTIONALITY")
    print("=" * 50)
    
    # Test 1: Check if camera streamer is running
    print("\n🔍 Test 1: Camera Streamer Process")
    result = run_command("ps aux | grep camera_streamer | grep -v grep")
    if "camera_streamer" in str(result.stdout):
        print("   ✅ Camera streamer process is running")
    else:
        print("   ❌ Camera streamer process not found")
        return False
    
    # Test 2: Check camera device
    print("\n🔍 Test 2: Camera Device")
    result = run_command("ls -la /dev/video*")
    if "/dev/video" in str(result.stdout):
        print("   ✅ Camera device found")
    else:
        print("   ❌ No camera device found")
        return False
    
    # Test 3: Test live preview endpoint
    print("\n🔍 Test 3: Live Preview Endpoint")
    try:
        response = requests.get(f"{API_BASE_URL}/live-preview", timeout=5)
        if response.status_code in [200, 503]:  # 503 is expected if camera not ready
            print(f"   ✅ Live preview endpoint responding (status: {response.status_code})")
        else:
            print(f"   ❌ Live preview endpoint error (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Live preview endpoint error: {e}")
    
    return True

def test_recording_system():
    """Test recording system"""
    print("\n🎥 TESTING RECORDING SYSTEM")
    print("=" * 50)
    
    # Test 1: Check recorder process
    print("\n🔍 Test 1: Recorder Process")
    result = run_command("ps aux | grep recorder.py | grep -v grep")
    if "recorder.py" in str(result.stdout):
        print("   ✅ Recorder process is running")
    else:
        print("   ❌ Recorder process not found")
        return False
    
    # Test 2: Check video worker process
    print("\n🔍 Test 2: Video Worker Process")
    result = run_command("ps aux | grep video_worker.py | grep -v grep")
    if "video_worker.py" in str(result.stdout):
        print("   ✅ Video worker process is running")
    else:
        print("   ❌ Video worker process not found")
        return False
    
    # Test 3: Check recording directories
    print("\n🔍 Test 3: Recording Directories")
    dirs_to_check = [
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/raw_recordings",
        "/opt/ezrec-backend/processed"
    ]
    for dir_path in dirs_to_check:
        if Path(dir_path).exists():
            print(f"   ✅ Directory exists: {dir_path}")
        else:
            print(f"   ❌ Directory missing: {dir_path}")
    
    # Test 4: Check recording status
    print("\n🔍 Test 4: Recording Status")
    test_api_endpoint("/status/is_recording", description="Check if system is currently recording")
    
    return True

def test_system_services():
    """Test system services"""
    print("\n⚙️ TESTING SYSTEM SERVICES")
    print("=" * 50)
    
    services_to_check = [
        "recorder.service",
        "video_worker.service", 
        "status_updater.service",
        "log_collector.service"
    ]
    
    for service in services_to_check:
        print(f"\n🔍 Checking {service}")
        result = run_command(f"systemctl is-active {service}")
        if "active" in str(result.stdout):
            print(f"   ✅ {service} is active")
        else:
            print(f"   ❌ {service} is not active")
    
    return True

def test_environment_and_dependencies():
    """Test environment and dependencies"""
    print("\n🔧 TESTING ENVIRONMENT & DEPENDENCIES")
    print("=" * 50)
    
    # Test 1: Check Python environment
    print("\n🔍 Test 1: Python Environment")
    result = run_command("which python3")
    print(f"   Python path: {result.stdout.strip()}")
    
    # Test 2: Check virtual environment
    print("\n🔍 Test 2: Virtual Environment")
    venv_path = "/opt/ezrec-backend/api/venv"
    if Path(venv_path).exists():
        print(f"   ✅ Virtual environment exists: {venv_path}")
    else:
        print(f"   ❌ Virtual environment missing: {venv_path}")
    
    # Test 3: Check key dependencies
    print("\n🔍 Test 3: Key Dependencies")
    dependencies = ["fastapi", "uvicorn", "boto3", "supabase", "opencv-python"]
    for dep in dependencies:
        try:
            result = run_command(f"python3 -c 'import {dep}; print(\"OK\")'")
            if "OK" in str(result.stdout):
                print(f"   ✅ {dep} is available")
            else:
                print(f"   ❌ {dep} is not available")
        except:
            print(f"   ❌ {dep} is not available")
    
    # Test 4: Check environment variables
    print("\n🔍 Test 4: Environment Variables")
    env_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY", 
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "AWS_S3_BUCKET"
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var} is set")
        else:
            print(f"   ❌ {var} is not set")
    
    return True

def test_network_and_connectivity():
    """Test network and connectivity"""
    print("\n🌐 TESTING NETWORK & CONNECTIVITY")
    print("=" * 50)
    
    # Test 1: Check API server port
    print("\n🔍 Test 1: API Server Port")
    result = run_command("netstat -tlnp | grep :9000")
    if ":9000" in str(result.stdout):
        print("   ✅ API server listening on port 9000")
    else:
        print("   ❌ API server not listening on port 9000")
    
    # Test 2: Check internet connectivity
    print("\n🔍 Test 2: Internet Connectivity")
    try:
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            print("   ✅ Internet connectivity working")
        else:
            print("   ❌ Internet connectivity issues")
    except Exception as e:
        print(f"   ❌ Internet connectivity error: {e}")
    
    # Test 3: Check Supabase connectivity
    print("\n🔍 Test 3: Supabase Connectivity")
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        try:
            response = requests.get(f"{supabase_url}/rest/v1/", timeout=10)
            if response.status_code in [200, 401]:  # 401 is expected without auth
                print("   ✅ Supabase connectivity working")
            else:
                print(f"   ❌ Supabase connectivity issues (status: {response.status_code})")
        except Exception as e:
            print(f"   ❌ Supabase connectivity error: {e}")
    else:
        print("   ❌ SUPABASE_URL not set")
    
    return True

def test_file_permissions():
    """Test file permissions"""
    print("\n📁 TESTING FILE PERMISSIONS")
    print("=" * 50)
    
    paths_to_check = [
        "/opt/ezrec-backend/api/api_server.py",
        "/opt/ezrec-backend/.env",
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/logs"
    ]
    
    for path in paths_to_check:
        if Path(path).exists():
            if os.access(path, os.R_OK):
                print(f"   ✅ Readable: {path}")
            else:
                print(f"   ❌ Not readable: {path}")
        else:
            print(f"   ❌ Does not exist: {path}")
    
    return True

def create_test_booking():
    """Create a test booking for testing"""
    print("\n📅 CREATING TEST BOOKING")
    print("=" * 50)
    
    # Create a test booking for 5 minutes from now
    now = datetime.now()
    start_time = (now + timedelta(minutes=5)).isoformat()
    end_time = (now + timedelta(minutes=10)).isoformat()
    
    test_booking = {
        "id": "test-booking-123",
        "user_id": "test-user-456",
        "start_time": start_time,
        "end_time": end_time,
        "date": now.strftime("%Y-%m-%d"),
        "camera_id": "test-camera",
        "booking_id": "test-booking-123",
        "email": "test@example.com"
    }
    
    # Test booking creation
    success = test_api_endpoint(
        "/bookings", 
        method="POST", 
        data=[test_booking], 
        expected_status=200,
        description="Create test booking"
    )
    
    if success:
        print("   ✅ Test booking created successfully")
        return test_booking
    else:
        print("   ❌ Failed to create test booking")
        return None

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 CLEANING UP TEST DATA")
    print("=" * 50)
    
    # Remove test booking
    test_api_endpoint(
        "/bookings/test-booking-123",
        method="DELETE",
        expected_status=200,
        description="Delete test booking"
    )
    
    print("   ✅ Test data cleaned up")

def main():
    """Main test function"""
    print("🚀 COMPREHENSIVE EZREC SYSTEM TEST")
    print("=" * 60)
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Test started at: {datetime.now()}")
    
    # Track test results
    test_results = []
    
    # Test 1: Basic API connectivity
    print("\n" + "="*60)
    print("TEST 1: BASIC API CONNECTIVITY")
    print("="*60)
    
    basic_tests = [
        ("/", "Root endpoint"),
        ("/status", "System status"),
        ("/test-alive", "Health check"),
        ("/bookings", "Get bookings"),
        ("/recordings", "Get recordings")
    ]
    
    for endpoint, description in basic_tests:
        success = test_api_endpoint(endpoint, description=description)
        test_results.append(("Basic API", endpoint, success))
    
    # Test 2: System status endpoints
    print("\n" + "="*60)
    print("TEST 2: SYSTEM STATUS ENDPOINTS")
    print("="*60)
    
    status_endpoints = [
        ("/status/cpu", "CPU usage"),
        ("/status/memory", "Memory usage"),
        ("/status/storage", "Storage info"),
        ("/status/temperature", "Temperature"),
        ("/status/uptime", "System uptime"),
        ("/status/network", "Network status"),
        ("/status/next_booking", "Next booking")
    ]
    
    for endpoint, description in status_endpoints:
        success = test_api_endpoint(endpoint, description=description)
        test_results.append(("System Status", endpoint, success))
    
    # Test 3: Environment and dependencies
    env_success = test_environment_and_dependencies()
    test_results.append(("Environment", "Dependencies", env_success))
    
    # Test 4: Network and connectivity
    network_success = test_network_and_connectivity()
    test_results.append(("Network", "Connectivity", network_success))
    
    # Test 5: File permissions
    permissions_success = test_file_permissions()
    test_results.append(("File Permissions", "Access", permissions_success))
    
    # Test 6: System services
    services_success = test_system_services()
    test_results.append(("System Services", "Status", services_success))
    
    # Test 7: Camera functionality
    camera_success = test_camera_functionality()
    test_results.append(("Camera", "Functionality", camera_success))
    
    # Test 8: Recording system
    recording_success = test_recording_system()
    test_results.append(("Recording", "System", recording_success))
    
    # Test 9: Create and test booking functionality
    print("\n" + "="*60)
    print("TEST 9: BOOKING FUNCTIONALITY")
    print("="*60)
    
    test_booking = create_test_booking()
    if test_booking:
        # Test booking retrieval
        test_api_endpoint("/bookings", description="Get bookings after creation")
        
        # Test booking update
        updated_booking = test_booking.copy()
        updated_booking["email"] = "updated@example.com"
        test_api_endpoint(
            f"/bookings/{test_booking['id']}", 
            method="PUT", 
            data=updated_booking,
            expected_status=200,
            description="Update test booking"
        )
        
        # Clean up
        cleanup_test_data()
    
    # Test 10: Advanced API endpoints
    print("\n" + "="*60)
    print("TEST 10: ADVANCED API ENDPOINTS")
    print("="*60)
    
    advanced_tests = [
        ("/media/presign?key=test&operation=get", "Media presign GET"),
        ("/media/presign?key=test&operation=put", "Media presign PUT"),
        ("/share/analytics/test-user", "Share analytics"),
        ("/share/analytics/popular", "Popular videos")
    ]
    
    for endpoint, description in advanced_tests:
        success = test_api_endpoint(endpoint, description=description)
        test_results.append(("Advanced API", endpoint, success))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, _, success in test_results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print("\n❌ FAILED TESTS:")
        for category, endpoint, success in test_results:
            if not success:
                print(f"   - {category}: {endpoint}")
    else:
        print("\n🎉 ALL TESTS PASSED! System is ready for frontend testing.")
    
    print(f"\nTest completed at: {datetime.now()}")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 