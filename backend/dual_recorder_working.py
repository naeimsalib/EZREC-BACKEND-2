#!/usr/bin/env python3
"""
WORKING DUAL RECORDER - Uses the exact same approach as the successful test script
This version replicates the working test script logic as a service
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
import pytz

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
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkingDualRecorder:
    def __init__(self):
        self.recording = False
        self.cameras = {}
        self.encoders = {}
        self.recording_threads = {}
        
    def detect_cameras(self):
        """Detect available cameras using the EXACT same method as the test script"""
        available_cameras = []
        
        for index in range(2):
            try:
                test_cam = Picamera2(camera_num=index)
                test_cam.close()
                available_cameras.append(index)
                logger.info(f"✅ Camera {index} detected")
            except Exception as e:
                logger.warning(f"⚠️ Camera {index} not available: {e}")
        
        logger.info(f"📷 Available cameras: {available_cameras}")
        return available_cameras
    
    def record_camera(self, camera_index, output_file, booking_id):
        """Record from a single camera - replicates the test script approach"""
        try:
            logger.info(f"🔧 Starting recording for camera {camera_index}")
            
            # Use the EXACT same approach as the working test script
            camera = Picamera2(camera_num=camera_index)
            config = camera.create_video_configuration()
            camera.configure(config)
            camera.start()
            
            # Create encoder
            encoder = H264Encoder()
            
            # Start recording
            camera.start_recording(encoder, str(output_file))
            
            self.cameras[camera_index] = camera
            self.encoders[camera_index] = encoder
            
            logger.info(f"✅ Camera {camera_index} started recording to {output_file}")
            
            # Record for the duration of the booking
            start_time = time.time()
            booking_duration = 10 * 60  # 10 minutes in seconds
            
            while self.recording and (time.time() - start_time) < booking_duration:
                time.sleep(1)
            
            # Stop recording
            camera.stop_recording()
            camera.stop()
            camera.close()
            
            logger.info(f"✅ Camera {camera_index} finished recording")
            
        except Exception as e:
            logger.error(f"❌ Camera {camera_index} recording failed: {e}")
    
    def start_recording_session(self, booking):
        """Start recording session using the test script approach"""
        logger.info(f"🎬 Starting recording session for booking: {booking['id']}")
        
        # Detect cameras
        logger.info("🔍 Detecting cameras...")
        available_cameras = self.detect_cameras()
        
        if not available_cameras:
            logger.error("❌ No cameras available")
            return False
        
        # Create recordings directory
        today = datetime.now().strftime("%Y-%m-%d")
        session_dir = RECORDINGS_DIR / today / f"session_{booking['id']}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Start recording using threads (like the test script)
        self.recording = True
        
        for camera_index in available_cameras:
            output_file = session_dir / f"camera_{camera_index}.mp4"
            
            # Start recording in a separate thread
            thread = threading.Thread(
                target=self.record_camera,
                args=(camera_index, output_file, booking['id'])
            )
            thread.daemon = True
            thread.start()
            
            self.recording_threads[camera_index] = thread
        
        logger.info("✅ Recording started successfully")
        return True
    
    def stop_recording_session(self):
        """Stop recording session"""
        if not self.recording:
            return
        
        logger.info("🛑 Stopping recording session")
        self.recording = False
        
        # Wait for threads to finish
        for camera_index, thread in self.recording_threads.items():
            try:
                thread.join(timeout=5)
                logger.info(f"✅ Camera {camera_index} thread finished")
            except Exception as e:
                logger.error(f"❌ Error stopping camera {camera_index} thread: {e}")
        
        self.recording_threads.clear()
        self.cameras.clear()
        self.encoders.clear()
        logger.info("✅ Recording stopped")
    
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
    if not bookings:
        return None
    
    now = datetime.now(pytz.timezone('America/New_York'))
    logger.info(f"🔍 Checking {len(bookings)} bookings at {now}")
    
    for booking in bookings:
        try:
            start_time = datetime.fromisoformat(booking['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(booking['end_time'].replace('Z', '+00:00'))
            
            logger.info(f"🔍 Booking {booking['id']}: {start_time} - {end_time}")
            logger.info(f"   Now: {now}")
            
            if start_time <= now <= end_time:
                logger.info(f"🎯 Active booking found: {booking['id']}")
                return booking
        except Exception as e:
            logger.error(f"❌ Error parsing booking {booking.get('id', 'unknown')}: {e}")
            continue
    
    logger.info("❌ No active booking found")
    return None

def main():
    """Main service function - runs continuously"""
    logger.info("🎥 WORKING Dual Recorder Service Starting")
    
    # Create recorder
    recorder = WorkingDualRecorder()
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
