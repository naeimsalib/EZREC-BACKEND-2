#!/usr/bin/env python3
"""
Manual Camera Testing Script
Tests individual camera initialization and recording
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("camera_test")

def signal_handler(sig, frame):
    print("🛑 Received termination signal")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def test_camera_initialization(camera_serial=None, camera_name="Unknown"):
    """Test camera initialization with detailed logging"""
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import H264Encoder
    except ImportError as e:
        logger.error(f"❌ Picamera2 not available: {e}")
        return False
    
    logger.info(f"🔧 Testing {camera_name} camera initialization")
    logger.info(f"📷 Camera serial: {camera_serial}")
    
    try:
        # Create camera object
        logger.info("📷 Creating Picamera2 object...")
        camera = Picamera2()
        
        # Get camera properties
        logger.info("📋 Getting camera properties...")
        props = camera.camera_properties
        logger.info(f"📷 Camera properties: {props}")
        
        # Check serial number
        if 'SerialNumber' in props:
            actual_serial = props['SerialNumber']
            logger.info(f"🔢 Camera serial: {actual_serial}")
            
            if camera_serial and actual_serial != camera_serial:
                logger.warning(f"⚠️  Serial mismatch! Expected: {camera_serial}, Got: {actual_serial}")
                camera.close()
                return False
        else:
            logger.warning("⚠️  No serial number found in camera properties")
        
        # Test configuration
        logger.info("⚙️ Testing camera configuration...")
        config = camera.create_video_configuration(
            main={"size": (1920, 1080), "format": "YUV420"},
            controls={
                "FrameDurationLimits": (33333, 1000000),
                "ExposureTime": 33333,
                "AnalogueGain": 1.0,
                "NoiseReductionMode": 0
            }
        )
        
        logger.info("🔧 Configuring camera...")
        camera.configure(config)
        
        logger.info("▶️ Starting camera...")
        camera.start()
        
        # Test recording for 5 seconds
        logger.info("🎥 Testing recording for 5 seconds...")
        test_file = f"/tmp/test_{camera_name.lower()}_camera.mp4"
        
        encoder = H264Encoder(
            bitrate=6000000,
            repeat=False,
            iperiod=30,
            qp=25
        )
        
        camera.start_recording(encoder, test_file)
        time.sleep(5)
        camera.stop_recording()
        
        # Check if file was created
        if Path(test_file).exists():
            file_size = Path(test_file).stat().st_size
            logger.info(f"✅ Test recording created: {test_file} ({file_size} bytes)")
            
            # Clean up test file
            Path(test_file).unlink()
            logger.info(f"🗑️ Cleaned up test file: {test_file}")
        else:
            logger.error(f"❌ Test recording file not created: {test_file}")
            camera.stop()
            camera.close()
            return False
        
        logger.info("⏹️ Stopping camera...")
        camera.stop()
        camera.close()
        
        logger.info(f"✅ {camera_name} camera test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ {camera_name} camera test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

def main():
    logger.info("🔍 Starting manual camera tests")
    
    # Get camera configuration from environment
    camera_0_serial = os.getenv('CAMERA_0_SERIAL')
    camera_1_serial = os.getenv('CAMERA_1_SERIAL')
    camera_0_name = os.getenv('CAMERA_0_NAME', 'left')
    camera_1_name = os.getenv('CAMERA_1_NAME', 'right')
    
    logger.info(f"📷 Camera 0: {camera_0_name} (Serial: {camera_0_serial})")
    logger.info(f"📷 Camera 1: {camera_1_name} (Serial: {camera_1_serial})")
    
    # Test first camera
    logger.info("=" * 50)
    logger.info("🔍 TESTING CAMERA 0")
    logger.info("=" * 50)
    
    success_0 = test_camera_initialization(camera_0_serial, camera_0_name)
    
    # Wait between tests
    time.sleep(3)
    
    # Test second camera
    logger.info("=" * 50)
    logger.info("🔍 TESTING CAMERA 1")
    logger.info("=" * 50)
    
    success_1 = test_camera_initialization(camera_1_serial, camera_1_name)
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Camera 0 ({camera_0_name}): {'✅ PASS' if success_0 else '❌ FAIL'}")
    logger.info(f"Camera 1 ({camera_1_name}): {'✅ PASS' if success_1 else '❌ FAIL'}")
    
    if success_0 and success_1:
        logger.info("🎉 Both cameras working correctly!")
    elif success_0 or success_1:
        logger.info("⚠️  One camera working, one failed")
    else:
        logger.error("❌ Both cameras failed")
    
    return success_0 and success_1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 