#!/usr/bin/env python3
"""
Main Recording Service
- Reads bookings from bookings_cache.json
- Starts/stops recordings at scheduled times (local timezone)
- Saves raw recordings to /opt/ezrec-backend/recordings/
"""

import os
import time
import json
import logging
import signal
import sys
import pytz
import psutil
from pathlib import Path
from dateutil import parser, tz
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

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

# Load environment
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

# Timezone
TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE") or os.getenv("SYSTEM_TIMEZONE") or "UTC"
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)

# Validate required ENV vars
REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"❌ Missing required environment variables: {missing}")
    sys.exit(1)

# Configs
USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
RAW_DIR = Path(os.getenv('RAW_RECORDINGS_DIR', '/opt/ezrec-backend/recordings/'))
LOG_FILE = Path(os.getenv('RECORDER_LOG', '/opt/ezrec-backend/logs/recorder.log'))
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))

# Prevent conflicting process
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

RAW_DIR.mkdir(parents=True, exist_ok=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info(f"📡 Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")

# Graceful shutdown
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
        self.filename = f"raw_{booking['id']}_{datetime.now(LOCAL_TZ).strftime('%H%M%S')}"
        self.filepath = self.date_folder / (self.filename + ".mp4")
        self.lockfile = self.filepath.with_suffix(".lock")
        self.completed_marker = self.filepath.with_suffix(".completed")
        self.picam2 = None
        self.encoder = None
        self.output = None
        self.active = False

    def start(self):
        if not Picamera2:
            logger.error("❌ picamera2 not available; cannot record.")
            return False
        try:
            self.lockfile.touch()
            logger.info("🔧 Initializing camera...")
            self.picam2 = safe_init_camera()

            logger.info("🎥 Creating video configuration...")
            config = self.picam2.create_video_configuration(
                main={"size": (1920, 1080)}, controls={"FrameRate": 30}
            )
            self.picam2.configure(config)

            self.encoder = H264Encoder(bitrate=10000000)
            self.output = FileOutput(str(self.filepath))

            logger.info("▶️ Starting video recording...")
            self.picam2.start_recording(self.encoder, self.output)
            self.active = True

            logger.info(f"✅ Started recording: {self.filepath}")
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
                logger.info(f"⏹️ Stopped recording: {self.filepath}")
                self.completed_marker.touch()

                metadata = {
                    "booking_id": self.booking["id"],
                    "user_id": USER_ID,
                    "camera_id": CAMERA_ID,
                    "date": datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
                }
                meta_path = self.filepath.with_suffix(".json")
                with open(meta_path, "w") as f:
                    json.dump(metadata, f)

                # Update booking status in Supabase
                supabase.table('bookings').update({'status': 'completed'}).eq('id', self.booking['id']).execute()
                supabase.table('cameras').update({
                    'is_recording': False,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'idle'
                }).eq('id', CAMERA_ID).execute()

                # Check that both .mp4 and .json exist before removing booking from cache
                if self.filepath.exists() and meta_path.exists():
                    try:
                        if BOOKING_CACHE_FILE.exists():
                            with open(BOOKING_CACHE_FILE, 'r') as f:
                                bookings = json.load(f)
                            # Remove only the booking with the matching id
                            updated_bookings = [b for b in bookings if b.get('id') != self.booking['id']]
                            with open(BOOKING_CACHE_FILE, 'w') as f:
                                json.dump(updated_bookings, f, indent=2)
                            logger.info(f"🗑️ Removed completed booking {self.booking['id']} from cache file.")
                        else:
                            logger.warning(f"Booking cache file {BOOKING_CACHE_FILE} does not exist when trying to remove completed booking.")
                    except Exception as e:
                        logger.error(f"Error removing completed booking from cache: {e}")
                else:
                    logger.warning(f"Not removing booking {self.booking['id']} from cache: .mp4 or .json file missing.")

            except Exception as e:
                logger.error(f"Error stopping recording: {e}")

            finally:
                if self.lockfile.exists():
                    self.lockfile.unlink()
                self.active = False

def get_active_booking(bookings):
    now = datetime.now(LOCAL_TZ)
    logger.info(f"🕒 Checking time: {now.isoformat()}")
    logger.info(f"USER_ID: {USER_ID}, CAMERA_ID: {CAMERA_ID}")
    for booking in bookings:
        try:
            start_time = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
            end_time = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
            logger.info(f"🔍 Booking {booking['id']}: {start_time} → {end_time}")
        except Exception as e:
            logger.warning(f"Invalid booking time format: {e}")
            continue
        logger.info(f"🔍 Comparing booking.user_id: {booking.get('user_id')}, booking.camera_id: {booking.get('camera_id')}")
        if (
            booking.get("user_id") == USER_ID and
            booking.get("camera_id") == CAMERA_ID and
            start_time <= now <= end_time
        ):
            logger.info(f"✅ Active booking matched: {booking['id']}")
            return booking
    return None

def load_bookings():
    logger.info("📂 Loading bookings from file")
    if not BOOKING_CACHE_FILE.exists():
        logger.warning(f"⚠️ Booking file does not exist: {BOOKING_CACHE_FILE}")
        return []

    try:
        with open(BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                logger.info(f"✅ Loaded {len(data)} bookings from cache")
                return data
            else:
                logger.warning("⚠️ Bookings file does not contain a list")
                return []
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error in booking cache: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error reading booking file: {e}")

    return []

def main():
    current_session = None
    while True:
        bookings = load_bookings()
        active_booking = get_active_booking(bookings)
        if active_booking:
            if not current_session or current_session.booking['id'] != active_booking['id']:
                if current_session:
                    logger.info("🧹 Stopping previous session before starting new")
                    current_session.stop()
                current_session = RecordingSession(active_booking)
                current_session.start()
        else:
            if current_session:
                logger.info("🛑 No active booking, stopping current session")
                current_session.stop()
                current_session = None
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
