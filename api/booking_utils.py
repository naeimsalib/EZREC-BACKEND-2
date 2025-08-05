import os
import json
import os
import logging
from pathlib import Path
from supabase import create_client
import os
from dotenv import load_dotenv

dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def update_booking_status(booking_id: str, new_status: str):
    # Update local file
    try:
        if BOOKING_CACHE_FILE.exists():
            with open(BOOKING_CACHE_FILE, "r") as f:
                bookings = json.load(f)

            updated = False
            for b in bookings:
                if b["id"] == booking_id:
                    b["status"] = new_status
                    updated = True
                    break

            if updated:
                with open(BOOKING_CACHE_FILE, "w") as f:
                    json.dump(bookings, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to update local booking cache: {e}")

    # Update Supabase
    try:
        supabase.table("bookings").update({"status": new_status}).eq("id", booking_id).execute()
    except Exception as e:
        print(f"⚠️ Failed to update Supabase booking status: {e}")
