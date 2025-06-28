#!/usr/bin/env python3
"""
Booking Sync Service
- Fetches bookings from Supabase every 3 seconds
- Updates bookings_cache.json with new, edited, or deleted bookings
- Designed to run as a standalone process (systemd service)
"""
import os
import time
import json
import logging
import sys
import pytz
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from zoneinfo import ZoneInfo

load_dotenv("/opt/ezrec-backend/.env")

# Validate required environment variables
REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"Missing required environment variables: {missing}")
    sys.exit(1)

from zoneinfo import ZoneInfo
LOCAL_TZ = ZoneInfo(os.popen('cat /etc/timezone').read().strip()) if os.path.exists('/etc/timezone') else None

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID', '0')
BOOKING_CACHE_FILE = Path(os.getenv('BOOKING_CACHE_FILE', '/opt/ezrec-backend/bookings_cache.json'))
LOG_FILE = Path(os.getenv('BOOKING_SYNC_LOG', '/opt/ezrec-backend/logs/booking_sync.log'))
FETCH_INTERVAL = int(os.getenv('BOOKING_FETCH_INTERVAL', '3'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_bookings():
    try:
        response = supabase.table('bookings').select('*').eq('user_id', USER_ID).eq('camera_id', CAMERA_ID).eq('status', 'confirmed').execute()
        if response.data is None:
            logger.error(f"Supabase response has no data: {response}")
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Failed to fetch bookings: {e}")
        return None

def load_local_cache():
    if BOOKING_CACHE_FILE.exists():
        try:
            with open(BOOKING_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load local cache: {e}")
    return []

def save_local_cache(bookings):
    try:
        with open(BOOKING_CACHE_FILE, 'w') as f:
            json.dump(bookings, f)
    except Exception as e:
        logger.warning(f"Failed to save local cache: {e}")

def bookings_changed(old, new):
    return json.dumps(old, sort_keys=True) != json.dumps(new, sort_keys=True)

def main():
    logger.info("Booking Sync Service started")
    last_bookings = load_local_cache()
    while True:
        bookings = fetch_bookings()
        if bookings is not None and bookings_changed(last_bookings, bookings):
            logger.info("Bookings updated; saving to cache.")
            save_local_cache(bookings)
            last_bookings = bookings
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    main() 