#!/usr/bin/env python3
"""
Main Recording Service
- Reads bookings from bookings_cache.json
- Starts/stops recordings at scheduled times
- Saves raw recordings to /opt/ezrec-backend/raw_recordings/
- Does NOT process or upload videos
- Designed to run as a standalone process (systemd service)
"""
import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from supabase import create_client
from uuid import UUID
import sys
import pytz
import psutil
from zoneinfo import ZoneInfo
import uuid

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
except ImportError:
    Picamera2 = None

load_dotenv("/opt/ezrec-backend/.env")

# Validate required environment variables
REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"Missing required environment variables: {missing}")
    sys.exit(1)

# Prevent running if ezrec_backend.py is active
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'ezrec_backend.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("ERROR: ezrec_backend.py is running. recorder.py should not run in parallel. Exiting.")
            sys.exit(1)
    except Exception:
        continue

# Use timezone-aware datetime
LOCAL_TZ = ZoneInfo(os.popen('cat /etc/timezone').read().strip()) if os.path.exists('/etc/timezone') else None

USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID', '0')
BOOKING_CACHE_FILE = Path(os.getenv('BOOKING_CACHE_FILE', '/opt/ezrec-backend/bookings_cache.json'))
RAW_DIR = Path(os.getenv('RAW_RECORDINGS_DIR', '/opt/ezrec-backend/raw_recordings/'))
LOG_FILE = Path(os.getenv('RECORDER_LOG', '/opt/ezrec-backend/logs/recorder.log'))
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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

class RecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.filename = f"raw_{booking['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        self.filepath = RAW_DIR / self.filename
        self.picam2 = None
        self.encoder = None
        self.output = None
        self.active = False

    def start(self):
        if not Picamera2:
            logger.error("picamera2 not available; cannot record.")
            return False
        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_video_configuration(main={"size": (1920, 1080)}, controls={"FrameRate": 30})
            self.picam2.configure(config)
            self.encoder = H264Encoder(bitrate=10000000)
            self.output = FileOutput(str(self.filepath))
            self.picam2.start_recording(self.encoder, self.output)
            self.active = True
            logger.info(f"Started recording: {self.filepath}")
            # Set is_recording True in cameras table
            try:
                supabase.table('cameras').update({'is_recording': True}).eq('id', CAMERA_ID).execute()
                logger.info(f"Camera {CAMERA_ID} is_recording set to True in Supabase.")
            except Exception as e:
                logger.error(f"Failed to update camera is_recording=True in Supabase: {e}")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    def stop(self):
        if self.active and self.picam2:
            try:
                self.picam2.stop_recording()
                self.picam2.close()
                logger.info(f"Stopped recording: {self.filepath}")
                # Update booking status to 'completed' in Supabase
                try:
                    supabase.table('bookings').update({'status': 'completed'}).eq('id', self.booking['id']).execute()
                    logger.info(f"Booking {self.booking['id']} status set to 'completed' in Supabase.")
                except Exception as e:
                    logger.error(f"Failed to update booking status in Supabase: {e}")
                # Set is_recording False in cameras table
                try:
                    supabase.table('cameras').update({'is_recording': False}).eq('id', CAMERA_ID).execute()
                    logger.info(f"Camera {CAMERA_ID} is_recording set to False in Supabase.")
                except Exception as e:
                    logger.error(f"Failed to update camera is_recording=False in Supabase: {e}")
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
            self.active = False


def load_bookings():
    if BOOKING_CACHE_FILE.exists():
        try:
            with open(BOOKING_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load bookings: {e}")
    return []

def get_active_booking(bookings):
    now = datetime.now(LOCAL_TZ).time()
    today = datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
    for booking in bookings:
        try:
            start_time = datetime.strptime(booking['start_time'], "%H:%M").time()
            end_time = datetime.strptime(booking['end_time'], "%H:%M").time()
        except Exception:
            continue
        if booking['date'] == today and start_time <= now <= end_time:
            return booking
    return None

def is_valid_uuid(val):
    try:
        UUID(str(val))
        return True
    except Exception:
        return False

def main():
    logger.info("Recorder Service started")
    current_session = None
    while True:
        bookings = load_bookings()
        active_booking = get_active_booking(bookings)
        if active_booking:
            if not current_session or current_session.booking['id'] != active_booking['id']:
                if current_session:
                    current_session.stop()
                current_session = RecordingSession(active_booking)
                current_session.start()
        else:
            if current_session:
                current_session.stop()
                # After stopping, check for another active booking
                bookings = load_bookings()
                next_booking = get_active_booking(bookings)
                if next_booking:
                    current_session = RecordingSession(next_booking)
                    current_session.start()
                else:
                    current_session = None
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 