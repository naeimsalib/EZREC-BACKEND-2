#!/usr/bin/env python3
"""
Test script to verify camera detection works without CameraManager
"""
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(__file__))

try:
    from dual_recorder import detect_cameras, validate_camera_setup
    print("✅ Successfully imported dual_recorder functions")
    
    print("\n🔍 Testing camera detection...")
    camera0_index, camera1_index = detect_cameras()
    
    if camera0_index is not None and camera1_index is not None:
        print(f"✅ Camera detection successful!")
        print(f"   Camera 0 index: {camera0_index}")
        print(f"   Camera 1 index: {camera1_index}")
    else:
        print("❌ Camera detection failed")
    
    print("\n🔍 Testing camera validation...")
    if validate_camera_setup():
        print("✅ Camera validation successful!")
    else:
        print("❌ Camera validation failed")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 