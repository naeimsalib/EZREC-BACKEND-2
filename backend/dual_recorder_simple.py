#!/usr/bin/env python3
"""
Simplified Dual Camera Recorder
This version uses the most basic Picamera2 configuration to avoid compatibility issues
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    print("✅ Picamera2 imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Picamera2: {e}")
    sys.exit(1)

# Configuration
CAMERA_0_NAME = "left"
CAMERA_1_NAME = "right"
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/opt/ezrec-backend/logs/dual_recorder.log')
    ]
)
logger = logging.getLogger(__name__)

class SimpleCameraRecorder:
    """Simplified camera recorder with minimal configuration"""
    
    def __init__(self, camera_index, camera_name, output_path):
        self.camera_index = camera_index
        self.camera_name = camera_name
        self.output_path = output_path
        self.picamera2 = None
        self.encoder = None
        self.recording = False
        self.thread = None
        self.error = None
        self.success = False
        
    def initialize_camera(self):
        """Initialize camera with minimal configuration"""
        try:
            logger.info(f"🔧 Initializing {self.camera_name} camera (index {self.camera_index})")
            
            # Create camera with minimal config
            self.picamera2 = Picamera2(camera_num=self.camera_index)
            
            # Use default video configuration (no custom settings)
            config = self.picamera2.create_video_configuration()
            logger.info(f"📷 Using default config for {self.camera_name}: {config}")
            
            # Configure and start camera
            self.picamera2.configure(config)
            self.picamera2.start()
            
            # Create encoder
            self.encoder = H264Encoder()
            
            logger.info(f"✅ {self.camera_name} camera initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.camera_name} camera initialization failed: {e}")
            self.error = str(e)
            return False
    
    def start_recording(self):
        """Start recording"""
        try:
            if not self.picamera2:
                logger.error(f"❌ {self.camera_name} camera not initialized")
                return False
            
            logger.info(f"🎬 Starting recording for {self.camera_name} to {self.output_path}")
            self.picamera2.start_recording(self.encoder, str(self.output_path))
            self.recording = True
            self.success = True
            logger.info(f"✅ {self.camera_name} recording started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.camera_name} recording start failed: {e}")
            self.error = str(e)
            return False
    
    def stop_recording(self):
        """Stop recording"""
        try:
            if self.picamera2 and self.recording:
                self.picamera2.stop_recording()
                self.recording = False
                logger.info(f"✅ {self.camera_name} recording stopped")
        except Exception as e:
            logger.error(f"❌ {self.camera_name} recording stop failed: {e}")
    
    def cleanup(self):
        """Clean up camera resources"""
        try:
            if self.picamera2:
                self.picamera2.stop()
                self.picamera2.close()
                logger.info(f"✅ {self.camera_name} camera cleaned up")
        except Exception as e:
            logger.error(f"❌ {self.camera_name} cleanup failed: {e}")

class SimpleDualRecorder:
    """Simplified dual camera recorder"""
    
    def __init__(self):
        self.camera0_recorder = None
        self.camera1_recorder = None
        self.recording = False
        
    def detect_cameras(self):
        """Detect available cameras"""
        logger.info("🔍 Detecting cameras...")
        
        available_cameras = []
        
        # Test camera 0
        try:
            test_cam = Picamera2(camera_num=0)
            test_cam.close()
            available_cameras.append(0)
            logger.info("✅ Camera 0 detected")
        except Exception as e:
            logger.warning(f"⚠️ Camera 0 not available: {e}")
        
        # Test camera 1
        try:
            test_cam = Picamera2(camera_num=1)
            test_cam.close()
            available_cameras.append(1)
            logger.info("✅ Camera 1 detected")
        except Exception as e:
            logger.warning(f"⚠️ Camera 1 not available: {e}")
        
        logger.info(f"📷 Available cameras: {available_cameras}")
        return available_cameras
    
    def start_recording_session(self, booking):
        """Start a recording session for a booking"""
        try:
            logger.info(f"🎬 Starting recording session for booking: {booking['id']}")
            
            # Create recordings directory
            date_str = datetime.now().strftime("%Y-%m-%d")
            recordings_dir = RECORDINGS_DIR / date_str
            recordings_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            time_str = datetime.now().strftime("%H%M%S")
            filename_base = f"{time_str}_{booking['user_id']}_{booking['camera_id']}"
            
            # Detect available cameras
            available_cameras = self.detect_cameras()
            
            if not available_cameras:
                logger.error("❌ No cameras available")
                return False
            
            # Initialize camera recorders
            if 0 in available_cameras:
                camera0_file = recordings_dir / f"{filename_base}_cam1.mp4"
                self.camera0_recorder = SimpleCameraRecorder(0, CAMERA_0_NAME, camera0_file)
                
                if not self.camera0_recorder.initialize_camera():
                    logger.error("❌ Camera 0 initialization failed")
                    self.camera0_recorder = None
            
            if 1 in available_cameras and len(available_cameras) > 1:
                camera1_file = recordings_dir / f"{filename_base}_cam2.mp4"
                self.camera1_recorder = SimpleCameraRecorder(1, CAMERA_1_NAME, camera1_file)
                
                if not self.camera1_recorder.initialize_camera():
                    logger.error("❌ Camera 1 initialization failed")
                    self.camera1_recorder = None
            
            # Start recording on available cameras
            success_count = 0
            
            if self.camera0_recorder:
                if self.camera0_recorder.start_recording():
                    success_count += 1
            
            if self.camera1_recorder:
                if self.camera1_recorder.start_recording():
                    success_count += 1
            
            if success_count > 0:
                self.recording = True
                logger.info(f"✅ Recording started on {success_count} camera(s)")
                return True
            else:
                logger.error("❌ No cameras started recording successfully")
                return False
                
        except Exception as e:
            logger.error(f"❌ Recording session start failed: {e}")
            return False
    
    def stop_recording_session(self):
        """Stop the recording session"""
        try:
            logger.info("🛑 Stopping recording session...")
            
            if self.camera0_recorder:
                self.camera0_recorder.stop_recording()
                self.camera0_recorder.cleanup()
            
            if self.camera1_recorder:
                self.camera1_recorder.stop_recording()
                self.camera1_recorder.cleanup()
            
            self.recording = False
            logger.info("✅ Recording session stopped")
            
        except Exception as e:
            logger.error(f"❌ Recording session stop failed: {e}")
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording

def main():
    """Main function for testing"""
    logger.info("🎥 Simple Dual Recorder Test")
    
    # Create test booking
    test_booking = {
        "id": "test-booking-123",
        "user_id": "test-user-456",
        "camera_id": "test-camera-789"
    }
    
    # Create recorder
    recorder = SimpleDualRecorder()
    
    try:
        # Start recording
        if recorder.start_recording_session(test_booking):
            logger.info("✅ Recording started successfully")
            
            # Record for 10 seconds
            time.sleep(10)
            
            # Stop recording
            recorder.stop_recording_session()
            logger.info("✅ Recording completed successfully")
        else:
            logger.error("❌ Recording failed to start")
            
    except KeyboardInterrupt:
        logger.info("🛑 Recording interrupted by user")
        recorder.stop_recording_session()
    except Exception as e:
        logger.error(f"❌ Recording failed: {e}")
        recorder.stop_recording_session()

if __name__ == "__main__":
    main()
