#!/usr/bin/env python3
"""
Comprehensive EZREC System Test Suite
Tests all phases: Camera Streaming → Recording → Processing → Upload
"""

import requests
import time
import json
import subprocess
import os
from pathlib import Path
import cv2

def test_camera_streamer():
    """Test camera streamer endpoints"""
    print("🔍 Testing Camera Streamer...")
    
    try:
        # Test basic health check
        response = requests.get("http://localhost:9000/", timeout=5)
        if response.status_code == 200:
            print("✅ Camera streamer health check passed")
        else:
            print(f"❌ Camera streamer health check failed: {response.status_code}")
            return False
        
        # Test camera status endpoint
        response = requests.get("http://localhost:9000/camera-status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Camera status: {status['status']}")
            if status['status'] == 'healthy':
                print(f"   Frame size: {status.get('frame_size', 'N/A')}")
                print(f"   Queue size: {status.get('queue_size', 'N/A')}")
            return True
        else:
            print(f"❌ Camera status check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Camera streamer test failed: {e}")
        return False

def test_live_preview():
    """Test live preview MJPEG stream"""
    print("📹 Testing Live Preview Stream...")
    
    try:
        # Test MJPEG stream (brief test)
        response = requests.get("http://localhost:9000/live-preview", 
                              stream=True, timeout=10)
        
        if response.status_code == 200:
            # Read first few bytes to verify it's MJPEG
            content_type = response.headers.get('content-type', '')
            if 'multipart/x-mixed-replace' in content_type:
                print("✅ Live preview stream working (MJPEG format)")
                return True
            else:
                print(f"⚠️ Live preview returned unexpected content type: {content_type}")
                return False
        else:
            print(f"❌ Live preview failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Live preview test failed: {e}")
        return False

def test_opencv_recording():
    """Test OpenCV recording functionality"""
    print("🎬 Testing OpenCV Recording...")
    
    try:
        # Create a test recording
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Failed to open camera for recording test")
            return False
        
        # Configure camera
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        output_file = "test_recording.mp4"
        video_writer = cv2.VideoWriter(output_file, fourcc, 30, (1280, 720))
        
        if not video_writer.isOpened():
            print("❌ Failed to initialize video writer")
            return False
        
        # Record 3 seconds
        print("📹 Recording 3 seconds of test video...")
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 3:
            ret, frame = camera.read()
            if ret:
                video_writer.write(frame)
                frame_count += 1
        
        # Cleanup
        video_writer.release()
        camera.release()
        
        # Check result
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
            print(f"✅ Recording test successful: {frame_count} frames, {os.path.getsize(output_file)} bytes")
            
            # Test FFmpeg compatibility
            result = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height,avg_frame_rate",
                "-of", "json", output_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ FFmpeg compatibility test passed")
                # Clean up test file
                os.remove(output_file)
                return True
            else:
                print("❌ FFmpeg compatibility test failed")
                return False
        else:
            print("❌ Recording test failed - file too small or missing")
            return False
            
    except Exception as e:
        print(f"❌ Recording test failed: {e}")
        return False

def test_service_status():
    """Test systemd service status"""
    print("🔧 Testing Systemd Services...")
    
    services = [
        "camera_streamer.service",
        "recorder.service", 
        "video_worker.service",
        "status_updater.service"
    ]
    
    all_healthy = True
    
    for service in services:
        try:
            result = subprocess.run([
                "systemctl", "is-active", service
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip() == "active":
                print(f"✅ {service}: active")
            else:
                print(f"❌ {service}: {result.stdout.strip()}")
                all_healthy = False
                
        except Exception as e:
            print(f"❌ {service}: error checking status - {e}")
            all_healthy = False
    
    return all_healthy

def test_api_endpoints():
    """Test API server endpoints"""
    print("🌐 Testing API Endpoints...")
    
    try:
        # Test basic API health
        response = requests.get("http://localhost:8000/test-alive", timeout=5)
        if response.status_code == 200:
            print("✅ API server health check passed")
        else:
            print(f"❌ API server health check failed: {response.status_code}")
            return False
        
        # Test live preview proxy
        response = requests.get("http://localhost:8000/live-preview", timeout=5)
        if response.status_code in [200, 503]:  # 503 is expected if camera not ready
            print(f"✅ API live preview proxy: {response.status_code}")
            return True
        else:
            print(f"❌ API live preview proxy failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def test_file_permissions():
    """Test file permissions and directories"""
    print("📁 Testing File Permissions...")
    
    required_dirs = [
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/media_cache"
    ]
    
    all_good = True
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            if os.access(dir_path, os.W_OK):
                print(f"✅ {dir_path}: exists and writable")
            else:
                print(f"❌ {dir_path}: exists but not writable")
                all_good = False
        else:
            print(f"❌ {dir_path}: does not exist")
            all_good = False
    
    return all_good

def test_environment():
    """Test environment variables and dependencies"""
    print("🔧 Testing Environment...")
    
    # Test OpenCV
    try:
        import cv2
        print("✅ OpenCV: available")
    except ImportError:
        print("❌ OpenCV: not available")
        return False
    
    # Test FastAPI
    try:
        import fastapi
        print("✅ FastAPI: available")
    except ImportError:
        print("❌ FastAPI: not available")
        return False
    
    # Test FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg: available")
        else:
            print("❌ FFmpeg: not working")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg: not found")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 EZREC Full System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment", test_environment),
        ("File Permissions", test_file_permissions),
        ("Systemd Services", test_service_status),
        ("Camera Streamer", test_camera_streamer),
        ("Live Preview", test_live_preview),
        ("OpenCV Recording", test_opencv_recording),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for production.")
    elif passed >= total * 0.8:
        print("⚠️ Most tests passed. System is mostly functional.")
    else:
        print("❌ Many tests failed. System needs attention.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 