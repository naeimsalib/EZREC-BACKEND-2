#!/usr/bin/env python3
"""
Main Recording Service - Dual Camera Support
- Reads bookings from bookings_cache.json
- Starts/stops recordings at scheduled times (local timezone)
- Records from both cameras in parallel using threading
- Saves raw recordings to /opt/ezrec-backend/recordings/
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

# 🔧 Set up logging FIRST before any functions that use logger
LOG_DIR = "/opt/ezrec-backend/logs"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "recorder.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("recorder")

# 🔧 Set up basic configuration variables
RESOLUTION = os.getenv('RESOLUTION', '1280x720')
try:
    width, height = map(int, RESOLUTION.lower().split('x'))
except Exception:
    width, height = 1280, 720

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput

    def safe_init_camera(camera_serial=None, retries=3, delay=3):
        """Initialize a camera with the specified serial number"""
        for i in range(retries):
            try:
                camera = Picamera2()
                
                # If camera serial is specified, configure it
                if camera_serial:
                    # Get camera info and find the one with matching serial
                    camera_info = camera.camera_properties
                    if 'SerialNumber' in camera_info and camera_info['SerialNumber'] != camera_serial:
                        camera.close()
                        raise RuntimeError(f"Camera serial mismatch. Expected: {camera_serial}, Got: {camera_info['SerialNumber']}")
                    logger.info(f"✅ Initialized camera with serial: {camera_serial}")
                else:
                    logger.info("✅ Initialized default camera")
                    
                return camera
            except RuntimeError as e:
                if "Camera __init__ sequence did not complete" in str(e):
                    logger.warning(f"⚠️ Camera busy (try {i+1}/{retries})... retrying in {delay}s")
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError("❌ Camera failed to initialize after multiple attempts")

    def get_camera_serials():
        """Get camera serials from environment variables with fallback logic"""
        cam1_serial = os.getenv('CAMERA_1_SERIAL')
        cam2_serial = os.getenv('CAMERA_2_SERIAL')
        
        if not cam1_serial and not cam2_serial:
            logger.warning("⚠️ No camera serials configured. Using single camera mode.")
            return None, None
        
        if not cam1_serial:
            logger.warning("⚠️ CAMERA_1_SERIAL not configured. Using single camera mode.")
            return None, cam2_serial
        
        if not cam2_serial:
            logger.warning("⚠️ CAMERA_2_SERIAL not configured. Using single camera mode.")
            return cam1_serial, None
        
        logger.info(f"🔍 Dual camera mode: CAMERA_1_SERIAL={cam1_serial}, CAMERA_2_SERIAL={cam2_serial}")
        return cam1_serial, cam2_serial

    def test_camera_availability(camera_serial, camera_name):
        """Test if a camera is available and working"""
        try:
            logger.info(f"🔍 Testing {camera_name} availability (serial: {camera_serial})")
            camera = Picamera2()
            
            # Get camera info
            camera_info = camera.camera_properties
            actual_serial = camera_info.get('SerialNumber', 'Unknown')
            
            if camera_serial and actual_serial != camera_serial:
                logger.warning(f"⚠️ {camera_name} serial mismatch. Expected: {camera_serial}, Got: {actual_serial}")
                camera.close()
                return False
            
            # Test basic configuration
            config = camera.create_video_configuration(
                main={"size": (width, height), "format": "YUV420"},
                controls={
                    "FrameDurationLimits": (33333, 1000000),
                    "ExposureTime": 33333,
                    "AnalogueGain": 1.0
                }
            )
            
            camera.configure(config)
            camera.start()
            camera.stop()
            camera.close()
            
            logger.info(f"✅ {camera_name} is available and working")
            return True
            
        except Exception as e:
            logger.error(f"❌ {camera_name} is not available: {e}")
            return False

    def get_available_cameras():
        """Get list of available cameras with fallback logic"""
        cam1_serial, cam2_serial = get_camera_serials()
        available_cameras = []
        
        if cam1_serial and test_camera_availability(cam1_serial, "Camera 1"):
            available_cameras.append(("Camera 1", cam1_serial))
        
        if cam2_serial and test_camera_availability(cam2_serial, "Camera 2"):
            available_cameras.append(("Camera 2", cam2_serial))
        
        if not available_cameras:
            logger.error("❌ No cameras are available. Cannot start recording.")
            return []
        
        logger.info(f"✅ Available cameras: {[name for name, _ in available_cameras]}")
        return available_cameras

except ImportError:
    Picamera2 = None

dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

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
RAW_DIR = Path(os.getenv('RAW_RECORDINGS_DIR', '/opt/ezrec-backend/recordings/'))
LOG_FILE = Path(os.getenv('RECORDER_LOG', '/opt/ezrec-backend/logs/recorder.log'))
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))
# 🔧 Resolution already parsed at the top of the file

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

# 🔧 Logging already set up at the top of the file

RAW_DIR.mkdir(parents=True, exist_ok=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info(f"📡 Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
logger.info(f"🎥 Resolution configured: {width}x{height}")
logger.info(f"🔧 Environment loaded from: {dotenv_path}")

def handle_exit(sig, frame):
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    # If we're currently recording, try to stop gracefully
    if 'current_session' in globals() and current_session and current_session.active:
        logger.info("🛑 Stopping active recording before exit...")
        try:
            current_session.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping recording during exit: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def set_is_recording(value: bool):
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

def repair_mp4_file(file_path: Path) -> bool:
    """
    Attempt to repair a corrupted MP4 file using FFmpeg.
    Returns True if repair was successful, False otherwise.
    """
    try:
        import subprocess
        
        # Create a backup of the original file
        backup_path = file_path.with_suffix('.mp4.backup')
        file_path.rename(backup_path)
        
        # Try to repair using FFmpeg
        result = subprocess.run([
            'ffmpeg', '-i', str(backup_path), '-c', 'copy', '-avoid_negative_ts', 'make_zero',
            str(file_path)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and file_path.exists():
            logger.info(f"✅ Successfully repaired MP4 file: {file_path}")
            # Remove backup if repair was successful
            backup_path.unlink()
            return True
        else:
            logger.error(f"❌ Failed to repair MP4 file: {result.stderr}")
            # Restore original file
            if backup_path.exists():
                backup_path.rename(file_path)
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during MP4 repair: {e}")
        # Restore original file if backup exists
        backup_path = file_path.with_suffix('.mp4.backup')
        if backup_path.exists():
            backup_path.rename(file_path)
        return False

class CameraRecordingThread:
    """Thread for recording from a single camera"""
    def __init__(self, camera_serial, output_path, duration, camera_name="unknown"):
        self.camera_serial = camera_serial
        self.output_path = output_path
        self.duration = duration
        self.camera_name = camera_name
        self.camera = None
        self.encoder = None
        self.success = False
        self.error = None
        self.thread = None

    def record(self):
        """Record from this camera for the specified duration"""
        try:
            logger.info(f"🎥 Starting recording from {self.camera_name} (serial: {self.camera_serial})")
            
            # Initialize camera
            self.camera = safe_init_camera(camera_serial=self.camera_serial)
            
            # Create camera configuration optimized for reliable recording
            config = self.camera.create_video_configuration(
                main={"size": (width, height), "format": "YUV420"},
                controls={
                    "FrameDurationLimits": (33333, 1000000),  # 1-30fps
                    "ExposureTime": 33333,  # 1/30 second
                    "AnalogueGain": 1.0,
                    "NoiseReductionMode": 0  # Disable noise reduction for stability
                }
            )
            
            self.camera.configure(config)
            self.camera.start()
            
            # Create encoder with settings optimized for reliable MP4 output
            self.encoder = H264Encoder(
                bitrate=4000000,  # 4Mbps (reduced for stability)
                repeat=False,
                iperiod=30,
                qp=30,  # Higher QP for stability
                profile="baseline",  # Use baseline profile for compatibility
                level="4.1"  # Specify H.264 level
            )
            
            # Start recording
            self.camera.start_recording(self.encoder, str(self.output_path))
            
            # Wait for recording duration
            time.sleep(self.duration)
            
            # Stop recording
            self.camera.stop_recording()
            time.sleep(2.0)  # Give time for file finalization
            
            # Stop and close camera
            self.camera.stop()
            self.camera.close()
            
            self.success = True
            logger.info(f"✅ Completed recording from {self.camera_name}: {self.output_path}")
            
        except Exception as e:
            self.error = str(e)
            logger.error(f"❌ Recording failed for {self.camera_name}: {e}")
            if self.camera:
                try:
                    self.camera.close()
                except:
                    pass

    def start(self):
        """Start the recording thread"""
        self.thread = threading.Thread(target=self.record)
        self.thread.start()

    def join(self):
        """Wait for the recording thread to complete"""
        if self.thread:
            self.thread.join()

class DualRecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RAW_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        self.date_folder.mkdir(parents=True, exist_ok=True)
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        
        # File paths for dual camera setup
        self.cam1_filepath = self.date_folder / (self.filename_base + "_cam1.mp4")
        self.cam2_filepath = self.date_folder / (self.filename_base + "_cam2.mp4")
        self.merged_filepath = self.date_folder / (self.filename_base + "_merged.mp4")
        
        # Use merged filepath as the main output for compatibility
        self.final_filepath = self.merged_filepath
        
        self.lockfile = self.final_filepath.with_suffix(".lock")
        self.completed_marker = self.final_filepath.with_suffix(".done")
        self.active = False
        self.recording_start_time = None
        self.camera_threads = []
        self.camera_errors = {}

    def start(self):
        try:
            self.lockfile.touch()
            logger.info(f"🎬 Starting dual camera recording session: {self.filename_base}")
            
            # Get available cameras with fallback logic
            available_cameras = get_available_cameras()
            
            if not available_cameras:
                logger.error("❌ No cameras available. Cannot start recording.")
                return False
            
            # Log camera availability
            if len(available_cameras) == 1:
                logger.warning(f"⚠️ Only one camera available: {available_cameras[0][0]}. Using single camera mode.")
            else:
                logger.info(f"✅ {len(available_cameras)} cameras available for recording.")
            
            # Calculate recording duration
            start_dt = parser.isoparse(self.booking["start_time"]).astimezone(LOCAL_TZ)
            end_dt = parser.isoparse(self.booking["end_time"]).astimezone(LOCAL_TZ)
            duration = (end_dt - datetime.now(LOCAL_TZ)).total_seconds()
            
            if duration <= 0:
                logger.warning("⚠️ Recording duration is 0 or negative. Using minimum duration.")
                duration = 10  # Minimum 10 seconds
            
            # Create camera recording threads based on available cameras
            self.camera_threads = []
            
            for i, (camera_name, camera_serial) in enumerate(available_cameras):
                if i == 0:
                    output_path = self.cam1_filepath
                elif i == 1:
                    output_path = self.cam2_filepath
                else:
                    # Fallback for additional cameras
                    output_path = self.date_folder / f"{self.filename_base}_cam{i+1}.mp4"
                
                thread = CameraRecordingThread(
                    camera_serial=camera_serial,
                    output_path=output_path,
                    duration=duration,
                    camera_name=camera_name
                )
                self.camera_threads.append(thread)
            
            # Start all camera threads
            logger.info(f"🎥 Starting {len(self.camera_threads)} camera recording threads...")
            for thread in self.camera_threads:
                thread.start()
            
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)
            logger.info(f"✅ Started dual camera recording: {len(self.camera_threads)} cameras active")
            
            # Update booking status
            update_booking_status(self.booking["id"], "Recording")
            supabase.table('cameras').update({
                'is_recording': True,
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                'status': 'online'
            }).eq('id', CAMERA_ID).execute()
            set_is_recording(True)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start dual camera recording: {e}")
            if self.lockfile.exists():
                self.lockfile.unlink()
            return False

    def stop(self):
        logger.info("🛑 Stopping dual camera recording session")
        try:
            if self.active:
                # Wait for all camera threads to complete
                logger.info("⏳ Waiting for camera recording threads to complete...")
                for thread in self.camera_threads:
                    thread.join()
                
                self.active = False
                logger.info(f"⏹️ Stopped dual camera recording: {self.filename_base}")

                # Check recording results
                successful_recordings = []
                for thread in self.camera_threads:
                    if thread.success:
                        successful_recordings.append(thread.output_path)
                    else:
                        self.camera_errors[thread.camera_name] = thread.error
                        logger.warning(f"⚠️ {thread.camera_name} recording failed: {thread.error}")

                # Create .done file if at least one camera recorded successfully
                if successful_recordings:
                    # Check if files exist and are not corrupted
                    valid_files = []
                    for file_path in successful_recordings:
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            logger.info(f"📹 {file_path.name} size: {file_size} bytes")
                            
                            if file_size > 100 * 1024:  # 100KB minimum
                                # Try to validate the MP4 file
                                mp4_valid = False
                                try:
                                    import subprocess
                                    result = subprocess.run(
                                        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(file_path)],
                                        capture_output=True, text=True, timeout=10
                                    )
                                    if result.returncode == 0:
                                        mp4_valid = True
                                        logger.info(f"✅ {file_path.name} validation passed")
                                    else:
                                        logger.warning(f"⚠️ {file_path.name} validation failed")
                                except Exception as e:
                                    logger.warning(f"⚠️ Could not validate {file_path.name}: {e}")
                                
                                # If MP4 is corrupted, try to repair it
                                if not mp4_valid:
                                    logger.info(f"🔧 Attempting to repair {file_path.name}...")
                                    if repair_mp4_file(file_path):
                                        logger.info(f"✅ Successfully repaired {file_path.name}")
                                        mp4_valid = True
                                    else:
                                        logger.warning(f"⚠️ Could not repair {file_path.name}")
                                
                                if mp4_valid:
                                    valid_files.append(file_path)
                                else:
                                    logger.warning(f"⚠️ {file_path.name} is corrupted and could not be repaired")
                            else:
                                logger.warning(f"⚠️ {file_path.name} too small: {file_size} bytes")
                        else:
                            logger.warning(f"⚠️ {file_path.name} not found after recording")
                    
                    # Create .done file if we have valid recordings
                    if valid_files:
                        self.completed_marker.touch()
                        logger.info(f"✅ Marked {len(valid_files)} valid recordings for processing: {self.completed_marker}")
                    else:
                        logger.error("❌ No valid recordings created. Skipping .done creation.")
                else:
                    logger.error("❌ No cameras recorded successfully. Skipping .done creation.")

                # Remove lock file
                if self.lockfile.exists():
                    self.lockfile.unlink()
                    logger.info(f"🔓 Removed lock file: {self.lockfile}")

                # Save metadata file with camera information
                try:
                    metadata_path = self.final_filepath.with_suffix(".json")
                    metadata = {
                        "booking_id": self.booking["id"],
                        "user_id": self.booking.get("user_id"),
                        "camera_id": self.booking.get("camera_id"),
                        "start_time": self.booking["start_time"],
                        "end_time": self.booking["end_time"],
                        "recording_start": self.recording_start_time.isoformat() if self.recording_start_time else None,
                        "recording_end": datetime.now(LOCAL_TZ).isoformat(),
                        "file_path": str(self.final_filepath),
                        "dual_camera": True,
                        "cameras_configured": len(self.camera_threads),
                        "cameras_successful": len([t for t in self.camera_threads if t.success]),
                        "camera_errors": self.camera_errors,
                        "cam1_file": str(self.cam1_filepath) if self.cam1_filepath.exists() else None,
                        "cam2_file": str(self.cam2_filepath) if self.cam2_filepath.exists() else None,
                        "cam1_size": self.cam1_filepath.stat().st_size if self.cam1_filepath.exists() else 0,
                        "cam2_size": self.cam2_filepath.stat().st_size if self.cam2_filepath.exists() else 0
                    }
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, indent=2)
                    logger.info(f"📝 Metadata saved to: {metadata_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to save metadata: {e}")

                # Update Supabase booking status
                try:
                    update_booking_status(self.booking["id"], "RecordingFinished")
                    logger.info(f"📡 Updated booking status to RecordingFinished for booking ID: {self.booking['id']}")
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
            logger.error(f"❌ Error stopping dual camera recording: {e}")
            self.active = False

def get_active_booking(bookings):
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
    if not BOOKING_CACHE_FILE.exists():
        return []
    try:
        with open(BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def main():
    current_session = None
    while True:
        try:
            bookings = load_bookings()
            now = datetime.now(LOCAL_TZ)
            active_booking = get_active_booking(bookings)
            
            if current_session:
                end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
                # Only log if a recording actually started
                if current_session.recording_start_time:
                    logger.info(
                        f"Now: {now.isoformat()}, Booking end: {end_time.isoformat()}, "
                        f"Should stop: {now > end_time}, Session started: {current_session.recording_start_time.isoformat()}"
                    )
                # Only stop if end time has passed and at least 10 seconds have elapsed
                min_duration = 10  # seconds
                elapsed = (now - current_session.recording_start_time).total_seconds() if current_session.recording_start_time else 0
                if now > end_time and elapsed > min_duration:
                    logger.info(f"Stopping session: now={now}, end_time={end_time}, elapsed={elapsed}s")
                    current_session.stop()
                    current_session = None
                    
            if not current_session and active_booking:
                current_session = DualRecordingSession(active_booking)
                if not current_session.start():
                    current_session = None
                    
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
