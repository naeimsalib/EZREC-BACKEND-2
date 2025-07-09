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
import socket

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
USER_MEDIA_BUCKET = os.getenv("AWS_USER_MEDIA_BUCKET", S3_BUCKET)
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

user_media_s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# Overlay position mapping
POSITION_MAP = {
    "top_left": "10:10",
    "top_right": "main_w-overlay_w-10:10",
    "top_center": "(main_w-overlay_w)/2:10",
    "bottom_left": "10:main_h-overlay_h-10",
    "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
    "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-10",
}

LOGO_POSITION = os.getenv("LOGO_POSITION", "top_right")
SPONSOR_0_POSITION = os.getenv("SPONSOR_0_POSITION", "bottom_left")
SPONSOR_1_POSITION = os.getenv("SPONSOR_1_POSITION", "bottom_right")
SPONSOR_2_POSITION = os.getenv("SPONSOR_2_POSITION", "bottom_center")
INTRO_POSITION = os.getenv("INTRO_POSITION", "top_left")  # Not used for overlay, but for future

RESOLUTION = os.getenv('RESOLUTION', '1280x720')
try:
    width, height = map(int, RESOLUTION.lower().split('x'))
except Exception:
    width, height = 1280, 720

VIDEO_ENCODER = os.getenv('VIDEO_ENCODER', 'h264_v4l2m2m')

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

def download_file(url: str, path: Path, bucket=None, key=None):
    if path.exists():
        return
    if url and url.startswith("s3://") and bucket and key:
        # Download from S3 directly
        try:
            user_media_s3.download_file(bucket, key, str(path))
        except Exception as e:
            log.error(f"Failed to download s3://{bucket}/{key}: {e}")
    elif url:
        try:
            r = requests.get(url, stream=True)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            log.error(f"Failed to download {url}: {e}")

def fetch_user_media(user_id: str):
    """
    Fetch intro video, logo, and sponsor logos for the user from user_settings table.
    Returns: (intro_url, logo_url, sponsor_logo_urls)
    """
    try:
        res = supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            intro = res.data.get("intro_video_url")
            logo = res.data.get("logo_url")
            sponsors = res.data.get("sponsor_logo_urls") or []
            if isinstance(sponsors, str):
                # In case it's stored as a comma-separated string
                sponsors = [s.strip() for s in sponsors.split(",") if s.strip()]
            return intro, logo, sponsors[:3]
        return None, None, []
    except Exception:
        return None, None, []

# Main logo config (can be a URL or local path)
MAIN_LOGO_URL = os.getenv("MAIN_LOGO_URL")  # e.g. S3 URL
MAIN_LOGO_PATH = os.getenv("MAIN_LOGO_PATH", "/opt/ezrec-backend/main_logo.png")

def download_if_needed(url, path: Path):
    if url and not path.exists():
        try:
            r = requests.get(url, stream=True)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            log.error(f"Failed to download {url}: {e}")
    return path if path.exists() else None

def is_internet_available(host="8.8.8.8", port=53, timeout=3):
    """Check if the internet is available by trying to connect to a DNS server."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def get_video_info(file: Path):
    """Return (codec, width, height, fps, pix_fmt) for a video file using ffprobe."""
    import json as _json
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,avg_frame_rate,pix_fmt",
            "-of", "json", str(file)
        ], capture_output=True, text=True)
        info = _json.loads(result.stdout)
        stream = info['streams'][0]
        codec = stream.get('codec_name')
        width = int(stream.get('width'))
        height = int(stream.get('height'))
        pix_fmt = stream.get('pix_fmt')
        # avg_frame_rate is like '30/1'
        fr = stream.get('avg_frame_rate', '30/1')
        if '/' in fr:
            num, den = fr.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fr)
        return codec, width, height, fps, pix_fmt
    except Exception as e:
        log.error(f"Could not get video info for {file}: {e}")
        return None, None, None, None, None

def process_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    """
    Optimized video processing with hardware acceleration and single-pass operation.
    Tries multiple encoders in order: h264_v4l2m2m, h264_omx, libx264.
    Logs full FFmpeg error output for each attempt.
    """
    output_file = PROCESSED_DIR / date_dir.name / raw_file.name
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Use local cache for user media
    user_media_dir = MEDIA_CACHE_DIR / user_id
    intro_path = user_media_dir / "intro.mp4"
    logo_path = user_media_dir / "logo.png"
    sponsor_paths = [user_media_dir / f"sponsor_logo_{i}.png" for i in range(3)]

    # Sanity check durations
    max_duration = 600  # 10 minutes in seconds
    raw_duration = get_duration(raw_file)
    if raw_duration > max_duration:
        log.warning(f"Main recording duration too long: {raw_duration:.2f}s. Skipping processing.")
        return None
    
    # Check intro duration and trim if needed
    if intro_path.exists():
        intro_duration = get_duration(intro_path)
        if intro_duration > max_duration:
            log.warning(f"Intro video duration too long: {intro_duration:.2f}s. Trimming to {max_duration}s.")
            trimmed_intro = intro_path.with_name("intro_trimmed.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(intro_path), "-t", str(max_duration), "-c", "copy", str(trimmed_intro)
            ], check=True)
            intro_path = trimmed_intro
        # --- NEW: Check intro format and re-encode if needed ---
        codec, w, h, fps, pix_fmt = get_video_info(intro_path)
        needs_reencode = False
        if codec != 'h264':
            needs_reencode = True
        if w != width or h != height:
            needs_reencode = True
        if abs(fps - 30) > 0.5:
            needs_reencode = True
        if pix_fmt != 'yuv420p':
            needs_reencode = True
        if needs_reencode:
            log.info(f"Re-encoding intro video to H.264 1280x720 30fps yuv420p for fast concat...")
            reencoded_intro = intro_path.with_name("intro_reencoded.mp4")
            reencode_cmd = [
                "ffmpeg", "-y", "-threads", "2", "-i", str(intro_path),
                "-vf", f"scale={width}:{height},fps=30",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-pix_fmt", "yuv420p", str(reencoded_intro)
            ]
            result = subprocess.run(reencode_cmd, capture_output=True)
            if result.returncode != 0:
                log.error(f"Intro re-encode failed: {result.stderr.decode()}")
                return None
            intro_path = reencoded_intro

    # --- Two-pass logic if intro video is present ---
    if intro_path.exists():
        concat_output = raw_file.parent / f"concat_{raw_file.name}"
        # Pass 1: Concat and scale intro + main
        concat_cmd = [
            "ffmpeg", "-y", "-threads", "2",
            "-i", str(intro_path), "-i", str(raw_file),
            "-filter_complex",
            f"[0:v]scale={width}:{height},format=yuv420p[intro];"
            f"[1:v]scale={width}:{height},format=yuv420p[main];"
            f"[intro][main]concat=n=2:v=1:a=0[concat]",
            "-map", "[concat]",
            "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", str(concat_output)
        ]
        log.info(f"[Two-pass] Pass 1: Concatenating intro and main video to {concat_output}")
        try:
            start = time.time()
            result = subprocess.run(concat_cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                log.error(f"Concat pass failed: {result.stderr.decode()}")
                return None
            log.info(f"✅ Concat completed in {time.time() - start:.2f}s")
        except subprocess.TimeoutExpired:
            log.error("❌ FFmpeg concat step timed out.")
            return None
        except Exception as e:
            log.error(f"❌ FFmpeg concat error: {e}")
            return None
        # Pass 2: Overlays and encode (hardware if available)
        input_args = ["-i", str(concat_output)]
        filter_parts = []
        last_output = "[0:v]"
        video_inputs = 1
        logo_inputs = []
        if logo_path.exists():
            input_args.extend(["-i", str(logo_path)])
            logo_inputs.append(("logo", video_inputs, LOGO_POSITION))
            video_inputs += 1
        sponsor_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]
        for i, sponsor_path in enumerate(sponsor_paths):
            if sponsor_path.exists():
                input_args.extend(["-i", str(sponsor_path)])
                logo_inputs.append((f"sponsor{i}", video_inputs, sponsor_positions[i]))
                video_inputs += 1
        for name, idx, position in logo_inputs:
            scale_filter = f"[{idx}:v]scale=iw*0.15:ih*0.15[{name}_scaled]"
            filter_parts.append(scale_filter)
            overlay_position = POSITION_MAP.get(position, "top_right")
            overlay_filter = f"{last_output}[{name}_scaled]overlay={overlay_position}:format=auto[{name}_out]"
            filter_parts.append(overlay_filter)
            last_output = f"[{name}_out]"
        ffmpeg_base_cmd = ["ffmpeg", "-y"] + input_args
        if filter_parts:
            filter_complex = ";".join(filter_parts)
            ffmpeg_base_cmd.extend(["-filter_complex", filter_complex, "-map", last_output])
        else:
            ffmpeg_base_cmd.extend(["-map", "0:v"])
        ffmpeg_base_cmd += ["-c:v", VIDEO_ENCODER, "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p", str(output_file)]
        log.info(f"[Two-pass] Pass 2: Applying overlays and encoding to {output_file}")
        try:
            start_time = time.time()
            result = subprocess.run(ffmpeg_base_cmd, check=True, capture_output=True, text=True, timeout=1800)
            end_time = time.time()
            processing_time = end_time - start_time
            log.info(f"\u2705 Video processing completed in {processing_time:.1f}s using {VIDEO_ENCODER}")
            if output_file.exists() and output_file.stat().st_size > 1024:
                return output_file
            else:
                log.error("Output file missing or too small")
                return None
        except subprocess.CalledProcessError as e:
            log.error(f"FFmpeg failed with {VIDEO_ENCODER}: {e.stderr}")
            if VIDEO_ENCODER != 'libx264':
                log.info("Retrying with software encoder libx264...")
                ffmpeg_base_cmd = [arg if arg != VIDEO_ENCODER else 'libx264' for arg in ffmpeg_base_cmd]
                try:
                    start_time = time.time()
                    result = subprocess.run(ffmpeg_base_cmd, check=True, capture_output=True, text=True, timeout=1800)
                    end_time = time.time()
                    processing_time = end_time - start_time
                    log.info(f"\u2705 Video processing completed in {processing_time:.1f}s using libx264 (fallback)")
                    if output_file.exists() and output_file.stat().st_size > 1024:
                        return output_file
                    else:
                        log.error("Output file missing or too small (fallback)")
                        return None
                except Exception as e2:
                    log.error(f"FFmpeg fallback to libx264 failed: {e2}")
            else:
                log.error(f"FFmpeg failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            log.error(f"FFmpeg processing timed out after 30 minutes")
        except Exception as e:
            log.error(f"FFmpeg error: {e}")
        finally:
            if concat_output.exists():
                concat_output.unlink()
        log.error("FFmpeg processing failed. Video not processed.")
        return None
    # --- Single-pass logic if no intro video ---
    # Build optimized single-pass FFmpeg command
    input_args = []
    filter_parts = []
    
    # Add inputs
    video_inputs = 0
    if intro_path.exists():
        input_args.extend(["-i", str(intro_path)])
        video_inputs += 1
    
    input_args.extend(["-i", str(raw_file)])
    main_video_idx = video_inputs
    video_inputs += 1
    
    # Add logo inputs
    logo_inputs = []
    if logo_path.exists():
        input_args.extend(["-i", str(logo_path)])
        logo_inputs.append(("logo", video_inputs, LOGO_POSITION))
        video_inputs += 1
    
    # Add sponsor logo inputs
    sponsor_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]
    for i, sponsor_path in enumerate(sponsor_paths):
        if sponsor_path.exists():
            input_args.extend(["-i", str(sponsor_path)])
            logo_inputs.append((f"sponsor{i}", video_inputs, sponsor_positions[i]))
            video_inputs += 1
    
    # Build filter chain
    if intro_path.exists():
        # Scale and format both intro and main video before concat
        filter_parts.append(f"[0:v]scale={width}:{height},format=yuv420p[intro_scaled]")
        filter_parts.append(f"[{main_video_idx}:v]scale={width}:{height},format=yuv420p[main_scaled]")
        filter_parts.append(f"[intro_scaled][main_scaled]concat=n=2:v=1:a=0[concat]")
        last_output = "[concat]"
    else:
        filter_parts.append(f"[{main_video_idx}:v]scale={width}:{height},format=yuv420p[main_scaled]")
        last_output = "[main_scaled]"
    
    # Add logo overlays (if any)
    for name, idx, position in logo_inputs:
        scale_filter = f"[{idx}:v]scale=iw*0.15:ih*0.15[{name}_scaled]"
        filter_parts.append(scale_filter)
        overlay_position = POSITION_MAP.get(position, "top_right")
        overlay_filter = f"{last_output}[{name}_scaled]overlay={overlay_position}:format=auto[{name}_out]"
        filter_parts.append(overlay_filter)
        last_output = f"[{name}_out]"
    
    # Build FFmpeg command
    ffmpeg_base_cmd = ["ffmpeg", "-y"] + input_args
    if filter_parts:
        filter_complex = ";".join(filter_parts)
        ffmpeg_base_cmd.extend(["-filter_complex", filter_complex, "-map", last_output])
    else:
        ffmpeg_base_cmd.extend(["-map", f"{main_video_idx}:v"])
        ffmpeg_base_cmd.extend(["-vf", f"scale={width}:{height}"])
    ffmpeg_base_cmd += ["-c:v", VIDEO_ENCODER, "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p", str(output_file)]
    log.info(f"Using video encoder: {VIDEO_ENCODER}")
    log.info(f"FFmpeg command: {' '.join(ffmpeg_base_cmd)}")
    try:
        start_time = time.time()
        result = subprocess.run(ffmpeg_base_cmd, check=True, capture_output=True, text=True, timeout=1800)
        end_time = time.time()
        processing_time = end_time - start_time
        log.info(f"\u2705 Video processing completed in {processing_time:.1f}s using {VIDEO_ENCODER}")
        if output_file.exists() and output_file.stat().st_size > 1024:
            return output_file
        else:
            log.error("Output file missing or too small")
            return None
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg failed with {VIDEO_ENCODER}: {e.stderr}")
        if VIDEO_ENCODER != 'libx264':
            log.info("Retrying with software encoder libx264...")
            ffmpeg_base_cmd = [arg if arg != VIDEO_ENCODER else 'libx264' for arg in ffmpeg_base_cmd]
            try:
                start_time = time.time()
                result = subprocess.run(ffmpeg_base_cmd, check=True, capture_output=True, text=True, timeout=1800)
                end_time = time.time()
                processing_time = end_time - start_time
                log.info(f"\u2705 Video processing completed in {processing_time:.1f}s using libx264 (fallback)")
                if output_file.exists() and output_file.stat().st_size > 1024:
                    return output_file
                else:
                    log.error("Output file missing or too small (fallback)")
                    return None
            except Exception as e2:
                log.error(f"FFmpeg fallback to libx264 failed: {e2}")
        else:
            log.error(f"FFmpeg failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        log.error(f"FFmpeg processing timed out after 30 minutes")
    except Exception as e:
        log.error(f"FFmpeg error: {e}")
    log.error("FFmpeg processing failed. Video not processed.")
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

PENDING_UPLOADS_FILE = Path("/opt/ezrec-backend/pending_uploads.json")

def add_pending_upload(final_file, s3_key, meta):
    """Add a video to the pending uploads queue."""
    queue = []
    if PENDING_UPLOADS_FILE.exists():
        try:
            with open(PENDING_UPLOADS_FILE, 'r') as f:
                queue = json.load(f)
        except Exception:
            queue = []
    queue.append({
        "final_file": str(final_file),
        "s3_key": s3_key,
        "meta": meta
    })
    with open(PENDING_UPLOADS_FILE, 'w') as f:
        json.dump(queue, f, indent=2)

def retry_pending_uploads():
    if not is_internet_available():
        log.info("No internet connection. Skipping pending uploads.")
        return
    if not PENDING_UPLOADS_FILE.exists():
        return
    try:
        with open(PENDING_UPLOADS_FILE, 'r') as f:
            queue = json.load(f)
    except Exception:
        queue = []
    new_queue = []
    for item in queue:
        final_file = Path(item["final_file"])
        s3_key = item["s3_key"]
        meta = item["meta"]
        if final_file.exists():
            s3_url = upload_file_chunked(final_file, s3_key)
            if s3_url:
                payload = meta
                payload["video_url"] = s3_url
                payload["uploaded_at"] = datetime.now(LOCAL_TZ).isoformat()
                if insert_video_metadata(payload):
                    log.info(f"✅ Retried upload succeeded: {final_file}")
                    try:
                        os.remove(final_file)
                    except Exception:
                        pass
                    continue  # Don't add to new_queue
        new_queue.append(item)
    with open(PENDING_UPLOADS_FILE, 'w') as f:
        json.dump(new_queue, f, indent=2)
    if not new_queue:
        PENDING_UPLOADS_FILE.unlink()

def main():
    log.info("Video worker started and entering main loop")
    while True:
        retry_pending_uploads()
        for date_dir in RECORDINGS_DIR.glob("*/"):
            log.info(f"Scanning directory: {date_dir}")
            for raw_file in date_dir.glob("*.mp4"):
                done = raw_file.with_suffix(".done")
                completed = raw_file.with_suffix(".completed")
                lock = raw_file.with_suffix(".lock")
                meta_path = raw_file.with_suffix(".json")
                log.info(f"Checking {raw_file.name}: done={done.exists()}, completed={completed.exists()}, lock={lock.exists()}, meta={meta_path.exists()}")
                if not done.exists() or completed.exists() or lock.exists():
                    continue
                lock.touch()
                if not meta_path.exists():
                    lock.unlink()
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
                        payload = {
                            "user_id": user_id,
                            "video_url": None,  # Will be set after upload
                            "date": date_dir.name,
                            "recording_id": raw_file.stem,
                            "duration_seconds": int(get_duration(raw_file)),
                            "uploaded_at": None,
                            "filename": final_file.name,
                            "storage_path": s3_key
                        }
                        if is_internet_available():
                            s3_url = upload_file_chunked(final_file, s3_key)
                            if s3_url:
                                payload["video_url"] = s3_url
                                payload["uploaded_at"] = datetime.now(LOCAL_TZ).isoformat()
                                if insert_video_metadata(payload):
                                    update_booking_status(booking_id, "Uploaded")
                                    completed.touch()
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
                                    try:
                                        os.remove(meta_path)
                                    except Exception:
                                        pass
                                    try:
                                        update_booking_status(booking_id, "Completed")
                                        cache_file = Path("/opt/ezrec-backend/api/local_data/bookings.json")
                                        if cache_file.exists():
                                            with open(cache_file, 'r') as f:
                                                bookings = json.load(f)
                                            bookings = [b for b in bookings if b.get('id') != booking_id]
                                            with open(cache_file, 'w') as f:
                                                json.dump(bookings, f, indent=2)
                                            log.info(f"🗑️ Removed completed booking {booking_id} from cache (video_worker)")
                                    except Exception as e:
                                        log.error(f"Error removing booking from cache in video_worker: {e}")
                                continue
                        # If no internet, add to pending uploads
                        add_pending_upload(final_file, s3_key, payload)
                        log.info(f"No internet. Added {final_file} to pending uploads queue.")
                except Exception as e:
                    log.error(f"Processing error: {e}")
                finally:
                    if lock.exists():
                        lock.unlink()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
