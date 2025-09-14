#!/usr/bin/env python3
"""
Simple camera test script to verify basic camera functionality
This uses the most basic Picamera2 approach without any complex configurations
"""

import time
import sys
from pathlib import Path

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    print("✅ Picamera2 imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Picamera2: {e}")
    sys.exit(1)

def test_single_camera(camera_index=0):
    """Test a single camera with minimal configuration"""
    print(f"🔧 Testing camera {camera_index}...")
    
    try:
        # Create camera with minimal config
        camera = Picamera2(camera_num=camera_index)
        
        # Get default configuration
        config = camera.create_video_configuration()
        print(f"📷 Default config: {config}")
        
        # Configure camera
        camera.configure(config)
        camera.start()
        print(f"✅ Camera {camera_index} started successfully")
        
        # Test recording for 3 seconds
        output_file = f"/tmp/test_camera_{camera_index}.mp4"
        encoder = H264Encoder()
        
        print(f"🎬 Starting 3-second test recording to {output_file}")
        camera.start_recording(encoder, output_file)
        time.sleep(3)
        camera.stop_recording()
        
        print(f"✅ Test recording completed: {output_file}")
        
        # Check if file was created
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            print(f"📁 File created: {file_size} bytes")
            return True
        else:
            print(f"❌ File not created: {output_file}")
            return False
            
    except Exception as e:
        print(f"❌ Camera {camera_index} test failed: {e}")
        return False
    finally:
        try:
            camera.stop()
            camera.close()
        except:
            pass

def main():
    print("🎥 Simple Camera Test Script")
    print("=" * 50)
    
    # Test camera 0
    success_0 = test_single_camera(0)
    
    # Test camera 1
    success_1 = test_single_camera(1)
    
    print("\n📊 Results:")
    print(f"Camera 0: {'✅ SUCCESS' if success_0 else '❌ FAILED'}")
    print(f"Camera 1: {'✅ SUCCESS' if success_1 else '❌ FAILED'}")
    
    if success_0 or success_1:
        print("\n🎉 At least one camera is working!")
        return 0
    else:
        print("\n💥 No cameras are working!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
