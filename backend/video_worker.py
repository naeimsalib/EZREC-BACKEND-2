#!/usr/bin/env python3
# EZREC - Video Worker Script (fully updated, improved)

import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import shutil
import uuid
import json
import requests
import boto3
from boto3.s3.transfer import TransferConfig
import logging

# Load env without overriding systemd
load_dotenv("/opt/ezrec-backend/.env", override=False)

# --- Required env vars check ---
REQUIRED_VARS = [
    "SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID",
    "AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"
]
missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {missing}")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
USER_ID = os.getenv("USER_ID")
CAMERA_ID = os.getenv("CAMERA_ID")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("AWS_S3_BUCKET")
s3 = boto3.client("s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION
)

RECORDINGS_DIR = Path("/opt/ezrec-backend/recordings")
PROCESSED_DIR = Path("/opt/ezrec-backend/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_CACHE_DIR = Path("/opt/ezrec-backend/media_cache")
MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

LOCK_EXTENSION = ".lock"
PROCESSED_EXTENSION = ".done"
VIDEO_WORKER_CHECK_INTERVAL = int(os.getenv("VIDEO_WORKER_CHECK_INTERVAL", "15"))
LOG_FILE = "/opt/ezrec-backend/logs/video_worker.log"

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
def _log(msg):
    print(f"[video_worker] {datetime.now():%Y-%m-%d %H:%M:%S} - {msg}")
    logging.info(msg)

# --- Utility functions ---
def _get_video_duration(path: Path) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return float(result.stdout)
    except Exception as e:
        _log(f"Failed to get duration: {e}")
        return 0.0

def upload_large_file_to_s3(file_path, bucket_name, s3_key):
    config = TransferConfig(
        multipart_threshold=50 * 1024 * 1024,
        multipart_chunksize=10 * 1024 * 1024,
        use_threads=True
    )
    try:
        _log(f"\U0001F4E4 Uploading {file_path.name} to s3://{bucket_name}/{s3_key}")
        s3.upload_file(str(file_path), bucket_name, s3_key, Config=config,
                       ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"})
        url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        _log("✅ Upload completed")
        return url
    except Exception as e:
        _log(f"❌ Upload failed: {e}")
        return None

def _download_if_needed(url: str, dest: Path) -> Path:
    if not url: return None
    if dest.exists(): return dest
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(1024): f.write(chunk)
            _log(f"Downloaded: {dest}")
            return dest
        else:
            _log(f"Download failed ({r.status_code}): {url}")
    except Exception as e:
        _log(f"Download error: {e}")
    return None

def _fetch_intro_logo(user_id: str):
    try:
        res = supabase.table("user_settings").select("intro_video_url,logo_url").eq("user_id", user_id).single().execute()
        return res.data.get("intro_video_url"), res.data.get("logo_url") if res.data else (None, None)
    except Exception as e:
        _log(f"Error fetching intro/logo: {e}")
        return None, None

def _process_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    # Mirror date subfolder in processed dir
    processed_date_dir = PROCESSED_DIR / date_dir.name
    processed_date_dir.mkdir(parents=True, exist_ok=True)
    output_file = processed_date_dir / raw_file.name
    intro_url, logo_url = _fetch_intro_logo(user_id)
    intro_path = MEDIA_CACHE_DIR / f"intro_{user_id}.mp4" if intro_url else None
    logo_path = MEDIA_CACHE_DIR / f"logo_{user_id}.png" if logo_url else None
    concat_list = concat_output = None

    try:
        if intro_url: _download_if_needed(intro_url, intro_path)
        if logo_url: _download_if_needed(logo_url, logo_path)

        input_for_logo = raw_file
        if intro_path and intro_path.exists():
            concat_list = Path(f"/tmp/concat_{uuid.uuid4().hex}.txt")
            with open(concat_list, "w") as f:
                f.write(f"file '{intro_path}'\nfile '{raw_file}'\n")
            concat_output = output_file.with_suffix(".concat.mp4")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                            "-c", "copy", str(concat_output)], check=True)
            input_for_logo = concat_output

        if logo_path and logo_path.exists():
            subprocess.run([
                "ffmpeg", "-y", "-i", str(input_for_logo), "-i", str(logo_path),
                "-filter_complex", "overlay=W-w-10:H-h-10", "-c:v", "libx264",
                "-preset", "fast", "-crf", "23", str(output_file)
            ], check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", str(input_for_logo),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", str(output_file)
            ], check=True)

        if concat_output and concat_output.exists(): concat_output.unlink()
        if concat_list and concat_list.exists(): concat_list.unlink()
        _log(f"✅ FFmpeg complete: {output_file.name}")
        return output_file

    except Exception as e:
        _log(f"❌ FFmpeg error: {e}")
        # Mark unprocessed video in Supabase
        try:
            supabase.table("videos").insert({
                "user_id": user_id,
                "video_url": None,
                "date": date_dir.name,
                "recording_id": raw_file.stem,
                "duration_seconds": 0,
                "processing_error": str(e)
            }).execute()
        except Exception as db_e:
            _log(f"Failed to mark unprocessed video in Supabase: {db_e}")
        shutil.copy(raw_file, output_file)
        return output_file


def cleanup_stale_locks():
    # Remove .lock files older than 1 hour
    for date_dir in RECORDINGS_DIR.glob("*/"):
        for lock_file in date_dir.glob(f"*{LOCK_EXTENSION}"):
            try:
                if lock_file.stat().st_mtime < time.time() - 3600:
                    _log(f"Removing stale lock file: {lock_file}")
                    lock_file.unlink()
            except Exception as e:
                _log(f"Error cleaning up lock file {lock_file}: {e}")

def main():
    _log("🎬 Video Worker running")
    cleanup_stale_locks()
    while True:
        for date_dir in RECORDINGS_DIR.glob("*/"):
            for video_file in date_dir.glob("*.mp4"):
                lock_file = video_file.with_suffix(LOCK_EXTENSION)
                done_file = video_file.with_suffix(PROCESSED_EXTENSION)
                if done_file.exists() or lock_file.exists(): continue

                lock_file.touch()
                try:
                    meta_path = video_file.with_suffix(".json")
                    if not meta_path.exists():
                        _log(f"⚠️ Missing metadata: {meta_path}")
                        continue
                    with open(meta_path) as f:
                        meta = json.load(f)

                    user_id = meta.get("user_id")
                    booking_id = meta.get("booking_id")
                    duration = _get_video_duration(video_file)
                    processed_file = _process_video(video_file, user_id, date_dir)

                    if not processed_file.exists():
                        _log(f"❌ Missing processed file: {processed_file}")
                        continue

                    # Update booking status to video_processed
                    supabase.table("bookings").update({"status": "video_processed"}).eq("id", booking_id).execute()

                    # S3 key mirrors date subfolder
                    s3_key = f"{user_id}/{date_dir.name}/{processed_file.name}"
                    url = upload_large_file_to_s3(processed_file, S3_BUCKET, s3_key)
                    if not url:
                        _log(f"🔥 Failed upload: {processed_file}")
                        continue

                    supabase.table("videos").insert({
                        "user_id": user_id,
                        "video_url": url,
                        "date": date_dir.name,
                        "recording_id": video_file.stem,
                        "duration_seconds": duration
                    }).execute()

                    supabase.table("bookings").update({"status": "video_uploaded"}).eq("id", booking_id).execute()
                    # Optionally, do not delete booking, just mark as uploaded
                    # supabase.table("bookings").delete().eq("id", booking_id).execute()

                    _log(f"✅ Uploaded and saved metadata for {processed_file.name}")
                    os.remove(processed_file)
                    done_file.touch()
                except Exception as e:
                    _log(f"🔥 Worker error: {e}")
                finally:
                    if lock_file.exists(): lock_file.unlink()
        time.sleep(VIDEO_WORKER_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
