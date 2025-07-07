from fastapi import FastAPI, Request, HTTPException, Header, Query
from typing import List, Optional
from pathlib import Path
import json
import os
from dotenv import load_dotenv
from supabase import create_client
from fastapi.middleware.cors import CORSMiddleware
import boto3
from urllib.parse import unquote
from pydantic import BaseModel

load_dotenv("/opt/ezrec-backend/.env")

API_KEY = os.getenv("BOOKING_SYNC_API_KEY", "ezrec_prod_4b2e7e7c-8e2a-4c1b-9f2e-1a7b2e8c9d3f")
BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Load .env for AWS credentials
load_dotenv("/opt/ezrec-backend/.env")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "ezrec-videos")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeletePayload(BaseModel):
    key: str

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
        # Check for edits to non-existent bookings
        existing = json.loads(BOOKINGS_FILE.read_text()) if BOOKINGS_FILE.exists() else []
        existing_ids = {b["id"] for b in existing}
        unavailable = [b["id"] for b in bookings if b["id"] not in existing_ids]
        BOOKINGS_FILE.write_text(json.dumps(bookings, indent=2))
        # Supabase upsert
        if supabase:
            for booking in bookings:
                try:
                    supabase.table("bookings").upsert(booking).execute()
                except Exception as e:
                    print(f"[Supabase] Upsert error: {e}")
        if unavailable:
            return {"status": "partial", "message": f"Some bookings unavailable: {unavailable}", "count": len(bookings)}
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
        if len(filtered) == len(bookings):
            return {"status": "unavailable", "message": f"Booking {booking_id} not found"}
        BOOKINGS_FILE.write_text(json.dumps(filtered, indent=2))
        # Supabase delete
        if supabase:
            try:
                supabase.table("bookings").delete().eq("id", booking_id).execute()
            except Exception as e:
                print(f"[Supabase] Delete error: {e}")
        return {"status": "deleted", "booking_id": booking_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete booking: {e}")

@app.get("/status")
def status():
    return {"status": "ok"}

@app.get("/signed-url")
def get_signed_url(key: str = Query(..., description="S3 object key")):
    raw_key = key
    decoded_key = unquote(key)

    print(f"\n--- SIGNED URL DEBUG ---")
    print(f"🔑 Raw key:     {raw_key}")
    print(f"🧩 Decoded key: {decoded_key}")
    print(f"🪣 Bucket:      {S3_BUCKET}")
    print(f"🧪 Checking key in S3...")

    try:
        s3.head_object(Bucket=S3_BUCKET, Key=decoded_key)
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": S3_BUCKET, "Key": decoded_key},
            ExpiresIn=3600
        )
        print(f"✅ Signed URL generated")
        return {"url": url}
    except s3.exceptions.ClientError as e:
        print(f"❌ S3 head_object failed: {e}")
        raise HTTPException(status_code=404, detail="Object not found in S3")
    except Exception as e:
        print(f"🔥 Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@app.delete("/delete-video")
def delete_video(data: DeletePayload):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=data.key)
        print(f"✅ Deleted {data.key} from S3")
        return {"status": "success", "message": f"Deleted {data.key}"}
    except Exception as e:
        print(f"Failed to delete video: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 