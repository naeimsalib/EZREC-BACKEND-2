from supabase import create_client
from fastapi import FastAPI, HTTPException, Query, Request, Body, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import logging
import boto3
import os
from dotenv import load_dotenv
from urllib.parse import unquote
import sys
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, PlainTextResponse
import urllib.parse
import requests
import shutil
from uuid import uuid4
import smtplib
from email.message import EmailMessage
import psutil
import time
import numpy as np
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    import cv2
    PICAMERA2_AVAILABLE = False
import io
import threading
import pytz

# --------------------------
# LOAD .env FILE
# --------------------------
load_dotenv(dotenv_path="/opt/ezrec-backend/.env")

# --------------------------
# LOGGING SETUP
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("EZREC")

# --------------------------
# SUPABASE CONFIGURATION
# --------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --------------------------
# FASTAPI INIT
# --------------------------
app = FastAPI()

@app.get("/test-alive")
def test_alive():
    return {"status": "alive"}

# Allow only the production frontend domain for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://d3p0722z34ceid.cloudfront.net",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --------------------------
# FILE PATHS
# --------------------------
BOOKINGS_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
SYSTEM_FILE = Path("/opt/ezrec-backend/api/local_data/system.json")
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")

# --------------------------
# S3 CONFIGURATION
# --------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "ezrec-videos")
USER_MEDIA_BUCKET = os.getenv("AWS_USER_MEDIA_BUCKET", S3_BUCKET)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# --------------------------
# MODELS
# --------------------------
class Booking(BaseModel):
    id: str
    user_id: str
    start_time: str
    end_time: str
    date: str
    camera_id: Optional[str] = None
    recording_id: Optional[str] = None
    booking_id: str
    email: Optional[str] = None

class SystemSettings(BaseModel):
    main_logo_path: str
    sponsor_logo_paths: List[str]
    intro_video_path: str

class DeletePayload(BaseModel):
    key: str

class MediaNotifyRequest(BaseModel):
    user_id: str
    action: str  # "upload" or "delete"
    s3_key: str
    filename: str
    media_type: str

class ShareRequest(BaseModel):
    key: str
    user_id: str  # Now required

class ShareResponse(BaseModel):
    url: str

class SendShareEmailRequest(BaseModel):
    email: EmailStr
    link: str
    videoId: str

class RevokeShareRequest(BaseModel):
    user_id: str

# --------------------------
# ENDPOINTS
# --------------------------
@app.get("/")
def root():
    return {"message": "EZREC FastAPI is running"}

@app.get("/status")
def status():
    """Enhanced system status endpoint with detailed health information"""
    try:
        import psutil
        import shutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/opt/ezrec-backend")
        disk_used_percent = (disk.used / disk.total) * 100
        
        # Get camera status
        camera_status = "unknown"
        try:
            from pathlib import Path
            status_file = Path("/opt/ezrec-backend/status.json")
            if status_file.exists():
                with open(status_file) as f:
                    status_data = json.load(f)
                    camera_status = "recording" if status_data.get("is_recording", False) else "idle"
        except Exception:
            camera_status = "error"
        
        # Get recent recordings
        recent_recordings = []
        try:
            recordings_dir = Path("/opt/ezrec-backend/recordings")
            if recordings_dir.exists():
                for date_dir in sorted(recordings_dir.glob("*"), reverse=True)[:3]:
                    if date_dir.is_dir():
                        recordings = list(date_dir.glob("*.mp4"))
                        if recordings:
                            recent_recordings.append({
                                "date": date_dir.name,
                                "count": len(recordings),
                                "latest": recordings[-1].name if recordings else None
                            })
        except Exception:
            pass
        
        # Get last upload time
        last_upload = "unknown"
        try:
            processed_dir = Path("/opt/ezrec-backend/processed")
            if processed_dir.exists():
                processed_files = list(processed_dir.rglob("*.mp4"))
                if processed_files:
                    latest_file = max(processed_files, key=lambda x: x.stat().st_mtime)
                    last_upload = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
        except Exception:
            pass
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_used_percent": round(disk_used_percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 1)
            },
            "camera": {
                "status": camera_status,
                "mode": "dual" if os.getenv("DUAL_CAMERA_MODE", "false").lower() == "true" else "single"
            },
            "recordings": {
                "recent": recent_recordings,
                "last_upload": last_upload
            },
            "services": {
                "recorder": "running",  # TODO: Check actual service status
                "video_worker": "running",
                "api": "running"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/bookings")
def get_bookings():
    if BOOKINGS_FILE.exists():
        try:
            return json.loads(BOOKINGS_FILE.read_text())
        except Exception as e:
            logger.error(f"Error reading bookings: {e}")
            raise HTTPException(status_code=500, detail="Failed to read bookings file")
    return []

@app.post("/bookings")
def post_bookings(bookings: List[Booking]):
    try:
        logger.info(f"📥 Received {len(bookings)} bookings via POST")
        
        # Validate each booking
        for booking in bookings:
            logger.info(f"➡️ Validating booking: {booking.dict()}")
            
            # Parse booking times
            try:
                start_time = datetime.fromisoformat(booking.start_time.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(booking.end_time.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid booking time format: {e}")
            
            # Check if booking ends in the past
            now = datetime.now(timezone.utc)
            if end_time <= now:
                raise HTTPException(status_code=400, detail="Booking ends in the past")
            
            # Check if start time is after end time
            if start_time >= end_time:
                raise HTTPException(status_code=400, detail="Invalid booking times: start must be before end")
            
            # Check for overlapping bookings
            existing = []
            if BOOKINGS_FILE.exists():
                try:
                    existing = json.loads(BOOKINGS_FILE.read_text())
                except Exception as e:
                    logger.warning(f"Could not read existing bookings: {e}")
            
            for existing_booking in existing:
                try:
                    existing_start = datetime.fromisoformat(existing_booking['start_time'].replace('Z', '+00:00'))
                    existing_end = datetime.fromisoformat(existing_booking['end_time'].replace('Z', '+00:00'))
                    
                    # Check for overlap (not (booking.end <= existing.start or booking.start >= existing.end))
                    if not (end_time <= existing_start or start_time >= existing_end):
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Booking overlaps with existing booking {existing_booking.get('id', 'unknown')}"
                        )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing existing booking: {e}")
                    continue

        # All validations passed, save bookings
        existing = []
        if BOOKINGS_FILE.exists():
            try:
                existing = json.loads(BOOKINGS_FILE.read_text())
            except Exception as e:
                logger.warning(f"Could not read existing bookings: {e}")

        combined = existing + [b.dict() for b in bookings]
        unique = {b["id"]: b for b in combined}.values()
        BOOKINGS_FILE.write_text(json.dumps(list(unique), indent=2))

        return {"message": "Bookings saved", "count": len(bookings)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving bookings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save bookings")

@app.put("/bookings/{booking_id}")
def update_booking(booking_id: str, updated_booking: Booking):
    try:
        bookings = json.loads(BOOKINGS_FILE.read_text()) if BOOKINGS_FILE.exists() else []
        updated = False
        for i, b in enumerate(bookings):
            if b["id"] == booking_id:
                bookings[i] = updated_booking.dict()
                updated = True
                break
        if not updated:
            raise HTTPException(status_code=404, detail="Booking not found")
        BOOKINGS_FILE.write_text(json.dumps(bookings, indent=2))
        return {"status": "updated", "booking": updated_booking}
    except Exception as e:
        logger.error(f"Error updating booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: str):
    try:
        bookings = json.loads(BOOKINGS_FILE.read_text()) if BOOKINGS_FILE.exists() else []
        filtered = [b for b in bookings if b["id"] != booking_id]
        if len(filtered) == len(bookings):
            raise HTTPException(status_code=404, detail="Booking not found")
        BOOKINGS_FILE.write_text(json.dumps(filtered, indent=2))
        return {"status": "deleted", "booking_id": booking_id}
    except Exception as e:
        logger.error(f"Error deleting booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recordings")
def get_recordings():
    if not RECORDINGS_DIR.exists():
        return []

    recordings = []
    for date_dir in sorted(RECORDINGS_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        for f in date_dir.glob("*.mp4"):
            metadata_path = f.with_suffix(".json")
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text())
                    recordings.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {f.name}: {e}")
                    recordings.append({"filename": f.name, "path": str(f)})
            else:
                recordings.append({"filename": f.name, "path": str(f)})
    return recordings

@app.post("/system")
def update_system_settings(settings: SystemSettings):
    try:
        SYSTEM_FILE.write_text(json.dumps(settings.dict(), indent=2))
        return {"status": "success", "settings": settings}
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------
# NEW: SIGNED URL ENDPOINT
# --------------------------
@app.get("/signed-url")
async def get_signed_url(request: Request, key: str):
    print(f"⚡ Request received for key: {key}")
    try:
        decoded_key = urllib.parse.unquote(key)
        bucket = os.getenv("AWS_S3_BUCKET")
        region = os.getenv("AWS_REGION")
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not all([bucket, region, access_key, secret_key]):
            raise Exception("Missing AWS credentials")

        s3 = boto3.client("s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # Check if object exists
        s3.head_object(Bucket=bucket, Key=decoded_key)

        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": decoded_key},
            ExpiresIn=3600
        )
        return {"url": url}

    except s3.exceptions.NoSuchKey:
        return JSONResponse(status_code=404, content={"detail": "File not found in S3"})
    except Exception as e:
        logging.exception("Failed to generate signed URL")
        return JSONResponse(status_code=404, content={"detail": str(e)})

# --------------------------
# NEW: DELETE S3 OBJECT
# --------------------------
@app.delete("/delete-video")
def delete_video(data: DeletePayload):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=data.key)
        logger.info(f"✅ Deleted {data.key} from S3")
        return {"status": "success", "message": f"Deleted {data.key}"}
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream")
def stream_video(request: Request, key: str):
    decoded_key = urllib.parse.unquote(key)
    bucket = os.getenv("AWS_S3_BUCKET")
    region = os.getenv("AWS_REGION")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not all([bucket, region, access_key, secret_key]):
        return JSONResponse(status_code=500, content={"detail": "Missing AWS credentials"})

    s3 = boto3.client("s3",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    # Check if object exists
    try:
        s3.head_object(Bucket=bucket, Key=decoded_key)
    except s3.exceptions.NoSuchKey:
        return JSONResponse(status_code=404, content={"detail": "File not found in S3"})
    except Exception as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})

    # Generate signed URL
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": decoded_key},
        ExpiresIn=3600
    )

    # Forward Range header if present
    range_header = request.headers.get("range")
    headers = {"Range": range_header} if range_header else {}
    s3_response = requests.get(url, stream=True, headers=headers)

    # Prepare response headers
    response_headers = {
        "Content-Type": s3_response.headers.get("Content-Type", "video/mp4"),
        "Content-Length": s3_response.headers.get("Content-Length"),
        "Accept-Ranges": s3_response.headers.get("Accept-Ranges", "bytes"),
        "Content-Range": s3_response.headers.get("Content-Range"),
        "Access-Control-Allow-Origin": "*",
    }
    # Remove None values
    response_headers = {k: v for k, v in response_headers.items() if v}

    status_code = s3_response.status_code if s3_response.status_code in (200, 206) else 200

    return StreamingResponse(
        s3_response.raw,
        status_code=status_code,
        headers=response_headers
    )

@app.get("/media/presign")
def media_presign(
    key: str = Query(..., description="S3 object key"),
    operation: str = Query("get", description="Operation: put, get, or delete"),
    content_type: str = Query(None, description="Content-Type for upload (optional, required if frontend sets Content-Type)")
):
    """
    Generate a presigned S3 URL for upload (PUT), download (GET), or delete (DELETE).
    For PUT: always generate the URL (do not check if file exists). If content_type is provided, include it in the presign Params and require the frontend to use the same Content-Type header.
    For GET/DELETE: optionally check if file exists.
    Uses AWS_USER_MEDIA_BUCKET if set, otherwise AWS_S3_BUCKET.
    """
    decoded_key = urllib.parse.unquote(key)
    bucket = USER_MEDIA_BUCKET
    region = os.getenv("AWS_REGION")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not all([bucket, region, access_key, secret_key]):
        return JSONResponse(status_code=500, content={"detail": "Missing AWS credentials"})

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    if operation == "put":
        params = {"Bucket": bucket, "Key": decoded_key}
        if content_type:
            params["ContentType"] = content_type
        try:
            url = s3.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=3600
            )
            return {"url": url, "method": "PUT", "content_type": content_type}
        except Exception as e:
            logger.error(f"Failed to generate presigned PUT URL: {e}")
            return JSONResponse(status_code=500, content={"detail": str(e)})
    elif operation == "get":
        try:
            s3.head_object(Bucket=bucket, Key=decoded_key)
        except s3.exceptions.ClientError:
            return JSONResponse(status_code=404, content={"detail": "File not found in S3"})
        try:
            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": decoded_key},
                ExpiresIn=3600
            )
            return {"url": url, "method": "GET"}
        except Exception as e:
            logger.error(f"Failed to generate presigned GET URL: {e}")
            return JSONResponse(status_code=500, content={"detail": str(e)})
    elif operation == "delete":
        try:
            s3.head_object(Bucket=bucket, Key=decoded_key)
        except s3.exceptions.ClientError:
            return JSONResponse(status_code=404, content={"detail": "File not found in S3"})
        try:
            url = s3.generate_presigned_url(
                ClientMethod="delete_object",
                Params={"Bucket": bucket, "Key": decoded_key},
                ExpiresIn=3600
            )
            return {"url": url, "method": "DELETE"}
        except Exception as e:
            logger.error(f"Failed to generate presigned DELETE URL: {e}")
            return JSONResponse(status_code=500, content={"detail": str(e)})
    else:
        return JSONResponse(status_code=400, content={"detail": "Invalid operation. Use put, get, or delete."})

@app.post("/media/notify")
async def media_notify(payload: MediaNotifyRequest):
    logger.info(f"Media notify: {payload}")
    user_id = payload.user_id
    user_media_dir = Path(f"/opt/ezrec-backend/media_cache/{user_id}")
    user_media_dir.mkdir(parents=True, exist_ok=True)

    # Map media_type to S3 key and local filename
    media_map = {
        "main_logo_path": (f"{user_id}/logo/logo.png", "logo.png"),
        "intro_video_path": (f"{user_id}/intro-video/intro.mp4", "intro.mp4"),
        "sponsor_logo1_path": (f"{user_id}/sponsor-logo1/logo1.png", "sponsor_logo1.png"),
        "sponsor_logo2_path": (f"{user_id}/sponsor-logo2/logo2.png", "sponsor_logo2.png"),
        "sponsor_logo3_path": (f"{user_id}/sponsor-logo3/logo3.png", "sponsor_logo3.png"),
    }
    s3_key, local_name = media_map.get(payload.media_type, (None, None))
    if s3_key is not None:
        local_path = user_media_dir / local_name
        # Remove old file if it exists
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove old media file {local_path}: {e}")
        # Download the updated file from S3
        try:
            s3.download_file(USER_MEDIA_BUCKET, s3_key, str(local_path))
            logger.info(f"Downloaded {s3_key} to {local_path}")
        except Exception as e:
            logger.info(f"Media file {s3_key} not found or not downloaded: {e}")
    else:
        logger.warning(f"Unknown media_type for notify: {payload.media_type}")

    return {"status": "ok"}

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.options("/share")
async def options_share():
    return {"message": "OK"}

@app.post("/share", response_model=ShareResponse)
def create_share_link(req: ShareRequest):
    token = uuid4().hex
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    created_at = datetime.utcnow().isoformat()
    data = {
        "token": token,
        "video_key": req.key,
        "user_id": req.user_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "access_count": 0,
        "last_accessed": None,
        "revoked": False
    }
    try:
        supabase.table("shared_links").insert(data).execute()
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        raise HTTPException(status_code=500, detail="Failed to create share link")
    base_url = os.getenv("SHARE_BASE_URL", "https://yourdomain.com")
    return {"url": f"{base_url}/share/{token}"}

@app.post("/share/{token}/revoke")
def revoke_share_link(token: str, req: RevokeShareRequest):
    """
    Revoke a share link. Only the user who created the link can revoke it.
    """
    user_id = req.user_id
    try:
        # First check if the link exists and belongs to the user
        res = supabase.table("shared_links").select("*").eq("token", token).eq("user_id", user_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Share link not found or access denied")
        # Update the database to mark as revoked
        supabase.table("shared_links").update({
            "revoked": True,
            "revoked_at": datetime.utcnow().isoformat()
        }).eq("token", token).eq("user_id", user_id).execute()
        logger.info(f"Share link {token} revoked by user {user_id}")
        return {"status": "revoked", "message": "Share link revoked successfully"}
    except Exception as e:
        logger.error(f"Failed to revoke share link: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke share link")

@app.post("/share/{token}/download")
def track_download(token: str, request: Request):
    """
    Track when someone downloads a video from a share link.
    """
    try:
        # Get client IP for basic tracking
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Update download count
        res = supabase.table("shared_links").select("total_downloads").eq("token", token).single().execute()
        current_downloads = res.data.get("total_downloads", 0) if res.data else 0
        
        supabase.table("shared_links").update({
            "total_downloads": current_downloads + 1,
            "last_downloaded": datetime.utcnow().isoformat(),
            "last_download_ip": client_ip,
            "last_download_user_agent": user_agent
        }).eq("token", token).execute()
        
        logger.info(f"Download tracked for token {token} from IP {client_ip}")
        return {"status": "download_tracked", "download_count": current_downloads + 1}
        
    except Exception as e:
        logger.error(f"Failed to track download: {e}")
        raise HTTPException(status_code=500, detail="Failed to track download")

@app.get("/share/analytics/{user_id}")
def get_share_analytics(user_id: str):
    """
    Get analytics for all share links created by a user.
    """
    try:
        # Get all share links for the user
        res = supabase.table("shared_links").select("*").eq("user_id", user_id).execute()
        
        if not res.data:
            return {
                "total_links": 0,
                "active_links": 0,
                "total_views": 0,
                "total_downloads": 0,
                "links": []
            }
        
        links = res.data
        total_links = len(links)
        active_links = len([l for l in links if not l.get("revoked", False) and 
                          (not l.get("expires_at") or datetime.fromisoformat(l.get("expires_at")) > datetime.utcnow())])
        total_views = sum(l.get("access_count", 0) for l in links)
        total_downloads = sum(l.get("total_downloads", 0) for l in links)
        
        return {
            "total_links": total_links,
            "active_links": active_links,
            "total_views": total_views,
            "total_downloads": total_downloads,
            "links": links
        }
        
    except Exception as e:
        logger.error(f"Failed to get share analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get share analytics")

@app.get("/share/analytics/popular")
def get_popular_videos():
    """
    Get most popular shared videos across all users.
    """
    try:
        # This would require a more complex query, but for now we'll get recent links
        res = supabase.table("shared_links").select("*").order("created_at", desc=True).limit(50).execute()
        
        # Group by video_key and calculate stats
        video_stats = {}
        for link in res.data:
            video_key = link.get("video_key")
            if video_key not in video_stats:
                video_stats[video_key] = {
                    "video_key": video_key,
                    "share_count": 0,
                    "total_views": 0,
                    "total_downloads": 0,
                    "last_shared": None
                }
            
            video_stats[video_key]["share_count"] += 1
            video_stats[video_key]["total_views"] += link.get("access_count", 0)
            video_stats[video_key]["total_downloads"] += link.get("total_downloads", 0)
            
            if not video_stats[video_key]["last_shared"] or link.get("created_at") > video_stats[video_key]["last_shared"]:
                video_stats[video_key]["last_shared"] = link.get("created_at")
        
        # Sort by total views
        popular_videos = sorted(video_stats.values(), key=lambda x: x["total_views"], reverse=True)
        
        return {
            "popular_videos": popular_videos[:10]  # Top 10
        }
        
    except Exception as e:
        logger.error(f"Failed to get popular videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to get popular videos")

@app.get("/share/{token}", response_class=HTMLResponse)
def get_shared_video(request: Request, token: str):
    error = None
    video_url = None
    try:
        res = supabase.table("shared_links").select("*").eq("token", token).single().execute()
        row = res.data
    except Exception as e:
        logger.error(f"Share token lookup failed: {e}")
        row = None
        error = "Invalid or expired link."
    if not row:
        error = "Invalid or expired link."
    else:
        expires_at = row.get("expires_at")
        revoked = row.get("revoked", False)
        if revoked:
            error = "This share link has been revoked."
        elif expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            error = "This share link has expired."
        else:
            try:
                video_url = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": S3_BUCKET, "Key": row["video_key"]},
                    ExpiresIn=3600  # 1 hour
                )
                # Analytics: increment access_count and update last_accessed
                new_access_count = (row.get("access_count") or 0) + 1
                supabase.table("shared_links").update({
                    "access_count": new_access_count,
                    "last_accessed": datetime.utcnow().isoformat()
                }).eq("token", token).execute()
            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {e}")
                error = "Failed to generate video link."
    
    # Prepare template context with analytics
    template_context = {
        "request": request, 
        "video_url": video_url, 
        "error": error,
        "token": token,
        "access_count": row.get("access_count", 0) if row else 0,
        "last_accessed": row.get("last_accessed") if row else None,
        "expires_at": row.get("expires_at") if row else None
    }
    
    return templates.TemplateResponse("share_video.html", template_context)

@app.get("/share/{token}/download_url")
def get_download_url(token: str):
    """
    Return a fresh presigned S3 URL for downloading the shared video.
    """
    try:
        res = supabase.table("shared_links").select("*").eq("token", token).single().execute()
        row = res.data
        if not row:
            return JSONResponse(status_code=404, content={"detail": "Invalid or expired link."})
        expires_at = row.get("expires_at")
        revoked = row.get("revoked", False)
        if revoked or (expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)):
            return JSONResponse(status_code=403, content={"detail": "Link expired or revoked."})
        video_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": row["video_key"],
                "ResponseContentDisposition": "attachment; filename=\"shared_video.mp4\""
            },
            ExpiresIn=3600  # 1 hour
        )
        return {"url": video_url}
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to generate download URL."})

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_HOST_USER)

@app.post("/send-share-email")
def send_share_email(req: SendShareEmailRequest):
    # Security: Validate the user is allowed to send this link (TODO: implement real check)
    # For now, just check the video exists
    try:
        res = supabase.table("videos").select("*").eq("recording_id", req.videoId).single().execute()
        if not res.data:
            return JSONResponse(status_code=404, content={"detail": "Video not found."})
    except Exception as e:
        logger.error(f"Error validating video: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal error."})

    # Compose HTML email (dark theme, EZREC logo, styled like share page)
    html = f"""
    <html>
    <head>
    <style>
        body {{ background: #101014; color: #fff; font-family: 'Montserrat', Arial, sans-serif; margin: 0; padding: 0; }}
        .container {{ background: #18181c; border-radius: 16px; max-width: 480px; margin: 32px auto; padding: 32px; box-shadow: 0 4px 24px #0004; }}
        .logo {{ font-size: 2rem; font-weight: 700; letter-spacing: 2px; color: #fff; display: flex; align-items: center; }}
        .logo .red-dot {{ color: #ff2d2d; font-size: 2.2rem; margin-left: 2px; }}
        .btn {{ display: inline-block; margin-top: 24px; padding: 14px 32px; background: linear-gradient(90deg, #0077ff 60%, #0056cc 100%); color: #fff; border: none; border-radius: 6px; font-size: 1.1em; font-weight: 600; letter-spacing: 1px; text-decoration: none; }}
        .btn:hover {{ background: linear-gradient(90deg, #0056cc 60%, #0077ff 100%); }}
        .info {{ margin-top: 18px; padding: 14px; background: #15151a; border-radius: 6px; font-size: 1em; color: #b0b0b0; text-align: center; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">EZREC<span class="red-dot">&bull;</span></div>
            <h2 style="color:#fff;">You've received a shared video!</h2>
            <div class="info">
                <p>Someone has shared a video with you via EZREC. Click the button below to view and download the video.</p>
            </div>
            <a href="{req.link}" class="btn">View Shared Video</a>
            <div class="info" style="margin-top:32px;">
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break:break-all;"><a href="{req.link}" style="color:#0077ff;">{req.link}</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    # Send email
    try:
        msg = EmailMessage()
        msg["Subject"] = "You've received a shared video from EZREC"
        msg["From"] = EMAIL_FROM
        msg["To"] = req.email
        msg.set_content("You have received a shared video. Please view it in an HTML-capable email client.")
        msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Failed to send share email: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to send email."})

    # Optionally, update the booking record with the email (if videoId is provided)
    try:
        supabase.table("videos").update({"shared_email": req.email}).eq("recording_id", req.videoId).execute()
    except Exception as e:
        logger.warning(f"Failed to update video with shared email: {e}")

    return {"status": "ok"}

status_path = Path("/opt/ezrec-backend/status.json")

def read_status():
    if status_path.exists():
        with open(status_path) as f:
            return json.load(f)
    return {}

@app.get("/status/cpu")
def get_cpu():
    return {"cpu_usage": read_status().get("cpu_usage")}

@app.get("/status/memory")
def get_memory():
    return {"memory_usage": read_status().get("memory_usage")}

@app.get("/status/storage")
def get_storage():
    return {"storage": read_status().get("storage")}

@app.get("/status/temperature")
def get_temperature():
    return {"temperature": read_status().get("temperature")}

@app.get("/status/uptime")
def get_uptime():
    return {"uptime": read_status().get("uptime")}

@app.get("/status/errors")
def get_errors():
    return {"errors": read_status().get("errors")}

@app.get("/status/recent_recordings")
def get_recent_recordings():
    return {"recent_recordings": read_status().get("recent_recordings")}

@app.get("/status/is_recording")
def get_is_recording():
    """
    Returns {"is_recording": true/false} based on the value in /opt/ezrec-backend/status.json.
    This reflects the actual recording state as set by recorder.py.
    """
    status_path = Path("/opt/ezrec-backend/status.json")
    if status_path.exists():
        try:
            with open(status_path) as f:
                status = json.load(f)
            return {"is_recording": bool(status.get("is_recording", False))}
        except Exception:
            return {"is_recording": False}
    return {"is_recording": False}

@app.get("/status/network")
def get_network():
    return {"network": read_status().get("network")}

@app.post("/delete-user-data")
def delete_user_data(user_id: str = Query(...)):
    import json
    from pathlib import Path
    # Delete local recordings for user
    rec_dir = Path("/opt/ezrec-backend/recordings")
    for date_dir in rec_dir.glob("*/"):
        for f in date_dir.glob("*.mp4"):
            meta_path = f.with_suffix(".json")
            if meta_path.exists():
                try:
                    with open(meta_path) as mf:
                        meta = json.load(mf)
                    if meta.get("user_id") == user_id:
                        f.unlink(missing_ok=True)
                        meta_path.unlink(missing_ok=True)
                        # Also remove .done, .completed, .lock if present
                        for ext in [".done", ".completed", ".lock"]:
                            aux = f.with_suffix(ext)
                            if aux.exists():
                                aux.unlink()
                except Exception:
                    continue
    # Delete media cache for user
    media_cache = Path(f"/opt/ezrec-backend/media_cache/{user_id}")
    if media_cache.exists():
        shutil.rmtree(media_cache)
    # Remove user bookings from local cache
    bookings_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    if bookings_file.exists():
        try:
            with open(bookings_file) as f:
                bookings = json.load(f)
            bookings = [b for b in bookings if b.get("user_id") != user_id]
            with open(bookings_file, "w") as f:
                json.dump(bookings, f, indent=2)
        except Exception:
            pass
    return {"status": "ok"}

@app.get("/status/next_booking")
def get_next_booking():
    now = datetime.now(timezone.utc)
    bookings_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    if not bookings_file.exists():
        return {"start_time": None}
    try:
        with open(bookings_file) as f:
            data = json.load(f)
        
        # Handle both old and new booking formats
        if isinstance(data, list):
            bookings = data
        elif isinstance(data, dict) and 'bookings' in data:
            bookings = data['bookings']
        else:
            return {"start_time": None}
        
        # Find the next booking with start_time > now
        next_b = None
        for b in bookings:
            try:
                st = datetime.fromisoformat(b["start_time"]).astimezone(timezone.utc)
                if st > now:
                    if not next_b or st < datetime.fromisoformat(next_b["start_time"]).astimezone(timezone.utc):
                        next_b = b
            except Exception:
                continue
        if not next_b:
            return {"start_time": None}
        return {
            "start_time": next_b["start_time"],
            "end_time": next_b.get("end_time"),
            "user_id": next_b.get("user_id"),
            "booking_id": next_b.get("id"),
            "status": next_b.get("status")
        }
    except Exception:
        return {"start_time": None}

@app.get("/recording-logs")
def get_recording_logs(limit: int = 10):
    """Get recent recording logs and status"""
    try:
        logs = []
        
        # Get recent recordings
        recordings_dir = Path("/opt/ezrec-backend/recordings")
        if recordings_dir.exists():
            for date_dir in sorted(recordings_dir.glob("*"), reverse=True)[:3]:
                if date_dir.is_dir():
                    recordings = list(date_dir.glob("*.mp4"))
                    for recording in sorted(recordings, key=lambda x: x.stat().st_mtime, reverse=True)[:limit//3]:
                        try:
                            stat = recording.stat()
                            metadata_file = recording.with_suffix(".json")
                            metadata = {}
                            
                            if metadata_file.exists():
                                with open(metadata_file) as f:
                                    metadata = json.load(f)
                            
                            logs.append({
                                "type": "recording",
                                "filename": recording.name,
                                "date": date_dir.name,
                                "size_mb": round(stat.st_size / (1024*1024), 2),
                                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "booking_id": metadata.get("booking_id"),
                                "user_id": metadata.get("user_id"),
                                "status": "completed" if recording.with_suffix(".done").exists() else "processing"
                            })
                        except Exception as e:
                            logger.warning(f"Error processing recording {recording}: {e}")
        
        # Get recent log entries
        log_file = Path("/opt/ezrec-backend/logs/dual_recorder.log")
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:]  # Last 100 lines
                    
                    for line in recent_lines[-limit//2:]:
                        if any(keyword in line for keyword in ["ERROR", "WARNING", "INFO", "Recording", "Merge"]):
                            logs.append({
                                "type": "log",
                                "message": line.strip(),
                                "timestamp": line[:19] if len(line) > 19 else "unknown"
                            })
            except Exception as e:
                logger.warning(f"Error reading log file: {e}")
        
        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.get("created", x.get("timestamp", "")), reverse=True)
        
        return {
            "logs": logs[:limit],
            "total": len(logs),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recording logs: {e}")
        return {"logs": [], "total": 0, "error": str(e)}

@app.get("/booking-stats")
def get_booking_stats():
    """Get booking statistics"""
    try:
        bookings_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
        if not bookings_file.exists():
            return {"stats": {}, "error": "No bookings file found"}
        
        with open(bookings_file) as f:
            data = json.load(f)
        
        # Handle both old and new booking formats
        if isinstance(data, list):
            bookings = data
        elif isinstance(data, dict) and 'bookings' in data:
            bookings = data['bookings']
        else:
            return {"stats": {}, "error": "Invalid booking format"}
        
        # Calculate statistics
        total_bookings = len(bookings)
        today = datetime.now().date()
        
        today_bookings = 0
        completed_bookings = 0
        failed_bookings = 0
        recording_bookings = 0
        
        for booking in bookings:
            try:
                # Count today's bookings
                start_time = datetime.fromisoformat(booking["start_time"].replace('Z', '+00:00'))
                if start_time.date() == today:
                    today_bookings += 1
                
                # Count by status
                status = booking.get("status", "unknown")
                if status == "completed":
                    completed_bookings += 1
                elif status == "failed":
                    failed_bookings += 1
                elif status == "recording":
                    recording_bookings += 1
                    
            except Exception:
                continue
        
        stats = {
            "total_bookings": total_bookings,
            "today_bookings": today_bookings,
            "completed_bookings": completed_bookings,
            "failed_bookings": failed_bookings,
            "recording_bookings": recording_bookings,
            "success_rate": round((completed_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0
        }
        
        return {"stats": stats, "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error getting booking stats: {e}")
        return {"stats": {}, "error": str(e)}

@app.get("/health")
def health_check():
    """Comprehensive system health check endpoint"""
    try:
        import psutil
        import shutil
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "system": {},
            "cameras": {},
            "services": {},
            "warnings": []
        }
        
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = shutil.disk_usage("/opt/ezrec-backend")
            disk_used_percent = (disk.used / disk.total) * 100
            
            health_data["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_used_percent": round(disk_used_percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 1),
                "uptime_seconds": time.time() - psutil.boot_time()
            }
            
            # Check for high resource usage
            if cpu_percent > 80:
                health_data["warnings"].append(f"High CPU usage: {cpu_percent:.1f}%")
                health_data["status"] = "degraded"
            
            if memory.percent > 85:
                health_data["warnings"].append(f"High memory usage: {memory.percent:.1f}%")
                health_data["status"] = "degraded"
            
            if disk_used_percent > 90:
                health_data["warnings"].append(f"Low disk space: {disk_used_percent:.1f}% used")
                health_data["status"] = "degraded"
                
        except Exception as e:
            health_data["system"]["error"] = str(e)
            health_data["status"] = "error"
        
        # Temperature check (Raspberry Pi specific)
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000
                health_data["system"]["temperature_c"] = temp
                
                if temp > 70:
                    health_data["warnings"].append(f"High temperature: {temp:.1f}°C")
                    health_data["status"] = "degraded"
        except:
            health_data["system"]["temperature_c"] = "unknown"
        
        # Camera devices check
        try:
            import subprocess
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                devices = []
                for line in result.stdout.split('\n'):
                    if '/dev/video' in line:
                        device = line.strip().split()[0]
                        devices.append(device)
                
                health_data["cameras"] = {
                    "devices": devices,
                    "count": len(devices),
                    "status": "available" if len(devices) >= 2 else "insufficient"
                }
                
                if len(devices) < 2:
                    health_data["warnings"].append(f"Only {len(devices)} camera device(s) found")
                    health_data["status"] = "degraded"
                    
            else:
                health_data["cameras"] = {
                    "error": "v4l2-ctl failed",
                    "status": "error"
                }
                health_data["status"] = "error"
                
        except Exception as e:
            health_data["cameras"] = {
                "error": str(e),
                "status": "error"
            }
            health_data["status"] = "error"
        
        # Service status check
        try:
            import subprocess
            services = ["dual_recorder", "video_worker", "system_status", "ezrec-api"]
            service_status = {}
            
            for service in services:
                try:
                    result = subprocess.run(['systemctl', 'is-active', f'{service}.service'], 
                                          capture_output=True, text=True, timeout=5)
                    status = result.stdout.strip()
                    service_status[service] = status
                    
                    if status != "active":
                        health_data["warnings"].append(f"Service {service} is {status}")
                        health_data["status"] = "degraded"
                        
                except Exception:
                    service_status[service] = "unknown"
            
            health_data["services"] = service_status
            
        except Exception as e:
            health_data["services"] = {"error": str(e)}
        
        # Recording status check
        try:
            status_file = Path("/opt/ezrec-backend/status.json")
            if status_file.exists():
                with open(status_file) as f:
                    status_data = json.load(f)
                    health_data["recording"] = {
                        "is_recording": status_data.get("is_recording", False),
                        "last_update": status_data.get("last_update", "unknown")
                    }
            else:
                health_data["recording"] = {"status": "no_status_file"}
        except Exception as e:
            health_data["recording"] = {"error": str(e)}
        
        # FFmpeg availability check
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            health_data["ffmpeg"] = {
                "available": result.returncode == 0,
                "version": result.stdout.split('\n')[0] if result.returncode == 0 else "unknown"
            }
            
            if result.returncode != 0:
                health_data["warnings"].append("FFmpeg not available")
                health_data["status"] = "error"
                
        except Exception as e:
            health_data["ffmpeg"] = {"error": str(e), "available": False}
            health_data["status"] = "error"
        
        # Network connectivity check
        try:
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=5)
            health_data["network"] = {
                "internet": result.returncode == 0,
                "status": "connected" if result.returncode == 0 else "disconnected"
            }
            
            if result.returncode != 0:
                health_data["warnings"].append("No internet connectivity")
                health_data["status"] = "degraded"
                
        except Exception as e:
            health_data["network"] = {"error": str(e), "internet": False}
        
        return health_data
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
