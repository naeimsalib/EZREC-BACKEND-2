#!/usr/bin/env python3
"""
Simple OpenCV Camera Test for Raspberry Pi
"""

import cv2
import time
import sys

def test_opencv_camera():
    print("🧪 Testing OpenCV Camera on Raspberry Pi...")
    
    try:
        # Initialize camera
        print("📹 Opening camera with OpenCV...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Failed to open camera with OpenCV")
            return False
        
        print("✅ Camera opened successfully")
        
        # Configure camera settings
        print("⚙️ Configuring camera settings...")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Get actual settings
        actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"📐 Camera settings: {actual_width}x{actual_height} @ {actual_fps}fps")
        
        # Test frame capture
        print("📸 Testing frame capture...")
        ret, frame = cap.read()
        
        if ret and frame is not None:
            print(f"✅ Frame captured successfully: {frame.shape}")
            
            # Save test frame
            cv2.imwrite('/tmp/test_frame.jpg', frame)
            print("💾 Test frame saved to /tmp/test_frame.jpg")
            
            # Test multiple frames
            print("🔄 Testing multiple frames...")
            for i in range(5):
                ret, frame = cap.read()
                if ret:
                    print(f"  Frame {i+1}: {frame.shape}")
                else:
                    print(f"  Frame {i+1}: Failed")
                time.sleep(0.1)
            
            print("🎉 OpenCV camera test successful!")
            return True
        else:
            print("❌ Failed to capture frame")
            return False
            
    except Exception as e:
        print(f"❌ OpenCV camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'cap' in locals():
            cap.release()
            print("🔒 Camera released")

if __name__ == "__main__":
    success = test_opencv_camera()
    sys.exit(0 if success else 1) 