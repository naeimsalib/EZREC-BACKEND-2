#!/usr/bin/env python3
"""
Complete System Test Script
Tests the entire EZREC system without needing the frontend
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_camera_detection():
    """Test if cameras can be detected"""
    print("🔍 Testing camera detection...")
    
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 imported successfully")
        
        available_cameras = []
        
        # Test camera 0
        try:
            test_cam = Picamera2(camera_num=0)
            test_cam.close()
            available_cameras.append(0)
            print("✅ Camera 0 detected")
        except Exception as e:
            print(f"❌ Camera 0 not available: {e}")
        
        # Test camera 1
        try:
            test_cam = Picamera2(camera_num=1)
            test_cam.close()
            available_cameras.append(1)
            print("✅ Camera 1 detected")
        except Exception as e:
            print(f"❌ Camera 1 not available: {e}")
        
        print(f"📷 Available cameras: {available_cameras}")
        return available_cameras
        
    except ImportError as e:
        print(f"❌ Failed to import Picamera2: {e}")
        return []

def test_simple_recording():
    """Test simple recording with minimal configuration"""
    print("\n🎬 Testing simple recording...")
    
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
        
        # Test with camera 0
        print("📷 Testing Camera 0 recording...")
        camera = Picamera2(camera_num=0)
        
        # Use completely default configuration
        config = camera.create_video_configuration()
        print(f"📋 Using config: {config}")
        
        # Configure camera
        camera.configure(config)
        camera.start()
        print("✅ Camera started successfully")
        
        # Create encoder
        encoder = H264Encoder()
        
        # Test recording
        output_file = "/tmp/test_recording_camera0.mp4"
        print(f"🎬 Starting test recording to {output_file}")
        
        camera.start_recording(encoder, output_file)
        print("✅ Recording started")
        
        time.sleep(3)
        
        camera.stop_recording()
        print("✅ Recording stopped")
        
        camera.stop()
        camera.close()
        print("✅ Camera closed")
        
        # Check if file was created
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ Recording file created: {size} bytes")
            return True
        else:
            print("❌ Recording file not created")
            return False
            
    except Exception as e:
        print(f"❌ Simple recording test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_booking():
    """Create a test booking for the next few minutes"""
    print("\n📅 Creating test booking...")
    
    # Create bookings directory if it doesn't exist
    bookings_dir = Path("/opt/ezrec-backend/api/local_data")
    bookings_dir.mkdir(parents=True, exist_ok=True)
    
    bookings_file = bookings_dir / "bookings.json"
    
    # Calculate booking times (start now, end in 2 minutes)
    now = datetime.now(pytz.timezone('America/New_York'))
    start_time = now
    end_time = now + timedelta(minutes=2)
    
    # Create test booking
    test_booking = {
        "id": f"test-booking-{int(time.time())}",
        "user_id": "test-user-123",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "camera_id": "test-camera-456",
        "recording_id": f"rec-{int(time.time())}",
        "status": None,
        "email": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Save booking
    with open(bookings_file, 'w') as f:
        json.dump([test_booking], f, indent=2)
    
    print(f"✅ Test booking created:")
    print(f"   ID: {test_booking['id']}")
    print(f"   Start: {start_time}")
    print(f"   End: {end_time}")
    print(f"   Duration: 2 minutes")
    
    return test_booking

def test_minimal_recorder():
    """Test the minimal recorder directly"""
    print("\n🎥 Testing minimal recorder...")
    
    try:
        # Import the minimal recorder
        sys.path.append('/opt/ezrec-backend/backend')
        from dual_recorder import MinimalDualRecorder, load_bookings, find_active_booking
        
        # Create recorder
        recorder = MinimalDualRecorder()
        
        # Load bookings
        bookings = load_bookings()
        print(f"📋 Loaded {len(bookings)} bookings")
        
        # Find active booking
        active_booking = find_active_booking(bookings)
        
        if active_booking:
            print(f"🎯 Active booking found: {active_booking['id']}")
            
            # Start recording
            print("🎬 Starting recording session...")
            if recorder.start_recording_session(active_booking):
                print("✅ Recording started successfully")
                
                # Record for 30 seconds
                print("⏳ Recording for 30 seconds...")
                time.sleep(30)
                
                # Stop recording
                recorder.stop_recording_session()
                print("✅ Recording stopped")
                
                return True
            else:
                print("❌ Failed to start recording")
                return False
        else:
            print("❌ No active booking found")
            return False
            
    except Exception as e:
        print(f"❌ Minimal recorder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_recording_files():
    """Check if recording files were created"""
    print("\n📁 Checking for recording files...")
    
    # Check recordings directory
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    if not recordings_dir.exists():
        print("❌ Recordings directory does not exist")
        return False
    
    # Check today's directory
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = recordings_dir / today
    
    if not today_dir.exists():
        print(f"❌ Today's directory {today} does not exist")
        return False
    
    # Look for MP4 files
    mp4_files = list(today_dir.glob("*.mp4"))
    
    if mp4_files:
        print(f"✅ Found {len(mp4_files)} recording files:")
        for file in mp4_files:
            size = file.stat().st_size
            print(f"   📄 {file.name}: {size} bytes")
        return True
    else:
        print("❌ No MP4 files found")
        return False

def main():
    """Main test function"""
    print("🧪 EZREC Complete System Test")
    print("=" * 50)
    
    results = {}
    
    # Test 1: Camera detection
    print("\n1️⃣ Testing camera detection...")
    available_cameras = test_camera_detection()
    results['camera_detection'] = len(available_cameras) > 0
    
    if not available_cameras:
        print("❌ No cameras available, stopping tests")
        return False
    
    # Test 2: Simple recording
    print("\n2️⃣ Testing simple recording...")
    results['simple_recording'] = test_simple_recording()
    
    # Test 3: Create test booking
    print("\n3️⃣ Creating test booking...")
    test_booking = create_test_booking()
    results['booking_creation'] = True
    
    # Test 4: Test minimal recorder
    print("\n4️⃣ Testing minimal recorder...")
    results['minimal_recorder'] = test_minimal_recorder()
    
    # Test 5: Check recording files
    print("\n5️⃣ Checking recording files...")
    results['recording_files'] = check_recording_files()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! System is working correctly.")
    else:
        print("\n💥 SOME TESTS FAILED! Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
