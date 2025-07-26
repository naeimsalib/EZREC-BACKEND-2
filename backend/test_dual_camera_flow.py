#!/usr/bin/env python3
"""
Test Dual Camera Flow - End-to-End Testing
Tests the complete flow from recording to processing
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add API directory to path
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * 40)

def check_environment():
    """Check environment variables and configuration"""
    print_section("Environment Check")
    
    # Check .env file
    env_path = "/opt/ezrec-backend/.env"
    if os.path.exists(env_path):
        print(f"✅ .env file found: {env_path}")
        
        # Load and check key variables
        from dotenv import load_dotenv
        load_dotenv(env_path)
        
        required_vars = [
            "SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID",
            "CAMERA_0_SERIAL", "CAMERA_1_SERIAL", "DUAL_CAMERA_MODE"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: Not set")
    else:
        print(f"❌ .env file not found: {env_path}")
        return False
    
    return True

def check_camera_detection():
    """Test camera detection"""
    print_section("Camera Detection Test")
    
    try:
        from picamera2 import CameraManager, Picamera2
        
        manager = CameraManager()
        cameras = manager.cameras
        
        print(f"📷 Detected {len(cameras)} camera(s)")
        
        if len(cameras) < 2:
            print(f"❌ Only {len(cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return False
        
        # Test each camera
        for i in range(len(cameras)):
            try:
                print(f"🔧 Testing camera {i}...")
                camera = Picamera2(index=i)
                
                # Get properties
                props = camera.camera_properties
                serial = props.get('SerialNumber', f'unknown_{i}')
                print(f"📷 Camera {i}: Serial {serial}")
                
                # Test basic config
                config = camera.create_video_configuration(
                    main={"size": (1920, 1080), "format": "YUV420"}
                )
                camera.configure(config)
                camera.start()
                camera.stop()
                camera.close()
                
                print(f"✅ Camera {i} is working")
                
            except Exception as e:
                print(f"❌ Camera {i} test failed: {e}")
                return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Picamera2 not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Camera detection failed: {e}")
        return False

def check_directories():
    """Check required directories and permissions"""
    print_section("Directory Check")
    
    directories = [
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/api/local_data"
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path} exists")
            
            # Check permissions
            try:
                test_file = path / "test_write.tmp"
                test_file.touch()
                test_file.unlink()
                print(f"✅ {dir_path} is writable")
            except Exception as e:
                print(f"❌ {dir_path} not writable: {e}")
        else:
            print(f"❌ {dir_path} does not exist")

def check_services():
    """Check if required services are running"""
    print_section("Service Status")
    
    services = [
        "dual_recorder.service",
        "video_worker.service",
        "system_status.service"
    ]
    
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=10
            )
            status = result.stdout.strip()
            if status == "active":
                print(f"✅ {service}: {status}")
            else:
                print(f"❌ {service}: {status}")
        except Exception as e:
            print(f"❌ {service}: Error checking status - {e}")

def create_test_booking():
    """Create a test booking for testing"""
    print_section("Creating Test Booking")
    
    # Create a booking that starts in 30 seconds and lasts 2 minutes
    now = datetime.now()
    start_time = now + timedelta(seconds=30)
    end_time = start_time + timedelta(minutes=2)
    
    booking = {
        "id": "test-dual-camera-001",
        "user_id": os.getenv("USER_ID", "test-user"),
        "camera_id": os.getenv("CAMERA_ID", "test-camera"),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "scheduled"
    }
    
    # Save to bookings cache
    bookings_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    
    try:
        if bookings_file.exists():
            with open(bookings_file, 'r') as f:
                bookings = json.load(f)
        else:
            bookings = []
        
        # Remove any existing test booking
        bookings = [b for b in bookings if b.get('id') != booking['id']]
        
        # Add new test booking
        bookings.append(booking)
        
        with open(bookings_file, 'w') as f:
            json.dump(bookings, f, indent=2)
        
        print(f"✅ Created test booking: {booking['id']}")
        print(f"   Start: {start_time.strftime('%H:%M:%S')}")
        print(f"   End: {end_time.strftime('%H:%M:%S')}")
        print(f"   Duration: 2 minutes")
        
        return booking
        
    except Exception as e:
        print(f"❌ Failed to create test booking: {e}")
        return None

def monitor_recording_process():
    """Monitor the recording and processing process"""
    print_section("Monitoring Recording Process")
    
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = recordings_dir / today
    
    print(f"📁 Monitoring directory: {today_dir}")
    print("⏳ Waiting for recording to start...")
    
    # Wait for recording to start
    start_time = time.time()
    timeout = 120  # 2 minutes
    
    while time.time() - start_time < timeout:
        if today_dir.exists():
            files = list(today_dir.glob("*"))
            if files:
                print(f"✅ Files found in {today_dir}:")
                for file in files:
                    size = file.stat().st_size if file.exists() else 0
                    print(f"   {file.name}: {size:,} bytes")
                break
        
        time.sleep(5)
        print(".", end="", flush=True)
    
    print("\n⏳ Waiting for recording to complete and merge...")
    
    # Wait for merged file and .done marker
    start_time = time.time()
    timeout = 300  # 5 minutes
    
    while time.time() - start_time < timeout:
        if today_dir.exists():
            merged_files = list(today_dir.glob("*_merged.mp4"))
            done_files = list(today_dir.glob("*_merged.done"))
            
            if merged_files:
                print(f"✅ Merged files found:")
                for file in merged_files:
                    size = file.stat().st_size if file.exists() else 0
                    print(f"   {file.name}: {size:,} bytes")
            
            if done_files:
                print(f"✅ .done markers found:")
                for file in done_files:
                    print(f"   {file.name}")
            
            if merged_files and done_files:
                print("🎉 Recording and merge completed successfully!")
                return True
        
        time.sleep(10)
        print(".", end="", flush=True)
    
    print("\n❌ Timeout waiting for recording completion")
    return False

def check_video_processing():
    """Check if video processing is working"""
    print_section("Video Processing Check")
    
    processed_dir = Path("/opt/ezrec-backend/processed")
    today = datetime.now().strftime("%Y-%m-%d")
    today_processed = processed_dir / today
    
    print(f"📁 Checking processed directory: {today_processed}")
    
    if today_processed.exists():
        files = list(today_processed.glob("*"))
        if files:
            print(f"✅ Processed files found:")
            for file in files:
                size = file.stat().st_size if file.exists() else 0
                print(f"   {file.name}: {size:,} bytes")
            return True
        else:
            print("⚠️ No processed files found")
            return False
    else:
        print("⚠️ Processed directory not found")
        return False

def cleanup_test_booking():
    """Clean up test booking"""
    print_section("Cleanup")
    
    bookings_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    
    try:
        if bookings_file.exists():
            with open(bookings_file, 'r') as f:
                bookings = json.load(f)
            
            # Remove test booking
            bookings = [b for b in bookings if not b.get('id', '').startswith('test-dual-camera-')]
            
            with open(bookings_file, 'w') as f:
                json.dump(bookings, f, indent=2)
            
            print("✅ Cleaned up test bookings")
        else:
            print("⚠️ No bookings file found")
            
    except Exception as e:
        print(f"❌ Failed to cleanup test bookings: {e}")

def main():
    """Main test function"""
    print_header("Dual Camera Flow Test")
    
    # Step 1: Environment check
    if not check_environment():
        print("❌ Environment check failed")
        return False
    
    # Step 2: Camera detection
    if not check_camera_detection():
        print("❌ Camera detection failed")
        return False
    
    # Step 3: Directory check
    check_directories()
    
    # Step 4: Service check
    check_services()
    
    # Step 5: Create test booking
    booking = create_test_booking()
    if not booking:
        print("❌ Failed to create test booking")
        return False
    
    # Step 6: Monitor recording process
    print("\n🎬 Starting recording test...")
    print("📝 This will create a 2-minute test recording")
    print("⏰ Recording will start in 30 seconds...")
    
    success = monitor_recording_process()
    
    if success:
        # Step 7: Check video processing
        print("\n⏳ Waiting for video processing...")
        time.sleep(30)  # Wait for video worker to process
        
        processing_success = check_video_processing()
        
        if processing_success:
            print("\n🎉 Complete dual camera flow test PASSED!")
            print("✅ Recording ✅ Merging ✅ Processing")
        else:
            print("\n⚠️ Recording and merging worked, but processing may have issues")
    else:
        print("\n❌ Recording test failed")
    
    # Step 8: Cleanup
    cleanup_test_booking()
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        cleanup_test_booking()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        cleanup_test_booking()
        sys.exit(1) 