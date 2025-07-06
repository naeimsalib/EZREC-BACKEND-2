from fastapi import FastAPI, Request, HTTPException, Header
from typing import List, Optional
from pathlib import Path
import json
import os
from dotenv import load_dotenv

load_dotenv("/opt/ezrec-backend/.env")

API_KEY = os.getenv("BOOKING_SYNC_API_KEY", "ezrec_prod_4b2e7e7c-8e2a-4c1b-9f2e-1a7b2e8c9d3f")
BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/push")
async def push_bookings(request: Request, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        bookings = await request.json()
        if not isinstance(bookings, list):
            raise HTTPException(status_code=400, detail="Payload must be a list of bookings")
        BOOKINGS_FILE.write_text(json.dumps(bookings, indent=2))
        return {"status": "success", "count": len(bookings)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save bookings: {e}")

@app.post("/delete")
async def delete_booking(request: Request, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        data = await request.json()
        booking_id = data.get("id")
        if not booking_id:
            raise HTTPException(status_code=400, detail="Missing booking id")
        bookings = json.loads(BOOKINGS_FILE.read_text()) if BOOKINGS_FILE.exists() else []
        filtered = [b for b in bookings if b.get("id") != booking_id]
        BOOKINGS_FILE.write_text(json.dumps(filtered, indent=2))
        return {"status": "deleted", "booking_id": booking_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete booking: {e}") 