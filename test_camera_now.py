#!/usr/bin/env python3
"""
Quick camera test to verify functionality
"""

import sys
import time

def test_camera():
    print("🔧 Testing camera functionality...")
    
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
        print("✅ Picamera2 imported successfully")
        
        # Test camera 0
        print("\n📷 Testing Camera 0...")
        camera = Picamera2(camera_num=0)
        
        # Use default configuration
        config = camera.create_video_configuration()
        print(f"📋 Config: {config}")
        
        # Configure and start
        camera.configure(config)
        camera.start()
        print("✅ Camera started")
        
        # Test recording
        encoder = H264Encoder()
        output_file = "/tmp/test_camera_0.mp4"
        
        print(f"🎬 Recording to {output_file}")
        camera.start_recording(encoder, output_file)
        time.sleep(3)
        camera.stop_recording()
        
        camera.stop()
        camera.close()
        print("✅ Camera 0 test completed")
        
        # Check file
        import os
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ File created: {size} bytes")
            return True
        else:
            print("❌ File not created")
            return False
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_camera()
    if success:
        print("\n🎉 Camera test PASSED!")
    else:
        print("\n💥 Camera test FAILED!")
    sys.exit(0 if success else 1)
