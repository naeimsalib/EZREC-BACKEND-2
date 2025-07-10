import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("booking_utils")

def update_booking_status(booking_id: str, new_status: str) -> bool:
    """
    Updates booking status in both Supabase and the local cache file.
    """
    success = True

    # --- Update in Supabase ---
    try:
        logger.info(f"🔄 Updating Supabase booking {booking_id} to status '{new_status}'")
        response = supabase.table("bookings").update({"status": new_status}).eq("id", booking_id).execute()
        if response.error:
            logger.error(f"❌ Supabase update error: {response.error}")
            success = False
    except Exception as e:
        logger.error(f"❌ Supabase exception: {e}")
        success = False

    # --- Update in Local JSON ---
    try:
        if BOOKING_CACHE_FILE.exists():
            with open(BOOKING_CACHE_FILE, 'r') as f:
                bookings = json.load(f)

            updated = False
            for booking in bookings:
                if booking.get("id") == booking_id:
                    booking["status"] = new_status
                    updated = True
                    break

            if updated:
                with open(BOOKING_CACHE_FILE, 'w') as f:
                    json.dump(bookings, f, indent=2)
                logger.info(f"📄 Updated local cache for booking {booking_id} to status '{new_status}'")
            else:
                logger.warning(f"⚠️ Booking ID {booking_id} not found in local file.")
        else:
            logger.warning(f"⚠️ Local booking cache not found at {BOOKING_CACHE_FILE}")
    except Exception as e:
        logger.error(f"❌ Local file update error: {e}")
        success = False

    return success
