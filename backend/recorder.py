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

    def safe_init_camera(retries=3, delay=3):
        for i in range(retries):
            try:
                return Picamera2()
            except RuntimeError as e:
                if "Camera __init__ sequence did not complete" in str(e):
                    print(f"⚠️ Camera busy (try {i+1}/{retries})... retrying in {delay}s")
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError("❌ Camera failed to initialize after multiple attempts")
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
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

class RecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RAW_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        self.date_folder.mkdir(parents=True, exist_ok=True)
        # Use start and end time for filename
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        self.raw_filepath = self.date_folder / (self.filename_base + ".h264")
        self.final_filepath = self.date_folder / (self.filename_base + ".mp4")
        self.lockfile = self.final_filepath.with_suffix(".lock")
        self.completed_marker = self.final_filepath.with_suffix(".done")
        self.picam2 = None
        self.encoder = None
        self.output = None
        self.active = False
        self.recording_start_time = None

    def start(self):
        if not Picamera2:
            logger.error("❌ picamera2 not available; cannot record.")
            return False
        try:
            self.lockfile.touch()
            logger.info("🔧 Initializing camera...")
            self.picam2 = safe_init_camera()

            config = self.picam2.create_video_configuration(
                main={"size": (1920, 1080)}, controls={"FrameRate": 30}
            )
            self.picam2.configure(config)

            self.encoder = H264Encoder(bitrate=10000000)
            self.output = FileOutput(str(self.raw_filepath))

            self.picam2.start_recording(self.encoder, self.output)
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)

            logger.info(f"✅ Started recording: {self.raw_filepath}")
            update_booking_status(self.booking["id"], "Recording")

            supabase.table('cameras').update({
                'is_recording': True,
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                'status': 'online'
            }).eq('id', CAMERA_ID).execute()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            if self.lockfile.exists():
                self.lockfile.unlink()
            return False

    def stop(self):
        if self.active and self.picam2:
            try:
                self.picam2.stop_recording()
                self.picam2.close()
                logger.info(f"⏹️ Stopped recording: {self.raw_filepath}")
                # Convert raw H264 to MP4 using ffmpeg
                import subprocess
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-framerate", "30", "-i", str(self.raw_filepath),
                    "-c:v", "copy", "-movflags", "+faststart", str(self.final_filepath)
                ]
                logger.info(f"🎬 Running ffmpeg: {' '.join(ffmpeg_cmd)}")
                try:
                    subprocess.run(ffmpeg_cmd, check=True)
                    logger.info(f"✅ Converted to MP4: {self.final_filepath}")
                    # Clean up raw file
                    if self.raw_filepath.exists():
                        os.remove(self.raw_filepath)
                except Exception as e:
                    logger.error(f"❌ ffmpeg conversion failed: {e}")
                self.completed_marker.touch()

                # Write metadata
                if self.final_filepath.exists():
                    metadata = {
                        "booking_id": self.booking["id"],
                        "user_id": USER_ID,
                        "camera_id": CAMERA_ID,
                        "date": self.date_folder.name,
                        "start_time": self.booking["start_time"],
                        "end_time": self.booking["end_time"],
                        "filename": self.final_filepath.name
                    }
                    with open(self.final_filepath.with_suffix(".json"), "w") as f:
                        json.dump(metadata, f)

                supabase.table('cameras').update({
                    'is_recording': False,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'idle'
                }).eq('id', CAMERA_ID).execute()

                # Now update status to RecordingFinished
                update_booking_status(self.booking["id"], "RecordingFinished")

            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
            finally:
                if self.lockfile.exists():
                    self.lockfile.unlink()
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
        bookings = load_bookings()
        now = datetime.now(LOCAL_TZ)
        active_booking = get_active_booking(bookings)
        if current_session:
            end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
            logger.info(f"Now: {now.isoformat()}, Booking end: {end_time.isoformat()}, Should stop: {now > end_time}, Session started: {current_session.recording_start_time.isoformat() if current_session.recording_start_time else 'N/A'}")
            # Only stop if end time has passed and at least 10 seconds have elapsed
            min_duration = 10  # seconds
            elapsed = (now - current_session.recording_start_time).total_seconds() if current_session.recording_start_time else 0
            if now > end_time and elapsed > min_duration:
                logger.info(f"Stopping session: now={now}, end_time={end_time}, elapsed={elapsed}s")
                current_session.stop()
                current_session = None
        if not current_session and active_booking:
            current_session = RecordingSession(active_booking)
            current_session.start()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
