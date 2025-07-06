# booking_sync_api.py (replaces old booking_sync.py)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import logging
import os
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
LOG_FILE = Path("/opt/ezrec-backend/logs/booking_sync_api.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Booking(BaseModel):
    id: str
    user_id: str
    start_time: str
    end_time: str
    date: str
    camera_id: str
    recording_id: str = ""
    status: str = "Pending"

@app.get("/")
def root():
    return {"status": "booking_sync_api online"}

@app.get("/bookings")
def get_bookings():
    if BOOKING_CACHE_FILE.exists():
        try:
            return json.loads(BOOKING_CACHE_FILE.read_text())
        except Exception as e:
            logger.error(f"Error reading bookings: {e}")
            raise HTTPException(status_code=500, detail="Failed to read bookings file")
    return []

@app.post("/bookings")
def post_bookings(bookings: List[Booking]):
    try:
        logger.info(f"Received {len(bookings)} bookings via POST")
        existing = json.loads(BOOKING_CACHE_FILE.read_text()) if BOOKING_CACHE_FILE.exists() else []
        combined = existing + [b.dict() for b in bookings]
        unique = {b["id"]: b for b in combined}.values()
        BOOKING_CACHE_FILE.write_text(json.dumps(list(unique), indent=2))
        return {"message": "Bookings saved", "count": len(bookings)}
    except Exception as e:
        logger.error(f"Error saving bookings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save bookings")

@app.put("/bookings/{booking_id}")
def update_booking(booking_id: str, booking: Booking):
    try:
        bookings = json.loads(BOOKING_CACHE_FILE.read_text()) if BOOKING_CACHE_FILE.exists() else []
        updated = False
        for i, b in enumerate(bookings):
            if b["id"] == booking_id:
                bookings[i] = booking.dict()
                updated = True
                break
        if not updated:
            return {"status": "unavailable", "message": f"Booking {booking_id} not found"}
        BOOKING_CACHE_FILE.write_text(json.dumps(bookings, indent=2))
        return {"status": "updated", "booking": booking.dict()}
    except Exception as e:
        logger.error(f"Error updating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: str):
    try:
        bookings = json.loads(BOOKING_CACHE_FILE.read_text()) if BOOKING_CACHE_FILE.exists() else []
        filtered = [b for b in bookings if b["id"] != booking_id]
        if len(filtered) == len(bookings):
            return {"status": "unavailable", "message": f"Booking {booking_id} not found"}
        BOOKING_CACHE_FILE.write_text(json.dumps(filtered, indent=2))
        return {"status": "deleted", "booking_id": booking_id}
    except Exception as e:
        logger.error(f"Error deleting booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))
