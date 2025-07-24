#!/usr/bin/env python3
"""
EZREC System Health Test Script
Comprehensive diagnostics for dual camera setup, disk space, services, and configuration
"""

import os
import sys
import json
import time
import subprocess
import psutil
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * 40)

def check_environment():
    """Check environment configuration"""
    print_section("Environment Configuration")
    
    required_vars = [
        "SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"
    ]
    
    optional_vars = [
        "CAMERA_1_SERIAL", "CAMERA_2_SERIAL", "DUAL_CAMERA_MODE",
        "RESOLUTION", "VIDEO_ENCODER"
    ]
    
    print("Required Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * len(value)} (configured)")
        else:
            print(f"  ❌ {var}: NOT SET")
    
    print("\nOptional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️ {var}: NOT SET")

def check_system_resources():
    """Check system resources"""
    print_section("System Resources")
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU Usage: {cpu_percent}%")
    
    # Memory
    memory = psutil.virtual_memory()
    print(f"Memory: {memory.percent}% used ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)")
    
    # Disk space
    disk = shutil.disk_usage("/opt/ezrec-backend")
    disk_used_percent = (disk.used / disk.total) * 100
    print(f"Disk: {disk_used_percent:.1f}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
    
    # Temperature
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
        if result.returncode == 0:
            temp = result.stdout.strip()
            print(f"Temperature: {temp}")
        else:
            print("Temperature: Unable to read")
    except Exception:
        print("Temperature: Unable to read")

def check_camera_hardware():
    """Check camera hardware"""
    print_section("Camera Hardware")
    
    # Check video devices
    video_devices = list(Path("/dev").glob("video*"))
    print(f"Video devices found: {len(video_devices)}")
    for device in video_devices:
        print(f"  📹 {device}")
    
    # Check camera detection
    try:
        result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("\nCamera detection output:")
            print(result.stdout)
        else:
            print("❌ Camera detection failed")
    except Exception as e:
        print(f"❌ Camera detection error: {e}")

def check_camera_availability():
    """Test camera availability"""
    print_section("Camera Availability")
    
    try:
        from picamera2 import Picamera2
        
        cam1_serial = os.getenv('CAMERA_1_SERIAL')
        cam2_serial = os.getenv('CAMERA_2_SERIAL')
        
        cameras_to_test = []
        if cam1_serial:
            cameras_to_test.append(("Camera 1", cam1_serial))
        if cam2_serial:
            cameras_to_test.append(("Camera 2", cam2_serial))
        
        if not cameras_to_test:
            print("⚠️ No camera serials configured")
            return
        
        for camera_name, camera_serial in cameras_to_test:
            print(f"\nTesting {camera_name} (serial: {camera_serial})...")
            try:
                camera = Picamera2()
                camera_info = camera.camera_properties
                actual_serial = camera_info.get('SerialNumber', 'Unknown')
                
                if actual_serial == camera_serial:
                    print(f"  ✅ {camera_name} is available and matches serial")
                else:
                    print(f"  ⚠️ {camera_name} serial mismatch. Expected: {camera_serial}, Got: {actual_serial}")
                
                camera.close()
            except Exception as e:
                print(f"  ❌ {camera_name} is not available: {e}")
    
    except ImportError:
        print("❌ picamera2 not available")

def check_services():
    """Check systemd services"""
    print_section("System Services")
    
    services = [
        "recorder.service",
        "video_worker.service", 
        "system_status.service",
        "log_collector.service",
        "health_api.service"
    ]
    
    for service in services:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True)
            status = result.stdout.strip()
            if status == "active":
                print(f"✅ {service}: {status}")
            else:
                print(f"❌ {service}: {status}")
        except Exception as e:
            print(f"❌ {service}: Error checking status - {e}")

def check_directories():
    """Check directory structure and permissions"""
    print_section("Directory Structure")
    
    directories = [
        "/opt/ezrec-backend",
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/processed",
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/media_cache",
        "/opt/ezrec-backend/api/local_data"
    ]
    
    for directory in directories:
        path = Path(directory)
        if path.exists():
            try:
                stat = path.stat()
                print(f"✅ {directory}: exists (owner: {stat.st_uid})")
            except Exception as e:
                print(f"❌ {directory}: exists but error reading - {e}")
        else:
            print(f"❌ {directory}: does not exist")

def check_recent_recordings():
    """Check recent recordings"""
    print_section("Recent Recordings")
    
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    if not recordings_dir.exists():
        print("❌ Recordings directory does not exist")
        return
    
    # Find recent date directories
    date_dirs = sorted(recordings_dir.glob("*"), reverse=True)[:3]
    
    for date_dir in date_dirs:
        if date_dir.is_dir():
            print(f"\n📅 {date_dir.name}:")
            recordings = list(date_dir.glob("*.mp4"))
            done_files = list(date_dir.glob("*.done"))
            error_files = list(date_dir.glob("*.error"))
            
            print(f"  📹 Recordings: {len(recordings)}")
            print(f"  ✅ Done markers: {len(done_files)}")
            print(f"  ❌ Error markers: {len(error_files)}")
            
            if recordings:
                latest = max(recordings, key=lambda x: x.stat().st_mtime)
                size_mb = latest.stat().st_size / (1024**2)
                print(f"  📊 Latest: {latest.name} ({size_mb:.1f} MB)")

def check_network_connectivity():
    """Check network connectivity"""
    print_section("Network Connectivity")
    
    # Test internet
    try:
        result = subprocess.run(['ping', '-c', '3', '8.8.8.8'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Internet connectivity: OK")
        else:
            print("❌ Internet connectivity: Failed")
    except Exception:
        print("❌ Internet connectivity: Error testing")
    
    # Test Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    if supabase_url:
        try:
            import requests
            response = requests.get(f"{supabase_url}/rest/v1/", timeout=10)
            if response.status_code == 200:
                print("✅ Supabase connectivity: OK")
            else:
                print(f"❌ Supabase connectivity: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Supabase connectivity: {e}")

def check_ffmpeg():
    """Check FFmpeg availability"""
    print_section("FFmpeg")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version_line}")
        else:
            print("❌ FFmpeg: Not working")
    except Exception as e:
        print(f"❌ FFmpeg: {e}")

def generate_report():
    """Generate comprehensive health report"""
    print_header("EZREC System Health Report")
    print(f"Generated: {datetime.now().isoformat()}")
    
    check_environment()
    check_system_resources()
    check_camera_hardware()
    check_camera_availability()
    check_services()
    check_directories()
    check_recent_recordings()
    check_network_connectivity()
    check_ffmpeg()
    
    print_header("Health Report Complete")
    print("✅ Run this script regularly to monitor system health")
    print("📊 Check the /status endpoint for real-time monitoring")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # JSON output for API integration
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": {},
            "system": {},
            "cameras": {},
            "services": {},
            "health": "unknown"
        }
        # TODO: Implement JSON report generation
        print(json.dumps(report, indent=2))
    else:
        generate_report()

if __name__ == "__main__":
    main() 