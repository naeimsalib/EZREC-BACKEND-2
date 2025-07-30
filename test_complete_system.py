#!/usr/bin/env python3
"""
Complete EZREC System Test
Tests all components of the EZREC backend system
"""

import requests
import subprocess
import time
import sys
import os
from pathlib import Path

def test_system_requirements():
    """Test system requirements"""
    print("🔧 Testing System Requirements...")
    
    # Test Python
    try:
        import sys
        print(f"✅ Python version: {sys.version}")
    except Exception as e:
        print(f"❌ Python test failed: {e}")
        return False
    
    # Test FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
        else:
            print("❌ FFmpeg not working")
            return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False
    
    # Test v4l2-ctl
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ v4l2-ctl is available")
        else:
            print("❌ v4l2-ctl not working")
            return False
    except Exception as e:
        print(f"❌ v4l2-ctl test failed: {e}")
        return False
    
    return True

def test_virtual_environments():
    """Test virtual environments"""
    print("\n🐍 Testing Virtual Environments...")
    
    # Test API venv
    api_venv = Path("/opt/ezrec-backend/api/venv")
    if api_venv.exists():
        print("✅ API virtual environment exists")
        
        # Test Python imports in API venv
        try:
            result = subprocess.run([
                "/opt/ezrec-backend/api/venv/bin/python3", 
                "-c", 
                "import fastapi, uvicorn, supabase; print('✅ API venv imports working')"
            ], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ API venv imports successful")
            else:
                print(f"❌ API venv imports failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ API venv test failed: {e}")
            return False
    else:
        print("❌ API virtual environment missing")
        return False
    
    # Test backend venv
    backend_venv = Path("/opt/ezrec-backend/backend/venv")
    if backend_venv.exists():
        print("✅ Backend virtual environment exists")
        
        # Test Python imports in backend venv
        try:
            result = subprocess.run([
                "/opt/ezrec-backend/backend/venv/bin/python3", 
                "-c", 
                "import psutil, boto3, picamera2; print('✅ Backend venv imports working')"
            ], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Backend venv imports successful")
            else:
                print(f"❌ Backend venv imports failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Backend venv test failed: {e}")
            return False
    else:
        print("❌ Backend virtual environment missing")
        return False
    
    return True

def test_services():
    """Test systemd services"""
    print("\n🚀 Testing Services...")
    
    services = ["dual_recorder.service", "video_worker.service", "ezrec-api.service"]
    
    for service in services:
        try:
            result = subprocess.run(['sudo', 'systemctl', 'is-active', service], 
                                  capture_output=True, text=True, timeout=10)
            status = result.stdout.strip()
            if status == "active":
                print(f"✅ {service}: {status}")
            else:
                print(f"❌ {service}: {status}")
                return False
        except Exception as e:
            print(f"❌ {service}: error checking status - {e}")
            return False
    
    return True

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints...")
    
    # Wait for API to start
    print("⏳ Waiting for API to start...")
    time.sleep(10)
    
    # Test status endpoint
    try:
        response = requests.get("http://localhost:8000/status", timeout=10)
        if response.status_code == 200:
            print("✅ API status endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ API status failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API server not running (Connection refused)")
        return False
    except Exception as e:
        print(f"❌ API status error: {e}")
        return False
    
    # Test bookings endpoint
    try:
        response = requests.get("http://localhost:8000/bookings", timeout=10)
        if response.status_code == 200:
            print("✅ API bookings endpoint working")
        else:
            print(f"❌ API bookings failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API bookings error: {e}")
        return False
    
    return True

def test_directories():
    """Test required directories"""
    print("\n📁 Testing Directories...")
    
    required_dirs = [
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/processed",
        "/opt/ezrec-backend/final",
        "/opt/ezrec-backend/assets",
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/events",
        "/opt/ezrec-backend/api/local_data"
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} missing")
            return False
    
    return True

def test_assets():
    """Test required assets"""
    print("\n🎨 Testing Assets...")
    
    required_assets = [
        "/opt/ezrec-backend/assets/sponsor.png",
        "/opt/ezrec-backend/assets/company.png",
        "/opt/ezrec-backend/assets/intro.mp4"
    ]
    
    for asset_path in required_assets:
        if Path(asset_path).exists():
            print(f"✅ {asset_path}")
        else:
            print(f"❌ {asset_path} missing")
            return False
    
    return True

def test_camera_detection():
    """Test camera detection"""
    print("\n📹 Testing Camera Detection...")
    
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            devices = result.stdout
            if "video" in devices.lower():
                print("✅ Camera devices detected")
                # Count video devices
                video_count = devices.count("video")
                print(f"   Found {video_count} video device(s)")
            else:
                print("❌ No camera devices found")
                return False
        else:
            print("❌ Camera detection failed")
            return False
    except Exception as e:
        print(f"❌ Camera detection error: {e}")
        return False
    
    return True

def test_booking_creation():
    """Test booking creation"""
    print("\n📝 Testing Booking Creation...")
    
    try:
        booking = {
            "id": "test_complete_123",
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
        else:
            print(f"❌ Booking creation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Booking creation error: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 EZREC Complete System Test")
    print("==============================")
    print()
    
    tests = [
        ("System Requirements", test_system_requirements),
        ("Virtual Environments", test_virtual_environments),
        ("Services", test_services),
        ("API Endpoints", test_api_endpoints),
        ("Directories", test_directories),
        ("Assets", test_assets),
        ("Camera Detection", test_camera_detection),
        ("Booking Creation", test_booking_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed")
        print()
    
    print("📊 Complete Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! EZREC system is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for issues.")
        print("\n🔧 Troubleshooting:")
        print("1. Run: sudo ./fix_venv.sh")
        print("2. Check service logs: sudo journalctl -u ezrec-api.service -f")
        print("3. Restart services: sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 