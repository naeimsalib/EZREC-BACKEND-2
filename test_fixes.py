#!/usr/bin/env python3
"""
Test script to verify all fixes are working
"""

import os
import sys
import subprocess
import tempfile

def test_picamera2_import():
    """Test Picamera2 import with error handling"""
    print("🧪 Testing Picamera2 import...")
    try:
        from picamera2 import Picamera2
        print("✅ Picamera2 import successful")
        
        # Test camera detection with error handling
        try:
            temp_cam = Picamera2(index=0)
            try:
                props = temp_cam.camera_properties
                print("✅ camera_properties available")
            except AttributeError:
                print("✅ camera_properties not available (using fallback)")
            temp_cam.close()
            print("✅ Picamera2 camera creation successful")
        except Exception as e:
            print(f"⚠️ Camera creation failed (expected): {e}")
        
        return True
    except ImportError as e:
        print(f"❌ Picamera2 import failed: {e}")
        return False

def test_ffmpeg_paths():
    """Test FFmpeg and FFprobe with proper paths"""
    print("🧪 Testing FFmpeg paths...")
    
    import shutil
    
    ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
    ffprobe_path = shutil.which("ffprobe") or "/usr/bin/ffprobe"
    
    try:
        result = subprocess.run([ffmpeg_path, "-version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg working with proper path")
        else:
            print("❌ FFmpeg failed")
            return False
    except Exception as e:
        print(f"❌ FFmpeg error: {e}")
        return False
    
    try:
        result = subprocess.run([ffprobe_path, "-version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFprobe working with proper path")
        else:
            print("❌ FFprobe failed")
            return False
    except Exception as e:
        print(f"❌ FFprobe error: {e}")
        return False
    
    return True

def test_simple_imports():
    """Test basic imports"""
    print("🧪 Testing basic imports...")
    
    try:
        import os
        import tempfile
        import sys
        print("✅ Basic imports successful")
        return True
    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        return False

def test_system_status_timer():
    """Test if system_status.timer is enabled"""
    print("🧪 Testing system_status.timer...")
    
    try:
        result = subprocess.run(['systemctl', 'is-enabled', 'system_status.timer'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'enabled' in result.stdout:
            print("✅ system_status.timer is enabled")
            return True
        else:
            print("❌ system_status.timer is not enabled")
            return False
    except Exception as e:
        print(f"❌ system_status.timer check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing all fixes...")
    
    success = True
    
    if not test_simple_imports():
        success = False
    
    if not test_picamera2_import():
        success = False
    
    if not test_ffmpeg_paths():
        success = False
    
    if not test_system_status_timer():
        success = False
    
    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 