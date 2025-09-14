#!/usr/bin/env python3
"""
Debug script to identify the exact camera initialization issue
"""

import sys
import traceback

def test_picamera2_basic():
    """Test basic Picamera2 functionality"""
    print("🔧 Testing basic Picamera2 functionality...")
    
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 imported successfully")
        
        # Test camera 0
        print("\n📷 Testing Camera 0...")
        try:
            camera = Picamera2(camera_num=0)
            print("✅ Camera 0 created successfully")
            
            # Get default configuration
            config = camera.create_video_configuration()
            print(f"📋 Default config: {config}")
            
            # Check if config has transform attribute
            if hasattr(config, 'transform'):
                print("⚠️ Config HAS transform attribute")
                print(f"   Transform: {config.transform}")
            else:
                print("✅ Config does NOT have transform attribute")
            
            camera.close()
            print("✅ Camera 0 closed successfully")
            
        except Exception as e:
            print(f"❌ Camera 0 failed: {e}")
            traceback.print_exc()
        
        # Test camera 1
        print("\n📷 Testing Camera 1...")
        try:
            camera = Picamera2(camera_num=1)
            print("✅ Camera 1 created successfully")
            
            # Get default configuration
            config = camera.create_video_configuration()
            print(f"📋 Default config: {config}")
            
            # Check if config has transform attribute
            if hasattr(config, 'transform'):
                print("⚠️ Config HAS transform attribute")
                print(f"   Transform: {config.transform}")
            else:
                print("✅ Config does NOT have transform attribute")
            
            camera.close()
            print("✅ Camera 1 closed successfully")
            
        except Exception as e:
            print(f"❌ Camera 1 failed: {e}")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"❌ Failed to import Picamera2: {e}")
        return False
    
    return True

def test_simple_recording():
    """Test simple recording without any custom configuration"""
    print("\n🎬 Testing simple recording...")
    
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
        
        # Test with camera 0
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
        output_file = "/tmp/test_recording.mp4"
        print(f"🎬 Starting test recording to {output_file}")
        
        camera.start_recording(encoder, output_file)
        print("✅ Recording started")
        
        import time
        time.sleep(2)
        
        camera.stop_recording()
        print("✅ Recording stopped")
        
        camera.stop()
        camera.close()
        print("✅ Camera closed")
        
        # Check if file was created
        import os
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ Recording file created: {size} bytes")
            return True
        else:
            print("❌ Recording file not created")
            return False
            
    except Exception as e:
        print(f"❌ Simple recording test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Camera Debug Script")
    print("=" * 50)
    
    # Test basic functionality
    if test_picamera2_basic():
        print("\n" + "=" * 50)
        # Test simple recording
        test_simple_recording()
    
    print("\n🏁 Debug complete")
