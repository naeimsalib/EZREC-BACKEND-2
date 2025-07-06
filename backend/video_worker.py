#!/usr/bin/env python3
"""
EZREC - Video Worker Script
"""

import os
import sys
import time
import subprocess
import shutil
import uuid
import json
import requests
import boto3
from boto3.s3.transfer import TransferConfig
from pathlib import Path
from datetime import datetime
import logging
import pytz
from dotenv import load_dotenv
from supabase import create_client

# ✅ Fix the import path for booking_utils.py
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

# Load environment variables
load_dotenv("/opt/ezrec-backend/.env", override=True)

TIMEZONE_NAME = os.getenv("TIMEZONE", "UTC")
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)

required_env_vars = [
    "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "USER_ID", "CAMERA_ID",
    "AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"
]
for var in required_env_vars:
    if not os.getenv(var):
        raise RuntimeError(f"Missing env: {var}")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
PROCESSED_DIR = Path("/opt/ezrec-backend/processed")
MEDIA_CACHE_DIR = Path("/opt/ezrec-backend/media_cache")
LOG_FILE = "/opt/ezrec-backend/logs/video_worker.log"
CHECK_INTERVAL = int(os.getenv("VIDEO_WORKER_CHECK_INTERVAL", "15"))

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger("video_worker")

def get_duration(file: Path) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(file)
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def upload_file_chunked(local_path: Path, s3_key: str) -> str:
    try:
        config = TransferConfig(
            multipart_threshold=20 * 1024 * 1024,
            multipart_chunksize=10 * 1024 * 1024
        )
        s3.upload_file(
            str(local_path), S3_BUCKET, s3_key,
            ExtraArgs={"ContentType": "video/mp4"}, Config=config
        )
        return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    except Exception as e:
        log.error(f"❌ Upload failed: {e}")
        return None

def download_file(url: str, path: Path):
    if not path.exists():
        r = requests.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def fetch_user_media(user_id: str):
    try:
        res = supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        return res.data.get("intro_video_url"), res.data.get("logo_url") if res.data else (None, None)
    except Exception:
        return None, None

def process_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    output_file = PROCESSED_DIR / date_dir.name / raw_file.name
    output_file.parent.mkdir(parents=True, exist_ok=True)

    intro_url, logo_url = fetch_user_media(user_id)
    intro_path = MEDIA_CACHE_DIR / f"intro_{user_id}.mp4"
    logo_path = MEDIA_CACHE_DIR / f"logo_{user_id}.png"

    if intro_url:
        download_file(intro_url, intro_path)
    if logo_url:
        download_file(logo_url, logo_path)

    try:
        intermediate = raw_file
        if intro_path.exists():
            concat_txt = MEDIA_CACHE_DIR / f"concat_{uuid.uuid4().hex}.txt"
            concat_txt.write_text(f"file '{intro_path}'\nfile '{raw_file}'\n")
            intermediate = output_file.with_name("with_intro.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-c", "copy", str(intermediate)
            ], check=True)

        if logo_path.exists():
            subprocess.run([
                "ffmpeg", "-y", "-i", str(intermediate), "-i", str(logo_path),
                "-filter_complex", "overlay=W-w-10:H-h-10",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                str(output_file)
            ], check=True)
        else:
            shutil.copy(intermediate, output_file)

        return output_file
    except Exception as e:
        log.error(f"FFmpeg error: {e}")
        return None

def insert_video_metadata(payload: dict) -> bool:
    headers = {
        "apikey": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = requests.post(
        f"{os.getenv('SUPABASE_URL')}/rest/v1/videos",
        headers=headers, json=payload
    )
    return r.status_code in (200, 201)

def main():
    while True:
        for date_dir in RECORDINGS_DIR.glob("*/"):
            for raw_file in date_dir.glob("*.mp4"):
                done = raw_file.with_suffix(".done")
                completed = raw_file.with_suffix(".completed")
                lock = raw_file.with_suffix(".lock")
                meta_path = raw_file.with_suffix(".json")
                # Only process if .done exists, .completed does not, and .lock does not exist
                if not done.exists() or completed.exists() or lock.exists():
                    continue
                # ... rest of the processing logic ...
                lock.touch()
                if not meta_path.exists():
                    lock.unlink()  # Clean up lock if meta missing
                    continue

                try:
                    with open(meta_path) as f:
                        meta = json.load(f)

                    user_id = meta["user_id"]
                    booking_id = meta["booking_id"]

                    update_booking_status(booking_id, "Processing")

                    final_file = process_video(raw_file, user_id, date_dir)

                    if final_file:
                        update_booking_status(booking_id, "Uploading")
                        s3_key = f"{user_id}/{date_dir.name}/{final_file.name}"
                        s3_url = upload_file_chunked(final_file, s3_key)
                        if s3_url:
                            payload = {
                                "user_id": user_id,
                                "video_url": s3_url,
                                "date": date_dir.name,
                                "recording_id": raw_file.stem,
                                "duration_seconds": int(get_duration(raw_file)),
                                "uploaded_at": datetime.now(LOCAL_TZ).isoformat(),
                                "filename": final_file.name,
                                "storage_path": s3_key
                            }
                            if insert_video_metadata(payload):
                                update_booking_status(booking_id, "Uploaded")
                                completed.touch()  # Mark as completed
                                # Remove files
                                try:
                                    os.remove(raw_file)
                                except Exception:
                                    pass
                                try:
                                    os.remove(final_file)
                                except Exception:
                                    pass
                                try:
                                    os.remove(done)
                                except Exception:
                                    pass
                                # Optionally remove .json
                                try:
                                    os.remove(meta_path)
                                except Exception:
                                    pass
                                # Remove booking from local cache and update status to Completed
                                try:
                                    cache_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
                                    if cache_file.exists():
                                        with open(cache_file, 'r') as f:
                                            bookings = json.load(f)
                                        bookings = [b for b in bookings if b.get('id') != booking_id]
                                        with open(cache_file, 'w') as f:
                                            json.dump(bookings, f, indent=2)
                                        log.info(f"🗑️ Removed completed booking {booking_id} from cache (video_worker)")
                                    update_booking_status(booking_id, "Completed")
                                except Exception as e:
                                    log.error(f"Error removing booking from cache in video_worker: {e}")
                except Exception as e:
                    log.error(f"Processing error: {e}")
                finally:
                    if lock.exists():
                        lock.unlink()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
