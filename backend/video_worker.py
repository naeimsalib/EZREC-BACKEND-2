#!/usr/bin/env python3
# EZREC - Video Worker Script (Updated for S3 folder structure and test scenarios)

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import shutil
import uuid
import json
import requests
import boto3
from boto3.s3.transfer import TransferConfig
import logging

# Load environment variables
load_dotenv("/opt/ezrec-backend/.env", override=False)

# Verify required environment variables
required_env_vars = [
    "SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID",
    "AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"
]
missing = [var for var in required_env_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"Missing environment variables: {missing}")

# Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# AWS S3 client
s3 = boto3.client("s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")

# Paths
RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
PROCESSED_DIR = Path("/opt/ezrec-backend/processed")
MEDIA_CACHE_DIR = Path("/opt/ezrec-backend/media_cache")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Constants
LOCK_EXT = ".lock"
DONE_EXT = ".done"
LOG_FILE = "/opt/ezrec-backend/logs/video_worker.log"
CHECK_INTERVAL = int(os.getenv("VIDEO_WORKER_CHECK_INTERVAL", "15"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("video_worker")

def get_duration(file: Path) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file)
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0.0

def upload_file_chunked(local_path: Path, s3_key: str) -> str:
    try:
        config = TransferConfig(multipart_threshold=20*1024*1024, multipart_chunksize=10*1024*1024)
        s3.upload_file(str(local_path), S3_BUCKET, s3_key, ExtraArgs={
            "ContentType": "video/mp4", "ACL": "public-read"
        }, Config=config)
        s3_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        log.info(f"📤 Uploaded to S3: {s3_url}")
        return s3_url
    except Exception as e:
        log.error(f"❌ Upload failed: {e}")
        return None

def download_file(url: str, path: Path):
    try:
        if not path.exists():
            r = requests.get(url, stream=True)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            log.info(f"✅ Downloaded: {path}")
    except Exception as e:
        log.error(f"❌ Download error: {e}")

def fetch_user_media(user_id: str):
    try:
        res = supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            return res.data.get("intro_video_url"), res.data.get("logo_url")
    except Exception as e:
        log.error(f"Error fetching media: {e}")
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
        # Add intro
        if intro_path.exists():
            concat_txt = MEDIA_CACHE_DIR / f"concat_{uuid.uuid4().hex}.txt"
            concat_txt.write_text(f"file '{intro_path}'\nfile '{raw_file}'\n")
            intermediate = output_file.with_name("with_intro.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-c", "copy", str(intermediate)
            ], check=True)

        # Add logo
        if logo_path.exists():
            subprocess.run([
                "ffmpeg", "-y", "-i", str(intermediate), "-i", str(logo_path),
                "-filter_complex", "overlay=W-w-10:H-h-10",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast", str(output_file)
            ], check=True)
        else:
            shutil.copy(intermediate, output_file)

        return output_file

    except Exception as e:
        log.error(f"FFmpeg error: {e}")
        return None

def cleanup_old_locks():
    for date_dir in RECORDINGS_DIR.glob("*/"):
        for lock in date_dir.glob(f"*{LOCK_EXT}"):
            if time.time() - lock.stat().st_mtime > 3600:
                log.info(f"Removing old lock: {lock}")
                lock.unlink()

def main():
    log.info("🎞️  Video worker started")
    cleanup_old_locks()

    while True:
        for date_dir in RECORDINGS_DIR.glob("*/"):
            for raw_file in date_dir.glob("*.mp4"):
                lock = raw_file.with_suffix(LOCK_EXT)
                done = raw_file.with_suffix(DONE_EXT)
                if lock.exists() or done.exists():
                    continue

                lock.touch()
                meta_path = raw_file.with_suffix(".json")
                if not meta_path.exists():
                    log.warning(f"No metadata found for: {raw_file}")
                    continue

                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    user_id = meta["user_id"]
                    booking_id = meta["booking_id"]
                    duration = get_duration(raw_file)
                    final_file = process_video(raw_file, user_id, date_dir)

                    if final_file:
                        s3_key = f"{user_id}/{date_dir.name}/{final_file.name}"
                        s3_url = upload_file_chunked(final_file, s3_key)
                        if s3_url:
                            supabase.table("videos").insert({
                                "user_id": user_id,
                                "video_url": s3_url,
                                "date": date_dir.name,
                                "recording_id": raw_file.stem,
                                "duration_seconds": duration
                            }).execute()
                            supabase.table("bookings").update({"status": "video_uploaded"}).eq("id", booking_id).execute()
                            done.touch()
                            os.remove(final_file)
                            log.info(f"✅ Uploaded: {s3_key}")
                        else:
                            log.error(f"Failed to upload {final_file}")
                except Exception as e:
                    log.error(f"Processing error: {e}")
                finally:
                    if lock.exists(): lock.unlink()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
