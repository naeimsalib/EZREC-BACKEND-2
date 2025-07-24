#!/usr/bin/env python3
"""
Main Recording Service
- Reads bookings from bookings_cache.json
- Starts/stops recordings at scheduled times (local timezone)
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

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput

    def safe_init_camera(retries=3, delay=3, camera_serial=None):
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
                    print(f"⚠️ Camera busy (try {i+1}/{retries})... retrying in {delay}s")
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError("❌ Camera failed to initialize after multiple attempts")

    def get_camera_serial():
        """Get the camera serial number from environment or detect available cameras"""
        # Check if specific camera serial is configured
        camera_serial = os.getenv('CAMERA_SERIAL')
        if camera_serial:
            return camera_serial
        
        # If no specific serial, try to detect cameras
        try:
            import subprocess
            result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'serial' in line.lower():
                        # Extract serial number from output
                        import re
                        match = re.search(r'serial[:\s]+([a-f0-9]+)', line, re.IGNORECASE)
                        if match:
                            return match.group(1)
        except Exception as e:
            logger.warning(f"Could not detect camera serial: {e}")
        
        return None
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
RESOLUTION = os.getenv('RESOLUTION', '1280x720')
try:
    width, height = map(int, RESOLUTION.lower().split('x'))
except Exception:
    width, height = 1280, 720

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

RAW_DIR.mkdir(parents=True, exist_ok=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info(f"📡 Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")

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

class RecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RAW_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        self.date_folder.mkdir(parents=True, exist_ok=True)
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        self.final_filepath = self.date_folder / (self.filename_base + ".mp4")
        self.lockfile = self.final_filepath.with_suffix(".lock")
        self.completed_marker = self.final_filepath.with_suffix(".done")
        self.active = False
        self.recording_start_time = None
        self.camera = None
        self.encoder = None

    def start(self):
        try:
            self.lockfile.touch()
            logger.info(f"Starting direct recording to {self.final_filepath}")
            
            # Get camera serial for this specific camera
            camera_serial = get_camera_serial()
            if camera_serial:
                logger.info(f"🔍 Using camera with serial: {camera_serial}")
            
            # Initialize camera directly with serial
            self.camera = safe_init_camera(camera_serial=camera_serial)
            
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
            self.camera.start_recording(self.encoder, str(self.final_filepath))
            
            # Wait longer to ensure recording has started properly
            time.sleep(1.0)
            
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)
            logger.info(f"✅ Started recording: {self.final_filepath}")
            update_booking_status(self.booking["id"], "Recording")
            supabase.table('cameras').update({
                'is_recording': True,
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                'status': 'online'
            }).eq('id', CAMERA_ID).execute()
            set_is_recording(True)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            if self.lockfile.exists():
                self.lockfile.unlink()
            if self.camera:
                try:
                    self.camera.close()
                except:
                    pass
            return False

    def stop(self):
        logger.info("🛑 Stopping recording session")
        try:
            if self.camera and self.active:
                # Stop recording first
                logger.info("Stopping camera recording...")
                self.camera.stop_recording()
                
                # Wait for recording to fully stop and file to be finalized
                logger.info("Waiting for recording to finalize...")
                time.sleep(2.0)  # Give more time for file finalization
                
                # Stop the camera
                logger.info("Stopping camera...")
                self.camera.stop()
                
                # Close camera properly
                logger.info("Closing camera...")
                self.camera.close()
                
                self.active = False
                logger.info(f"⏹️ Stopped recording: {self.final_filepath}")

                # Check if file exists and is not corrupted
                if self.final_filepath.exists():
                    file_size = self.final_filepath.stat().st_size
                    logger.info(f"Recorded file size: {file_size} bytes")
                    
                    # Always create .done file if file size is reasonable, regardless of MP4 validation
                    if file_size > 100 * 1024:  # 100KB minimum
                        # Try to validate the MP4 file first
                        mp4_valid = False
                        try:
                            import subprocess
                            result = subprocess.run(
                                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(self.final_filepath)],
                                capture_output=True, text=True, timeout=10
                            )
                            if result.returncode == 0:
                                mp4_valid = True
                                logger.info("✅ MP4 file validation passed")
                            else:
                                logger.warning(f"⚠️ MP4 file validation failed: {result.stderr}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not validate MP4 file: {e}")
                        
                        # If MP4 is corrupted, try to repair it
                        if not mp4_valid:
                            logger.info("🔧 Attempting to repair corrupted MP4 file...")
                            if repair_mp4_file(self.final_filepath):
                                logger.info("✅ Successfully repaired MP4 file")
                                mp4_valid = True
                            else:
                                logger.warning("⚠️ Could not repair MP4 file, but will still process it")
                        
                        # Always create .done file if file size is reasonable
                        # Let the video worker handle corrupted files during processing
                        self.completed_marker.touch()
                        if mp4_valid:
                            logger.info(f"✅ Marked video as ready for processing: {self.completed_marker}")
                        else:
                            logger.info(f"⚠️ Marked corrupted video for processing (video worker will handle): {self.completed_marker}")
                    else:
                        logger.warning(f"⚠️ Video file too small or incomplete: {file_size} bytes. Skipping .done creation.")
                else:
                    logger.warning("⚠️ Recording file not found after stop.")

                # Remove lock file to allow video worker to process
                if self.lockfile.exists():
                    self.lockfile.unlink()
                    logger.info(f"🔓 Removed lock file: {self.lockfile}")

                # Save metadata file
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
                        "file_size": self.final_filepath.stat().st_size if self.final_filepath.exists() else 0
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
            logger.error(f"❌ Error stopping recording: {e}")
            self.active = False
            if self.camera:
                try:
                    self.camera.close()
                except:
                    pass

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
                current_session = RecordingSession(active_booking)
                if not current_session.start():
                    current_session = None
                    
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
