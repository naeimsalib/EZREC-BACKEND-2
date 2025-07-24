#!/usr/bin/env python3
"""
Dual Camera Recording Service
- Records from both cameras simultaneously
- Merges recordings into one large video
- Supports side-by-side, grid, and picture-in-picture layouts
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
import subprocess

# 🔧 Ensure API utils can be imported
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
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
LOG_FILE = Path(os.getenv('RECORDER_LOG', '/opt/ezrec-backend/logs/dual_recorder.log'))
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))
RESOLUTION = os.getenv('RESOLUTION', '1280x720')
MERGE_METHOD = os.getenv('MERGE_METHOD', 'side_by_side')

# Camera configuration
CAMERA_0_SERIAL = os.getenv('CAMERA_0_SERIAL', '88000')
CAMERA_1_SERIAL = os.getenv('CAMERA_1_SERIAL', '80000')
CAMERA_0_NAME = os.getenv('CAMERA_0_NAME', 'left')
CAMERA_1_NAME = os.getenv('CAMERA_1_NAME', 'right')

try:
    width, height = map(int, RESOLUTION.lower().split('x'))
except Exception:
    width, height = 1280, 720

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'dual_recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ dual_recorder.py is already running.")
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

logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
logger.info(f"🎬 Merge method: {MERGE_METHOD}")

def safe_init_camera(camera_serial, camera_name, retries=3, delay=3):
    """Initialize a camera with specific serial number"""
    for i in range(retries):
        try:
            camera = Picamera2()
            
            # Configure camera with specific serial
            camera_info = camera.camera_properties
            if 'SerialNumber' in camera_info and camera_info['SerialNumber'] != camera_serial:
                camera.close()
                raise RuntimeError(f"Camera serial mismatch for {camera_name}. Expected: {camera_serial}, Got: {camera_info['SerialNumber']}")
            
            logger.info(f"✅ Initialized {camera_name} camera with serial: {camera_serial}")
            return camera
            
        except RuntimeError as e:
            if "Camera __init__ sequence did not complete" in str(e):
                logger.warning(f"⚠️ {camera_name} camera busy (try {i+1}/{retries})... retrying in {delay}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError(f"❌ {camera_name} camera failed to initialize after multiple attempts")

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

def merge_videos(video1_path: Path, video2_path: Path, output_path: Path, method: str = 'side_by_side'):
    """
    Merge two video files using FFmpeg
    Methods: side_by_side, grid, picture_in_picture
    """
    try:
        logger.info(f"🎬 Merging videos using method: {method}")
        
        if method == 'side_by_side':
            # Side by side layout
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', f'[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-map', '0:a',  # Use audio from first video
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                str(output_path)
            ]
        elif method == 'grid':
            # 2x1 grid layout
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', f'[0:v][1:v]vstack=inputs=2[v]',
                '-map', '[v]',
                '-map', '0:a',  # Use audio from first video
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                str(output_path)
            ]
        elif method == 'picture_in_picture':
            # Picture in picture (camera 1 as main, camera 2 as overlay)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[1:v]scale=320:240[overlay];[0:v][overlay]overlay=W-w-10:10[v]',
                '-map', '[v]',
                '-map', '0:a',  # Use audio from first video
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                str(output_path)
            ]
        else:
            raise ValueError(f"Unknown merge method: {method}")
        
        # Run FFmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully merged videos to: {output_path}")
            return True
        else:
            logger.error(f"❌ Failed to merge videos: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error merging videos: {e}")
        return False

class DualRecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RAW_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        self.date_folder.mkdir(parents=True, exist_ok=True)
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        
        # Individual camera files
        self.camera0_filepath = self.date_folder / f"{self.filename_base}_{CAMERA_0_NAME}.mp4"
        self.camera1_filepath = self.date_folder / f"{self.filename_base}_{CAMERA_1_NAME}.mp4"
        
        # Merged output file
        self.merged_filepath = self.date_folder / f"{self.filename_base}_merged.mp4"
        
        # Lock and marker files
        self.lockfile = self.merged_filepath.with_suffix(".lock")
        self.completed_marker = self.merged_filepath.with_suffix(".done")
        
        # Camera objects
        self.camera0 = None
        self.camera1 = None
        self.encoder0 = None
        self.encoder1 = None
        
        self.active = False
        self.recording_start_time = None
        self.recording_threads = []

    def start(self):
        try:
            self.lockfile.touch()
            logger.info(f"🎬 Starting dual camera recording to {self.merged_filepath}")
            
            # Initialize both cameras
            logger.info("📷 Initializing cameras...")
            self.camera0 = safe_init_camera(CAMERA_0_SERIAL, CAMERA_0_NAME)
            time.sleep(1)  # Small delay between camera init
            self.camera1 = safe_init_camera(CAMERA_1_SERIAL, CAMERA_1_NAME)
            
            # Configure cameras
            config = {
                "main": {"size": (width, height), "format": "YUV420"},
                "controls": {
                    "FrameDurationLimits": (33333, 1000000),  # 1-30fps
                    "ExposureTime": 33333,  # 1/30 second
                    "AnalogueGain": 1.0,
                    "FrameSkip": 0,  # Prevent frame skipping
                    "NoiseReductionMode": 0  # Disable noise reduction for stability
                }
            }
            
            self.camera0.configure(config)
            self.camera1.configure(config)
            
            # Start cameras
            self.camera0.start()
            self.camera1.start()
            
            # Create encoders
            self.encoder0 = H264Encoder(
                bitrate=4000000,  # 4Mbps per camera (reduced for dual setup)
                repeat=False,
                iperiod=30,
                qp=25
            )
            
            self.encoder1 = H264Encoder(
                bitrate=4000000,  # 4Mbps per camera
                repeat=False,
                iperiod=30,
                qp=25
            )
            
            # Start recording on both cameras
            logger.info(f"📹 Starting recording on {CAMERA_0_NAME} camera...")
            self.camera0.start_recording(self.encoder0, str(self.camera0_filepath))
            
            logger.info(f"📹 Starting recording on {CAMERA_1_NAME} camera...")
            self.camera1.start_recording(self.encoder1, str(self.camera1_filepath))
            
            # Wait for recording to start
            time.sleep(2.0)
            
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)
            logger.info(f"✅ Started dual camera recording")
            
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
            logger.error(f"❌ Failed to start dual recording: {e}")
            self.cleanup_cameras()
            if self.lockfile.exists():
                self.lockfile.unlink()
            return False

    def stop(self):
        logger.info("🛑 Stopping dual camera recording session")
        try:
            if self.active:
                # Stop recording on both cameras
                logger.info("Stopping camera recordings...")
                if self.camera0:
                    self.camera0.stop_recording()
                if self.camera1:
                    self.camera1.stop_recording()
                
                # Wait for recordings to finalize
                logger.info("Waiting for recordings to finalize...")
                time.sleep(2.0)
                
                # Stop and close cameras
                self.cleanup_cameras()
                
                self.active = False
                logger.info(f"⏹️ Stopped dual camera recording")

                # Check if both files exist and are valid
                if self.camera0_filepath.exists() and self.camera1_filepath.exists():
                    size0 = self.camera0_filepath.stat().st_size
                    size1 = self.camera1_filepath.stat().st_size
                    logger.info(f"📊 Camera 0 file size: {size0} bytes")
                    logger.info(f"📊 Camera 1 file size: {size1} bytes")
                    
                    if size0 > 100 * 1024 and size1 > 100 * 1024:  # Both files > 100KB
                        # Merge the videos
                        logger.info("🎬 Starting video merge...")
                        if merge_videos(self.camera0_filepath, self.camera1_filepath, 
                                      self.merged_filepath, MERGE_METHOD):
                            # Create .done marker for merged file
                            self.completed_marker.touch()
                            logger.info(f"✅ Created merged video: {self.merged_filepath}")
                            
                            # Save metadata
                            self.save_metadata()
                            
                            # Clean up individual camera files (optional)
                            # self.camera0_filepath.unlink()
                            # self.camera1_filepath.unlink()
                            # logger.info("🧹 Cleaned up individual camera files")
                        else:
                            logger.error("❌ Failed to merge videos")
                    else:
                        logger.warning("⚠️ One or both camera files too small, skipping merge")
                else:
                    logger.warning("⚠️ One or both camera files missing")

                # Remove lock file
                if self.lockfile.exists():
                    self.lockfile.unlink()
                    logger.info(f"🔓 Removed lock file: {self.lockfile}")

                # Update booking status
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
            logger.error(f"❌ Error stopping dual recording: {e}")
            self.active = False
            self.cleanup_cameras()

    def cleanup_cameras(self):
        """Clean up camera resources"""
        try:
            if self.camera0:
                self.camera0.stop()
                self.camera0.close()
                logger.info(f"🔒 Closed {CAMERA_0_NAME} camera")
            if self.camera1:
                self.camera1.stop()
                self.camera1.close()
                logger.info(f"🔒 Closed {CAMERA_1_NAME} camera")
        except Exception as e:
            logger.error(f"❌ Error cleaning up cameras: {e}")

    def save_metadata(self):
        """Save metadata for the merged recording"""
        try:
            metadata_path = self.merged_filepath.with_suffix(".json")
            metadata = {
                "booking_id": self.booking["id"],
                "user_id": self.booking.get("user_id"),
                "camera_id": self.booking.get("camera_id"),
                "start_time": self.booking["start_time"],
                "end_time": self.booking["end_time"],
                "recording_start": self.recording_start_time.isoformat() if self.recording_start_time else None,
                "recording_end": datetime.now(LOCAL_TZ).isoformat(),
                "file_path": str(self.merged_filepath),
                "file_size": self.merged_filepath.stat().st_size if self.merged_filepath.exists() else 0,
                "merge_method": MERGE_METHOD,
                "camera0_file": str(self.camera0_filepath),
                "camera1_file": str(self.camera1_filepath),
                "camera0_serial": CAMERA_0_SERIAL,
                "camera1_serial": CAMERA_1_SERIAL,
                "camera0_name": CAMERA_0_NAME,
                "camera1_name": CAMERA_1_NAME,
                "dual_camera": True
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"📝 Metadata saved to: {metadata_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")

def handle_exit(sig, frame):
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    if 'current_session' in globals() and current_session and current_session.active:
        logger.info("🛑 Stopping active dual recording before exit...")
        try:
            current_session.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping dual recording during exit: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

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
                if current_session.recording_start_time:
                    logger.info(
                        f"Now: {now.isoformat()}, Booking end: {end_time.isoformat()}, "
                        f"Should stop: {now > end_time}, Session started: {current_session.recording_start_time.isoformat()}"
                    )
                # Only stop if end time has passed and at least 10 seconds have elapsed
                min_duration = 10  # seconds
                elapsed = (current_session.recording_start_time and 
                          (now - current_session.recording_start_time).total_seconds()) or 0
                if now > end_time and elapsed > min_duration:
                    logger.info(f"Stopping dual session: now={now}, end_time={end_time}, elapsed={elapsed}s")
                    current_session.stop()
                    current_session = None
                    
            if not current_session and active_booking:
                current_session = DualRecordingSession(active_booking)
                if not current_session.start():
                    current_session = None
                    
        except Exception as e:
            logger.error(f"❌ Error in dual recorder main loop: {e}")
            
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 