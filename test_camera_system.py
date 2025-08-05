#!/usr/bin/env python3
"""
Comprehensive Camera System Test Script
Tests all components after CSI camera fix
"""

import subprocess
import time
import requests
import json
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return results"""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, "", str(e)

def test_service_status():
    """Test camera streamer service status"""
    print("\n" + "="*60)
    print("🔧 TESTING CAMERA STREAMER SERVICE")
    print("="*60)
    
    success, output, error = run_command(
        "sudo systemctl status camera_streamer.service --no-pager",
        "Check camera streamer service status"
    )
    
    if success and "active (running)" in output:
        print("✅ Camera streamer service is running")
        return True
    else:
        print("❌ Camera streamer service is not running properly")
        return False

def test_service_logs():
    """Test camera streamer service logs"""
    print("\n" + "="*60)
    print("📋 TESTING CAMERA STREAMER LOGS")
    print("="*60)
    
    success, output, error = run_command(
        "sudo journalctl -u camera_streamer.service --no-pager -n 10",
        "Check recent camera streamer logs"
    )
    
    if success and output:
        print("✅ Service logs retrieved successfully")
        if "libcamera-vid streamer started successfully" in output:
            print("✅ Streamer started successfully")
            return True
        else:
            print("⚠️ Streamer may not have started properly")
            return False
    else:
        print("❌ Could not retrieve service logs")
        return False

def test_camera_api():
    """Test camera API endpoints"""
    print("\n" + "="*60)
    print("🌐 TESTING CAMERA API ENDPOINTS")
    print("="*60)
    
    # Test camera status endpoint
    try:
        response = requests.get("http://localhost:9000/camera-status", timeout=10)
        print(f"Camera status endpoint: {response.status_code}")
        if response.status_code == 200:
            print("✅ Camera status endpoint responding")
            try:
                data = response.json()
                print(f"Camera data: {json.dumps(data, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
        else:
            print("❌ Camera status endpoint not responding properly")
    except Exception as e:
        print(f"❌ Camera status endpoint error: {e}")
    
    # Test live preview endpoint
    try:
        response = requests.get("http://localhost:9000/live-preview", timeout=5)
        print(f"Live preview endpoint: {response.status_code}")
        if response.status_code == 200:
            print("✅ Live preview endpoint responding")
        else:
            print("⚠️ Live preview endpoint may not be working")
    except Exception as e:
        print(f"⚠️ Live preview endpoint error: {e}")

def test_libcamera_process():
    """Test if libcamera-vid process is running"""
    print("\n" + "="*60)
    print("🎥 TESTING LIBCAMERA PROCESS")
    print("="*60)
    
    success, output, error = run_command(
        "ps aux | grep libcamera-vid | grep -v grep",
        "Check if libcamera-vid process is running"
    )
    
    if success and output:
        print("✅ libcamera-vid process is running")
        print(f"Process info: {output}")
        return True
    else:
        print("❌ libcamera-vid process is not running")
        return False

def test_camera_stream():
    """Test camera stream functionality"""
    print("\n" + "="*60)
    print("📹 TESTING CAMERA STREAM")
    print("="*60)
    
    # Test if we can capture a frame
    success, output, error = run_command(
        "timeout 3 libcamera-vid -t 3000 -o /tmp/test_stream.h264",
        "Test camera stream capture (3 seconds)"
    )
    
    if success:
        print("✅ Camera stream test completed")
        # Check if file was created
        test_file = Path("/tmp/test_stream.h264")
        if test_file.exists() and test_file.stat().st_size > 1024:
            print(f"✅ Test video file created: {test_file.stat().st_size} bytes")
            return True
        else:
            print("⚠️ Test video file not created or too small")
            return False
    else:
        print("❌ Camera stream test failed")
        return False

def test_recording_system():
    """Test recording system"""
    print("\n" + "="*60)
    print("🎬 TESTING RECORDING SYSTEM")
    print("="*60)
    
    # Check if recorder service is running
    success, output, error = run_command(
        "sudo systemctl status recorder.service --no-pager",
        "Check recorder service status"
    )
    
    if success and "active (running)" in output:
        print("✅ Recorder service is running")
    else:
        print("⚠️ Recorder service is not running")
    
    # Check if video worker is running
    success, output, error = run_command(
        "sudo systemctl status video_worker.service --no-pager",
        "Check video worker service status"
    )
    
    if success and "active (running)" in output:
        print("✅ Video worker service is running")
    else:
        print("⚠️ Video worker service is not running")

def test_system_health():
    """Test overall system health"""
    print("\n" + "="*60)
    print("🏥 TESTING SYSTEM HEALTH")
    print("="*60)
    
    # Test CPU usage
    success, output, error = run_command(
        "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1",
        "Check CPU usage"
    )
    if success and output:
        cpu_usage = float(output.strip())
        print(f"CPU Usage: {cpu_usage}%")
        if cpu_usage < 80:
            print("✅ CPU usage is normal")
        else:
            print("⚠️ CPU usage is high")
    
    # Test memory usage
    success, output, error = run_command(
        "free -m | grep Mem | awk '{print int($3/$2 * 100)}'",
        "Check memory usage"
    )
    if success and output:
        mem_usage = int(output.strip())
        print(f"Memory Usage: {mem_usage}%")
        if mem_usage < 80:
            print("✅ Memory usage is normal")
        else:
            print("⚠️ Memory usage is high")
    
    # Test disk space
    success, output, error = run_command(
        "df -h / | tail -1 | awk '{print $5}' | cut -d'%' -f1",
        "Check disk usage"
    )
    if success and output:
        disk_usage = int(output.strip())
        print(f"Disk Usage: {disk_usage}%")
        if disk_usage < 90:
            print("✅ Disk usage is normal")
        else:
            print("⚠️ Disk usage is high")

def main():
    """Main test function"""
    print("🚀 COMPREHENSIVE CAMERA SYSTEM TEST")
    print("="*60)
    print("Testing all components after CSI camera fix...")
    
    # Run all tests
    tests = [
        ("Service Status", test_service_status),
        ("Service Logs", test_service_logs),
        ("Camera API", test_camera_api),
        ("LibCamera Process", test_libcamera_process),
        ("Camera Stream", test_camera_stream),
        ("Recording System", test_recording_system),
        ("System Health", test_system_health),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Camera system is working perfectly!")
    elif passed >= total * 0.8:
        print("✅ Most tests passed! Camera system is working well.")
    else:
        print("⚠️ Some tests failed. Camera system may need attention.")

if __name__ == "__main__":
    main() 