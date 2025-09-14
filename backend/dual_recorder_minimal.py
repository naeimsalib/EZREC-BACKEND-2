#!/usr/bin/env python3
"""
MINIMAL Dual Camera Recorder - No Custom Configuration
This version uses absolutely minimal Picamera2 setup to avoid ALL compatibility issues
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

class MinimalCameraRecorder:
    """Minimal camera recorder with absolutely no custom configuration"""
    
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
        """Initialize camera with absolutely minimal configuration"""
        try:
            logger.info(f"🔧 Initializing {self.camera_name} camera (index {self.camera_index})")
            
            # Create camera with NO custom configuration
            self.picamera2 = Picamera2(camera_num=self.camera_index)
            
            # Use the most basic configuration possible
            config = self.picamera2.create_video_configuration()
            logger.info(f"📷 Using minimal config for {self.camera_name}")
            
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

class MinimalDualRecorder:
    """Minimal dual camera recorder"""
    
    def __init__(self):
        self.camera0_recorder = None
        self.camera1_recorder = None
        self.recording = False
        
    def detect_cameras(self):
        """Detect available cameras with minimal testing"""
        logger.info("🔍 Detecting cameras...")
        
        available_cameras = []
        
        # Test camera 0 with minimal setup
        try:
            test_cam = Picamera2(camera_num=0)
            test_cam.close()
            available_cameras.append(0)
            logger.info("✅ Camera 0 detected")
        except Exception as e:
            logger.warning(f"⚠️ Camera 0 not available: {e}")
        
        # Test camera 1 with minimal setup
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
                self.camera0_recorder = MinimalCameraRecorder(0, CAMERA_0_NAME, camera0_file)
                
                if not self.camera0_recorder.initialize_camera():
                    logger.error("❌ Camera 0 initialization failed")
                    self.camera0_recorder = None
            
            if 1 in available_cameras and len(available_cameras) > 1:
                camera1_file = recordings_dir / f"{filename_base}_cam2.mp4"
                self.camera1_recorder = MinimalCameraRecorder(1, CAMERA_1_NAME, camera1_file)
                
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

def load_bookings():
    """Load bookings from the bookings file"""
    try:
        if BOOKINGS_FILE.exists():
            import json
            with open(BOOKINGS_FILE, 'r') as f:
                bookings = json.load(f)
            logger.info(f"📋 Loaded {len(bookings)} bookings from cache")
            return bookings
        else:
            logger.warning("⚠️ No bookings file found")
            return []
    except Exception as e:
        logger.error(f"❌ Failed to load bookings: {e}")
        return []

def find_active_booking(bookings):
    """Find an active booking that should be recording now"""
    from datetime import datetime
    import pytz
    
    now = datetime.now(pytz.timezone('America/New_York'))
    logger.info(f"🔍 Checking {len(bookings)} bookings at {now}")
    
    for booking in bookings:
        try:
            start_time = datetime.fromisoformat(booking['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(booking['end_time'].replace('Z', '+00:00'))
            
            # Convert to local timezone
            start_time = start_time.astimezone(pytz.timezone('America/New_York'))
            end_time = end_time.astimezone(pytz.timezone('America/New_York'))
            
            logger.info(f"🔍 Booking {booking['id']}: {start_time} - {end_time}")
            logger.info(f"   Now: {now}")
            
            if start_time <= now <= end_time:
                logger.info(f"🎯 Active booking found: {booking['id']}")
                return booking
                
        except Exception as e:
            logger.error(f"❌ Error processing booking {booking.get('id', 'unknown')}: {e}")
    
    logger.info("❌ No active booking found")
    return None

def main():
    """Main service function - runs continuously"""
    logger.info("🎥 MINIMAL Dual Recorder Service Starting")
    
    # Create recorder
    recorder = MinimalDualRecorder()
    current_booking = None
    
    try:
        while True:
            # Load bookings
            bookings = load_bookings()
            
            # Find active booking
            active_booking = find_active_booking(bookings)
            
            if active_booking and not recorder.is_recording():
                # Start recording for active booking
                logger.info(f"🎬 Starting recording for booking: {active_booking['id']}")
                if recorder.start_recording_session(active_booking):
                    current_booking = active_booking
                    logger.info("✅ Recording started successfully")
                else:
                    logger.error("❌ Failed to start recording")
            
            elif not active_booking and recorder.is_recording():
                # Stop recording if no active booking
                logger.info("🛑 No active booking, stopping recording")
                recorder.stop_recording_session()
                current_booking = None
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
        if recorder.is_recording():
            recorder.stop_recording_session()
    except Exception as e:
        logger.error(f"❌ Service error: {e}")
        if recorder.is_recording():
            recorder.stop_recording_session()

if __name__ == "__main__":
    main()
