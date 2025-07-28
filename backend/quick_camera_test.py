#!/usr/bin/env python3
"""
Quick Camera Test - Immediate hardware verification
"""

import os
import sys
import subprocess
import time

def test_video_devices():
    """Test if video devices are available"""
    print("🔍 Testing video devices...")
    
    try:
        result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True)
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')
            devices = [d for d in devices if d]
            print(f"✅ Found {len(devices)} video devices:")
            for device in devices:
                print(f"   📹 {device}")
            return True
        else:
            print("❌ No video devices found")
            return False
    except Exception as e:
        print(f"❌ Error checking video devices: {e}")
        return False

def test_camera_info():
    """Test camera information"""
    print("\n📋 Testing camera information...")
    
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Camera information:")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to get camera information")
            return False
    except Exception as e:
        print(f"❌ Error getting camera info: {e}")
        return False

def test_python_camera():
    """Test Python camera access"""
    print("\n🐍 Testing Python camera access...")
    
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 import successful")
        
        # Test camera creation
        camera = Picamera2()
        print("✅ Camera creation successful")
        
        # Test configuration
        config = camera.create_video_configuration(
            main={"size": (1920, 1080), "format": "YUV420"}
        )
        camera.configure(config)
        camera.start()
        print("✅ Camera configuration and start successful")
        
        # Test image capture
        image = camera.capture_array()
        if image is not None and image.size > 0:
            print(f"✅ Image capture successful: {image.shape}")
        else:
            print("❌ Image capture failed - empty image")
            camera.stop()
            camera.close()
            return False
        
        camera.stop()
        camera.close()
        print("✅ Camera cleanup successful")
        return True
        
    except ImportError:
        print("❌ Picamera2 not available")
        return False
    except Exception as e:
        print(f"❌ Python camera test failed: {e}")
        return False

def test_video_recording():
    """Test video recording"""
    print("\n🎥 Testing video recording...")
    
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
        
        camera = Picamera2()
        config = camera.create_video_configuration(
            main={"size": (1920, 1080), "format": "YUV420"}
        )
        camera.configure(config)
        camera.start()
        
        # Create encoder
        encoder = H264Encoder(bitrate=6000000)
        
        # Start recording
        test_file = "/tmp/quick_camera_test.mp4"
        camera.start_recording(encoder, test_file)
        
        # Record for 3 seconds
        print("📹 Recording for 3 seconds...")
        time.sleep(3)
        
        # Stop recording
        camera.stop_recording()
        camera.stop()
        camera.close()
        
        # Check result
        if os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            if file_size > 0:
                print(f"✅ Video recording successful: {file_size} bytes")
                
                # Clean up
                os.remove(test_file)
                return True
            else:
                print("❌ Video recording failed - empty file")
                return False
        else:
            print("❌ Video recording failed - file not created")
            return False
            
    except Exception as e:
        print(f"❌ Video recording test failed: {e}")
        return False

def main():
    """Run all quick tests"""
    print("🚀 EZREC Quick Camera Test")
    print("=" * 40)
    
    tests = [
        ("Video Devices", test_video_devices),
        ("Camera Info", test_camera_info),
        ("Python Camera", test_python_camera),
        ("Video Recording", test_video_recording)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Camera is working perfectly.")
    elif passed > 0:
        print("⚠️ Some tests passed. Camera has issues but may be usable.")
    else:
        print("❌ All tests failed. Camera is not working properly.")

if __name__ == "__main__":
    main() 