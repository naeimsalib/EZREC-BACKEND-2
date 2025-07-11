from supabase import create_client
from fastapi import FastAPI, HTTPException, Query, Request, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import urllib.parse
import requests
import shutil
from uuid import uuid4

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

# --------------------------
# ENDPOINTS
# --------------------------
@app.get("/")
def root():
    return {"message": "EZREC FastAPI is running"}

@app.get("/status")
def status():
    return {"status": "online", "time": datetime.utcnow().isoformat()}

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
        for b in bookings:
            logger.info(f"➡️ Booking: {b.dict()}")

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
    # Directory for this user's media
    user_media_dir = Path(f"/opt/ezrec-backend/media_cache/{user_id}")
    user_media_dir.mkdir(parents=True, exist_ok=True)

    # Remove all old files for this user
    for f in user_media_dir.glob("*"):
        try:
            f.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove old media file {f}: {e}")

    # Download all user media from S3 (logo, intro, sponsor logos)
    # Assume keys are predictable: logo/logo.png, intro-video/intro.mp4, sponsor_logo_0.png, etc.
    s3_keys = [
        f"{user_id}/logo/logo.png",
        f"{user_id}/intro-video/intro.mp4",
        f"{user_id}/sponsor_logo_0.png",
        f"{user_id}/sponsor_logo_1.png",
        f"{user_id}/sponsor_logo_2.png",
    ]
    for key in s3_keys:
        local_path = user_media_dir / Path(key).name
        try:
            s3.download_file(USER_MEDIA_BUCKET, key, str(local_path))
            logger.info(f"Downloaded {key} to {local_path}")
        except Exception as e:
            logger.info(f"Media file {key} not found or not downloaded: {e}")

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
def revoke_share_link(token: str, user_id: str):
    """
    Revoke a share link. Only the user who created the link can revoke it.
    """
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
            Params={"Bucket": S3_BUCKET, "Key": row["video_key"]},
            ExpiresIn=3600  # 1 hour
        )
        return {"url": video_url}
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to generate download URL."})
