#!/usr/bin/env python3
"""
EZREC Dual Camera Recorder - Clean Architecture
- Uses CameraManager for reliable camera detection
- Records from both cameras simultaneously using threads
- Merges recordings using FFmpeg
- Robust error handling and logging
"""

import os
import sys
import time
import json
import logging
import signal
import pytz
import psutil
import threading
import subprocess
from pathlib import Path
from dateutil import parser
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# 🔧 Ensure API utils can be imported
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

# Load environment
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

# Environment variables
TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE") or os.getenv("SYSTEM_TIMEZONE") or "UTC"
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)

REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"❌ Missing required environment variables: {missing}")
    sys.exit(1)

USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
RECORDINGS_DIR = Path('/opt/ezrec-backend/recordings/')
LOG_FILE = Path('/opt/ezrec-backend/logs/dual_recorder.log')
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))

# Camera configuration
CAMERA_0_SERIAL = os.getenv('CAMERA_0_SERIAL', '88000')
CAMERA_1_SERIAL = os.getenv('CAMERA_1_SERIAL', '80000')
CAMERA_0_NAME = os.getenv('CAMERA_0_NAME', 'left')
CAMERA_1_NAME = os.getenv('CAMERA_1_NAME', 'right')
DUAL_CAMERA_MODE = os.getenv('DUAL_CAMERA_MODE', 'true').lower() == 'true'
MERGE_METHOD = os.getenv('MERGE_METHOD', 'side_by_side')

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'dual_recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ dual_recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
logger.info(f"🎬 Merge method: {MERGE_METHOD}")

def set_is_recording(value: bool):
    """Update recording status in status.json"""
    try:
        status_path = Path("/opt/ezrec-backend/status.json")
        status = {}
        if status_path.exists():
            try:
                with open(status_path) as f:
                    status = json.load(f)
            except Exception:
                status = {}
        status["is_recording"] = value
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to update recording status: {e}")

def detect_cameras():
    """Detect available cameras using CameraManager and return camera indices"""
    try:
        from picamera2 import CameraManager, Picamera2
        
        manager = CameraManager()
        cameras = manager.cameras
        
        logger.info(f"🔍 Detected {len(cameras)} camera(s)")
        
        if len(cameras) < 2:
            logger.warning(f"⚠️ Only {len(cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return None, None
        
        # Get camera properties to match serials
        camera_0_index = None
        camera_1_index = None
        
        for i in range(len(cameras)):
            try:
                # Create temporary Picamera2 instance to get properties
                temp_cam = Picamera2(index=i)
                props = temp_cam.camera_properties
                temp_cam.close()
                
                serial = props.get('SerialNumber', f'unknown_{i}')
                logger.info(f"📷 Camera {i}: Serial {serial}")
                
                if serial == CAMERA_0_SERIAL:
                    camera_0_index = i
                    logger.info(f"✅ Matched Camera 0 ({CAMERA_0_NAME}) to camera index {i}")
                elif serial == CAMERA_1_SERIAL:
                    camera_1_index = i
                    logger.info(f"✅ Matched Camera 1 ({CAMERA_1_NAME}) to camera index {i}")
                    
            except Exception as e:
                logger.error(f"❌ Error getting properties for camera {i}: {e}")
        
        if camera_0_index is not None and camera_1_index is not None:
            logger.info("✅ Both cameras detected and matched to serials")
            return camera_0_index, camera_1_index
        else:
            logger.warning("⚠️ Could not match cameras to configured serials")
            # Fallback: use first two cameras
            if len(cameras) >= 2:
                logger.info("🔄 Using first two cameras as fallback")
                return 0, 1
            else:
                logger.error("❌ Not enough cameras available")
                return None, None
                
    except ImportError as e:
        logger.error(f"❌ Picamera2 not available: {e}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Camera detection failed: {e}")
        return None, None

class CameraRecorder:
    """Thread-safe camera recorder for a single camera"""
    
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
        
        # Set up logging for this camera
        self.log_file = f"/tmp/{camera_name.lower()}_camera_debug.log"
        self.logger = self._setup_camera_logger()
    
    def _setup_camera_logger(self):
        """Set up dedicated logger for this camera"""
        logger = logging.getLogger(f"{self.camera_name.lower()}_camera")
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def initialize_camera(self):
        """Initialize the camera with proper configuration"""
        try:
            self.logger.info(f"🔧 Initializing {self.camera_name} camera (index: {self.camera_index})")
            
            # Create Picamera2 instance using camera index
            self.picamera2 = Picamera2(index=self.camera_index)
            
            # Configure camera
            config = self.picamera2.create_video_configuration(
                main={"size": (1920, 1080), "format": "YUV420"},
                controls={
                    "FrameDurationLimits": (33333, 1000000),
                    "ExposureTime": 33333,
                    "AnalogueGain": 1.0,
                    "NoiseReductionMode": 0
                }
            )
            
            self.picamera2.configure(config)
            self.picamera2.start()
            
            # Create encoder
            from picamera2.encoders import H264Encoder
            self.encoder = H264Encoder(
                bitrate=6000000,
                repeat=False,
                iperiod=30,
                qp=25
            )
            
            self.logger.info(f"✅ {self.camera_name} camera initialized successfully")
            return True
            
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ {self.camera_name} camera initialization failed: {e}")
            return False
    
    def start_recording(self):
        """Start recording in a separate thread"""
        if self.thread and self.thread.is_alive():
            self.logger.warning(f"⚠️ {self.camera_name} camera already recording")
            return False
        
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def _record_loop(self):
        """Main recording loop"""
        try:
            if not self.initialize_camera():
                return
            
            self.logger.info(f"🎥 Starting {self.camera_name} camera recording")
            self.recording = True
            
            # Start recording
            self.picamera2.start_recording(self.encoder, str(self.output_path))
            
            # Keep recording until stopped
            while self.recording:
                time.sleep(1)
                # Log progress every 10 seconds
                if int(time.time()) % 10 == 0:
                    if self.output_path.exists():
                        size = self.output_path.stat().st_size
                        self.logger.info(f"📹 {self.camera_name} recording: {size} bytes")
            
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ {self.camera_name} camera recording error: {e}")
        finally:
            self.stop_recording_internal()
    
    def stop_recording(self):
        """Stop recording"""
        self.recording = False
        if self.thread:
            self.thread.join(timeout=10)
    
    def stop_recording_internal(self):
        """Internal method to stop recording"""
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    time.sleep(2)  # Give time for file finalization
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
            
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
                self.success = True
            else:
                self.logger.error(f"❌ {self.camera_name} recording file not found")
                
        except Exception as e:
            self.logger.error(f"❌ Error stopping {self.camera_name} camera: {e}")

def merge_videos(video1_path: Path, video2_path: Path, output_path: Path, method: str = 'side_by_side'):
    """Merge two video files using FFmpeg"""
    try:
        if method == 'side_by_side':
            # Side-by-side merge
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                str(output_path)
            ]
        elif method == 'stacked':
            # Top-bottom merge
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]vstack=inputs=2[v]',
                '-map', '[v]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                str(output_path)
            ]
        else:
            raise ValueError(f"Unknown merge method: {method}")

        logger.info(f"🎬 Merging videos using {method} method...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            logger.info(f"✅ Successfully merged videos: {output_path}")
            return True
        else:
            logger.error(f"❌ Failed to merge videos: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error merging videos: {e}")
        return False

class DualRecordingSession:
    """Manages dual camera recording session"""
    
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RECORDINGS_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        
        # Create recordings directory
        try:
            self.date_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created/verified recordings directory: {self.date_folder}")
        except PermissionError as e:
            logger.error(f"❌ Permission denied creating {self.date_folder}: {e}")
            logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create recordings directory {self.date_folder}: {e}")
            raise
        
        # Parse booking times
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        
        # File paths
        self.camera0_file = self.date_folder / f"{self.filename_base}_{CAMERA_0_NAME}.mp4"
        self.camera1_file = self.date_folder / f"{self.filename_base}_{CAMERA_1_NAME}.mp4"
        self.merged_file = self.date_folder / f"{self.filename_base}_merged.mp4"
        
        # Camera recorders
        self.camera0_recorder = None
        self.camera1_recorder = None
        self.active = False
        self.recording_start_time = None

    def start(self):
        """Start dual camera recording"""
        try:
            logger.info(f"🎬 Starting dual camera recording session: {self.filename_base}")
            
            # Detect cameras
            camera0_index, camera1_index = detect_cameras()
            if camera0_index is None or camera1_index is None:
                logger.error("❌ Failed to detect cameras")
                return False
            
            # Create camera recorders
            self.camera0_recorder = CameraRecorder(camera0_index, CAMERA_0_NAME, self.camera0_file)
            self.camera1_recorder = CameraRecorder(camera1_index, CAMERA_1_NAME, self.camera1_file)
            
            # Start recording on both cameras
            logger.info("🎥 Starting camera recordings...")
            
            if not self.camera0_recorder.start_recording():
                logger.error("❌ Failed to start camera 0 recording")
                return False
            
            if not self.camera1_recorder.start_recording():
                logger.error("❌ Failed to start camera 1 recording")
                self.camera0_recorder.stop_recording()
                return False
            
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)
            logger.info("✅ Dual camera recording started successfully")
            
            # Update booking status
            try:
                update_booking_status(self.booking["id"], "Recording")
                logger.info(f"📡 Updated booking status to Recording")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
            # Update camera status
            try:
                supabase.table('cameras').update({
                    'is_recording': True,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'online'
                }).eq('id', CAMERA_ID).execute()
                logger.info(f"📡 Updated camera status")
            except Exception as e:
                logger.error(f"❌ Failed to update camera status: {e}")
            
            set_is_recording(True)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording session: {e}")
            return False

    def stop(self):
        """Stop dual camera recording"""
        logger.info("🛑 Stopping dual camera recording")
        
        try:
            # Stop camera recordings
            if self.camera0_recorder:
                self.camera0_recorder.stop_recording()
            if self.camera1_recorder:
                self.camera1_recorder.stop_recording()
            
            self.active = False
            
            # Wait for files to be finalized
            time.sleep(3)
            
            # Check recording results
            logger.info("🔍 Checking camera recording files...")
            
            cam0_success = self.camera0_recorder.success if self.camera0_recorder else False
            cam1_success = self.camera1_recorder.success if self.camera1_recorder else False
            
            if self.camera0_file.exists():
                cam0_size = self.camera0_file.stat().st_size
                logger.info(f"✅ {CAMERA_0_NAME} recording: {self.camera0_file.name} ({cam0_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_0_NAME} recording file missing: {self.camera0_file}")
            
            if self.camera1_file.exists():
                cam1_size = self.camera1_file.stat().st_size
                logger.info(f"✅ {CAMERA_1_NAME} recording: {self.camera1_file.name} ({cam1_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_1_NAME} recording file missing: {self.camera1_file}")
            
            # Merge videos if both cameras recorded successfully
            if cam0_success and cam1_success:
                logger.info("✅ Both camera recordings completed")
                
                if merge_videos(self.camera0_file, self.camera1_file, self.merged_file, MERGE_METHOD):
                    logger.info(f"✅ Successfully created merged video: {self.merged_file}")
                    
                    # Create .done marker for video worker
                    done_marker = self.merged_file.with_suffix('.done')
                    done_marker.touch()
                    
                    # Save metadata
                    self.save_metadata()
                    
                    # Clean up individual camera files
                    self.camera0_file.unlink(missing_ok=True)
                    self.camera1_file.unlink(missing_ok=True)
                    
                else:
                    logger.error("❌ Failed to merge videos")
            else:
                logger.warning("⚠️ One or both camera recordings failed")
                # Create error marker to prevent infinite retries
                error_marker = self.merged_file.with_suffix('.error')
                error_marker.touch()
                logger.error("🔧 Created .error marker to prevent infinite retries")
            
            # Update booking status
            try:
                update_booking_status(self.booking["id"], "RecordingFinished")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
            # Update camera status
            try:
                supabase.table('cameras').update({
                    'is_recording': False,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'online'
                }).eq('id', CAMERA_ID).execute()
                set_is_recording(False)
            except Exception as e:
                logger.error(f"❌ Failed to update camera status: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error stopping dual recording: {e}")

    def save_metadata(self):
        """Save metadata for the merged recording"""
        try:
            metadata_path = self.merged_file.with_suffix(".json")
            metadata = {
                "booking_id": self.booking["id"],
                "user_id": self.booking.get("user_id"),
                "camera_id": self.booking.get("camera_id"),
                "start_time": self.booking["start_time"],
                "end_time": self.booking["end_time"],
                "recording_start": self.recording_start_time.isoformat() if self.recording_start_time else None,
                "recording_end": datetime.now(LOCAL_TZ).isoformat(),
                "file_path": str(self.merged_file),
                "file_size": self.merged_file.stat().st_size if self.merged_file.exists() else 0,
                "camera_0_serial": CAMERA_0_SERIAL,
                "camera_1_serial": CAMERA_1_SERIAL,
                "merge_method": MERGE_METHOD,
                "dual_camera": True
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"📝 Metadata saved to: {metadata_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    if 'current_session' in globals() and current_session and current_session.active:
        logger.info("🛑 Stopping active recording before exit...")
        try:
            current_session.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping recording during exit: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def get_active_booking(bookings):
    """Get the currently active booking"""
    now = datetime.now(LOCAL_TZ)
    for booking in bookings:
        try:
            start_time = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
            end_time = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        except Exception:
            continue
        if booking.get("user_id") == USER_ID and booking.get("camera_id") == CAMERA_ID and start_time <= now <= end_time:
            return booking
    return None

def load_bookings():
    """Load bookings from cache file"""
    if not BOOKING_CACHE_FILE.exists():
        return []
    try:
        with open(BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def validate_camera_setup():
    """Validate camera setup and return detailed information"""
    try:
        from picamera2 import CameraManager, Picamera2
        
        logger.info("🔍 Validating camera setup...")
        
        # Check CameraManager
        manager = CameraManager()
        cameras = manager.cameras
        logger.info(f"📷 CameraManager reports {len(cameras)} camera(s)")
        
        if len(cameras) < 2:
            logger.error(f"❌ Only {len(cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return False
        
        # Test each camera individually
        for i in range(len(cameras)):
            try:
                logger.info(f"🔧 Testing camera {i}...")
                camera = Picamera2(index=i)
                
                # Get camera properties
                props = camera.camera_properties
                serial = props.get('SerialNumber', f'unknown_{i}')
                logger.info(f"📷 Camera {i}: Serial {serial}")
                
                # Test basic configuration
                config = camera.create_video_configuration(
                    main={"size": (1920, 1080), "format": "YUV420"}
                )
                camera.configure(config)
                camera.start()
                camera.stop()
                camera.close()
                
                logger.info(f"✅ Camera {i} is working correctly")
                
            except Exception as e:
                logger.error(f"❌ Camera {i} test failed: {e}")
                return False
        
        # Check environment variables
        logger.info(f"🔧 Environment configuration:")
        logger.info(f"   CAMERA_0_SERIAL: {CAMERA_0_SERIAL}")
        logger.info(f"   CAMERA_1_SERIAL: {CAMERA_1_SERIAL}")
        logger.info(f"   CAMERA_0_NAME: {CAMERA_0_NAME}")
        logger.info(f"   CAMERA_1_NAME: {CAMERA_1_NAME}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Picamera2 not available: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Camera validation failed: {e}")
        return False

def main():
    """Main application loop"""
    logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
    logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
    logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
    logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
    logger.info(f"🎬 Merge method: {MERGE_METHOD}")
    
    # Validate camera setup
    if not validate_camera_setup():
        logger.error("❌ Camera setup validation failed. Exiting.")
        sys.exit(1)
    
    # Verify recordings directory permissions
    try:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = RECORDINGS_DIR / "test_write.tmp"
        test_file.touch()
        test_file.unlink()
        logger.info(f"✅ Recordings directory is writable: {RECORDINGS_DIR}")
    except PermissionError as e:
        logger.error(f"❌ Permission denied accessing recordings directory: {RECORDINGS_DIR}")
        logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to access recordings directory: {RECORDINGS_DIR} - {e}")
        sys.exit(1)
    
    # Verify camera configuration
    if not CAMERA_0_SERIAL or CAMERA_0_SERIAL == "auto":
        logger.error("❌ CAMERA_0_SERIAL not properly configured")
        sys.exit(1)
    if not CAMERA_1_SERIAL or CAMERA_1_SERIAL == "auto":
        logger.error("❌ CAMERA_1_SERIAL not properly configured")
        sys.exit(1)
    
    logger.info("✅ Camera configuration verified")
    
    current_session = None
    
    while True:
        try:
            bookings = load_bookings()
            now = datetime.now(LOCAL_TZ)
            active_booking = get_active_booking(bookings)
            
            if current_session:
                end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
                if now > end_time:
                    logger.info(f"🛑 Booking ended, stopping recording")
                    current_session.stop()
                    current_session = None
                    
            if not current_session and active_booking:
                logger.info(f"🎬 Starting recording for booking: {active_booking['id']}")
                current_session = DualRecordingSession(active_booking)
                if not current_session.start():
                    logger.error(f"❌ Failed to start recording session")
                    current_session = None
                    
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 