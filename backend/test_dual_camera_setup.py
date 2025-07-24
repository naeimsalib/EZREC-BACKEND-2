#!/usr/bin/env python3
"""
Test script for dual camera setup
- Detects available cameras
- Tests camera initialization
- Verifies environment configuration
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
except ImportError:
    print("❌ picamera2 not available")
    sys.exit(1)

def get_camera_serials():
    """Get camera serials from environment variables"""
    cam1_serial = os.getenv('CAMERA_1_SERIAL')
    cam2_serial = os.getenv('CAMERA_2_SERIAL')
    
    print(f"🔍 Camera Configuration:")
    print(f"   CAMERA_1_SERIAL: {cam1_serial}")
    print(f"   CAMERA_2_SERIAL: {cam2_serial}")
    
    return cam1_serial, cam2_serial

def detect_available_cameras():
    """Detect all available cameras"""
    print("\n🔍 Detecting available cameras...")
    
    try:
        import subprocess
        result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("📋 Available cameras:")
            print(result.stdout)
            return result.stdout
        else:
            print(f"❌ Failed to list cameras: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Error detecting cameras: {e}")
        return None

def test_camera_initialization(camera_serial, camera_name):
    """Test initialization of a specific camera"""
    print(f"\n🎥 Testing {camera_name} initialization...")
    
    try:
        camera = Picamera2()
        
        # Get camera info
        camera_info = camera.camera_properties
        actual_serial = camera_info.get('SerialNumber', 'Unknown')
        
        print(f"   Camera serial: {actual_serial}")
        print(f"   Expected serial: {camera_serial}")
        
        if camera_serial and actual_serial != camera_serial:
            print(f"   ⚠️ Serial mismatch!")
            camera.close()
            return False
        
        # Test basic configuration
        config = camera.create_video_configuration(
            main={"size": (1280, 720), "format": "YUV420"},
            controls={
                "FrameDurationLimits": (33333, 1000000),
                "ExposureTime": 33333,
                "AnalogueGain": 1.0
            }
        )
        
        camera.configure(config)
        camera.start()
        
        print(f"   ✅ {camera_name} initialized successfully")
        
        # Test recording for 2 seconds
        print(f"   🎬 Testing recording for 2 seconds...")
        encoder = H264Encoder(
            bitrate=4000000,
            repeat=False,
            iperiod=30,
            qp=30,
            profile="baseline",
            level="4.1"
        )
        
        test_file = f"/tmp/test_{camera_name.lower()}.mp4"
        camera.start_recording(encoder, test_file)
        time.sleep(2)
        camera.stop_recording()
        time.sleep(1)
        
        # Check if file was created
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            print(f"   ✅ Test recording created: {file_size} bytes")
            os.remove(test_file)
        else:
            print(f"   ❌ Test recording failed")
        
        camera.stop()
        camera.close()
        return True
        
    except Exception as e:
        print(f"   ❌ {camera_name} initialization failed: {e}")
        return False

def main():
    print("🎬 EZREC Dual Camera Setup Test")
    print("=" * 50)
    
    # Check environment configuration
    cam1_serial, cam2_serial = get_camera_serials()
    
    # Detect available cameras
    camera_list = detect_available_cameras()
    
    # Test camera initialization
    success_count = 0
    
    if cam1_serial:
        if test_camera_initialization(cam1_serial, "Camera 1"):
            success_count += 1
    
    if cam2_serial:
        if test_camera_initialization(cam2_serial, "Camera 2"):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Cameras configured: {sum(1 for x in [cam1_serial, cam2_serial] if x)}")
    print(f"   Cameras initialized successfully: {success_count}")
    
    if success_count == 0:
        print("   ❌ No cameras working - check configuration")
        return False
    elif success_count == 1:
        print("   ⚠️ Only one camera working - will use single camera mode")
        return True
    else:
        print("   ✅ Dual camera setup working - ready for dual camera mode")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 