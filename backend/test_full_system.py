#!/usr/bin/env python3
"""
EZREC Full System Test Suite
Comprehensive test of all system components
"""

import os
import sys
import time
import requests
import cv2
import subprocess
import json
from pathlib import Path

def check_systemd_services():
    """Check if all systemd services are running"""
    print("🧪 Checking systemd services:")
    
    services = [
        'camera_streamer',
        'recorder', 
        'video_worker',
        'ezrec-api',
        'cloudflared',
        'status_updater',
        'health_api',
        'log_collector'
    ]
    
    results = {}
    for service in services:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', '--quiet', f'{service}.service'],
                capture_output=True,
                timeout=5
            )
            status = '✅ running' if result.returncode == 0 else '❌ not running'
            results[service] = result.returncode == 0
            print(f" - {service}: {status}")
        except Exception as e:
            print(f" - {service}: ❌ error checking ({e})")
            results[service] = False
    
    return results

def test_fastapi_endpoints():
    """Test FastAPI endpoints"""
    print("\n🌐 FastAPI Status Check:")
    
    endpoints = [
        ("http://localhost:9000/test-alive", "Test Alive"),
        ("http://localhost:9000/status", "Status"),
        ("http://localhost:9000/bookings", "Bookings"),
        ("http://localhost:9000/camera-status", "Camera Status"),
        ("http://localhost:9000/live-preview", "Live Preview")
    ]
    
    results = {}
    for url, name in endpoints:
        try:
            r = requests.get(url, timeout=5)
            status = f"✅ {r.status_code}"
            results[name] = r.status_code < 500
            print(f" - {name}: {status}")
        except requests.exceptions.ConnectionError:
            print(f" - {name}: ❌ connection failed")
            results[name] = False
        except Exception as e:
            print(f" - {name}: ❌ error ({e})")
            results[name] = False
    
    return results

def test_opencv_camera():
    """Test OpenCV camera access"""
    print("\n🎬 OpenCV Camera Test:")
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ OpenCV could not open camera")
            return False
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ Camera detected: {width}x{height} @ {fps:.1f}fps")
        
        # Test frame capture
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✅ Frame capture successful: {frame.shape}")
            cap.release()
            return True
        else:
            print("❌ Frame capture failed")
            cap.release()
            return False
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_file_permissions():
    """Test file permissions for key directories"""
    print("\n📁 File Permissions Test:")
    
    paths_to_check = [
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/recordings", 
        "/opt/ezrec-backend/processed",
        "/opt/ezrec-backend/media_cache",
        "/opt/ezrec-backend/api/local_data"
    ]
    
    results = {}
    for path in paths_to_check:
        try:
            p = Path(path)
            if p.exists():
                # Check if writable
                test_file = p / "test_write.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    status = "✅ writable"
                    results[path] = True
                except Exception:
                    status = "❌ not writable"
                    results[path] = False
            else:
                status = "❌ does not exist"
                results[path] = False
            print(f" - {path}: {status}")
        except Exception as e:
            print(f" - {path}: ❌ error ({e})")
            results[path] = False
    
    return results

def test_cloudflare_tunnel():
    """Test Cloudflare tunnel connectivity"""
    print("\n🌐 Cloudflare Tunnel Test:")
    
    try:
        # Check if tunnel is running
        result = subprocess.run(
            ['systemctl', 'is-active', '--quiet', 'cloudflared.service'],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Cloudflare tunnel service is running")
            
            # Test external connectivity
            try:
                r = requests.get("https://api.ezrec.org/test-alive", timeout=10)
                if r.status_code == 200:
                    print("✅ External API accessible via tunnel")
                    return True
                else:
                    print(f"⚠️ External API returned {r.status_code}")
                    return False
            except Exception as e:
                print(f"❌ External API test failed: {e}")
                return False
        else:
            print("❌ Cloudflare tunnel service not running")
            return False
            
    except Exception as e:
        print(f"❌ Tunnel test failed: {e}")
        return False

def test_environment_variables():
    """Test if required environment variables are set"""
    print("\n🔧 Environment Variables Test:")
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY", 
        "USER_ID",
        "CAMERA_ID",
        "AWS_REGION",
        "AWS_S3_BUCKET",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    results = {}
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f" - {var}: ✅ {display_value}")
            results[var] = True
        else:
            print(f" - {var}: ❌ not set")
            results[var] = False
    
    return results

def generate_report(service_results, api_results, camera_ok, file_results, tunnel_ok, env_results):
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE SYSTEM TEST REPORT")
    print("="*60)
    
    # Service status
    running_services = sum(service_results.values())
    total_services = len(service_results)
    print(f"\n🔧 Services: {running_services}/{total_services} running")
    
    # API endpoints
    working_apis = sum(api_results.values())
    total_apis = len(api_results)
    print(f"🌐 API Endpoints: {working_apis}/{total_apis} responding")
    
    # Camera
    print(f"📹 Camera: {'✅ Working' if camera_ok else '❌ Failed'}")
    
    # File permissions
    writable_paths = sum(file_results.values())
    total_paths = len(file_results)
    print(f"📁 File Permissions: {writable_paths}/{total_paths} writable")
    
    # Tunnel
    print(f"🌐 Cloudflare Tunnel: {'✅ Working' if tunnel_ok else '❌ Failed'}")
    
    # Environment
    set_vars = sum(env_results.values())
    total_vars = len(env_results)
    print(f"🔧 Environment Variables: {set_vars}/{total_vars} set")
    
    # Overall status
    total_tests = total_services + total_apis + 1 + total_paths + 1 + total_vars
    passed_tests = running_services + working_apis + (1 if camera_ok else 0) + writable_paths + (1 if tunnel_ok else 0) + set_vars
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! System is fully operational.")
        return True
    else:
        print(f"\n⚠️ {total_tests - passed_tests} tests failed. Check the output above for details.")
        return False

def main():
    """Main test function"""
    print("🚀 EZREC Full System Test Suite")
    print("="*60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run all tests
    service_results = check_systemd_services()
    api_results = test_fastapi_endpoints()
    camera_ok = test_opencv_camera()
    file_results = test_file_permissions()
    tunnel_ok = test_cloudflare_tunnel()
    env_results = test_environment_variables()
    
    # Generate report
    success = generate_report(
        service_results, api_results, camera_ok, 
        file_results, tunnel_ok, env_results
    )
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 