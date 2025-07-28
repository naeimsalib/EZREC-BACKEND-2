#!/usr/bin/env python3
"""
Test script to verify camera detection fix
"""

from picamera2 import Picamera2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_camera_detection():
    """Test the fixed camera detection method"""
    try:
        logger.info("🔍 Testing camera detection...")
        
        # Try to create a Picamera2 instance (auto-detects first camera)
        temp_cam = Picamera2()  # Removed index=i
        
        # Try to get camera properties safely
        try:
            props = temp_cam.camera_properties
            serial = props.get('SerialNumber', 'unknown_0')
        except AttributeError:
            # Fallback if camera_properties is not available
            serial = 'unknown_0'
        
        temp_cam.close()
        logger.info(f"📷 Camera 0: Serial {serial}")
        
        # For dual camera setup, we'll use the same camera twice for testing
        logger.info(f"📷 Camera 1: Using same camera for dual setup")
        
        logger.info("✅ Camera detection successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Camera detection failed: {e}")
        return False

if __name__ == "__main__":
    test_camera_detection() 