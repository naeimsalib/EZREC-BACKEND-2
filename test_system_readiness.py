#!/usr/bin/env python3
"""
Simple system readiness test
- Checks basic dependencies
- Validates camera setup
- Tests API endpoints
- Provides clear pass/fail results
"""

import os
import sys
import subprocess
import json
import requests
from pathlib import Path

def test_command(command, description):
    """Test if a command is available"""
    try:
        result = subprocess.run([command, '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ {description}: Available")
            return True
        else:
            print(f"❌ {description}: Failed")
            return False
    except Exception as e:
        print(f"❌ {description}: Not found ({e})")
        return False

def test_camera_devices():
    """Test camera device availability"""
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            devices = [line for line in result.stdout.split('\n') if '/dev/video' in line]
            if len(devices) >= 2:
                print(f"✅ Camera devices: {len(devices)} found")
                return True
            else:
                print(f"❌ Camera devices: Only {len(devices)} found (need 2)")
                return False
        else:
            print("❌ Camera devices: v4l2-ctl failed")
            return False
    except Exception as e:
        print(f"❌ Camera devices: Error ({e})")
        return False

def test_api_endpoint():
    """Test API health endpoint"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            warnings = data.get('warnings', [])
            print(f"✅ API health: {status}")
            if warnings:
                print(f"⚠️ Warnings: {len(warnings)} issues")
            return status == 'healthy'
        else:
            print(f"❌ API health: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health: Connection failed ({e})")
        return False

def test_environment():
    """Test environment variables"""
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'USER_ID', 'CAMERA_ID']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Environment: Missing {missing}")
        return False
    else:
        print("✅ Environment: All required variables set")
        return True

def test_directories():
    """Test required directories"""
    required_dirs = [
        '/opt/ezrec-backend/logs',
        '/opt/ezrec-backend/recordings',
        '/opt/ezrec-backend/processed',
        '/opt/ezrec-backend/api/local_data'
    ]
    
    missing = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing.append(dir_path)
    
    if missing:
        print(f"❌ Directories: Missing {missing}")
        return False
    else:
        print("✅ Directories: All required directories exist")
        return True

def test_services():
    """Test systemd services"""
    services = ['dual_recorder', 'video_worker', 'ezrec-api']
    failed = []
    
    for service in services:
        try:
            result = subprocess.run(['systemctl', 'is-active', f'{service}.service'], 
                                  capture_output=True, text=True, timeout=5)
            status = result.stdout.strip()
            if status == 'active':
                print(f"✅ Service {service}: Active")
            else:
                print(f"❌ Service {service}: {status}")
                failed.append(service)
        except Exception as e:
            print(f"❌ Service {service}: Error ({e})")
            failed.append(service)
    
    return len(failed) == 0

def main():
    """Run all tests"""
    print("🔍 Running system readiness tests...")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment),
        ("Directories", test_directories),
        ("FFmpeg", lambda: test_command('ffmpeg', 'FFmpeg')),
        ("FFprobe", lambda: test_command('ffprobe', 'FFprobe')),
        ("v4l2-ctl", lambda: test_command('v4l2-ctl', 'v4l2-ctl')),
        ("Camera Devices", test_camera_devices),
        ("API Health", test_api_endpoint),
        ("System Services", test_services)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: Test error ({e})")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 System is ready for recording!")
        return True
    else:
        print("⚠️ System has issues that need to be fixed before recording.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 