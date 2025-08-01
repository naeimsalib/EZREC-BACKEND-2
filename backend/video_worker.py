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
from enhanced_merge import merge_videos_with_retry, MergeResult

# Try to import file locking library, fallback to simple file-based locking
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
    log = logging.getLogger("video_worker")
    log.warning("⚠️ portalocker not available, using simple file-based locking")

# ✅ Fix the import path for booking_utils.py
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

def update_supabase_status(booking_id: str, status: str):
    """Update booking status in Supabase for skipped or failed jobs"""
    try:
        update_booking_status(booking_id, status)
        log.info(f"📡 Updated booking {booking_id} status to {status}")
    except Exception as e:
        log.error(f"❌ Failed to update booking {booking_id} status: {e}")

def extract_booking_id_from_filename(filename: str) -> str:
    """Extract booking ID from filename (e.g., '143000_user123_cam456_merged.mp4' -> 'user123_cam456')"""
    try:
        # Remove extension and split by underscore
        parts = filename.replace('.mp4', '').split('_')
        if len(parts) >= 3:
            # Return user_id_camera_id format
            return f"{parts[1]}_{parts[2]}"
        return filename.replace('.mp4', '')
    except Exception:
        return filename.replace('.mp4', '')

def acquire_file_lock(lock_path: Path, timeout: int = 30) -> bool:
    """Acquire a file lock using portalocker or fallback to simple file-based locking"""
    if HAS_PORTALOCKER:
        try:
            with open(lock_path, 'w') as f:
                portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)
                return True
        except portalocker.LockException:
            return False
        except Exception as e:
            log.warning(f"⚠️ Portalocker failed, falling back to simple locking: {e}")
            return acquire_simple_lock(lock_path, timeout)
    else:
        return acquire_simple_lock(lock_path, timeout)

def acquire_simple_lock(lock_path: Path, timeout: int = 30) -> bool:
    """Simple file-based locking with timeout"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to create the lock file atomically
            lock_path.touch(exist_ok=False)
            return True
        except FileExistsError:
            # Lock file exists, wait a bit and try again
            time.sleep(0.1)
        except Exception as e:
            log.error(f"❌ Error acquiring lock: {e}")
            return False
    return False

def release_file_lock(lock_path: Path):
    """Release a file lock"""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception as e:
        log.error(f"❌ Error releasing lock: {e}")

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

LOGO_POSITION = os.getenv("LOGO_POSITION", "bottom_right")
SPONSOR_0_POSITION = os.getenv("SPONSOR_0_POSITION", "bottom_left")
SPONSOR_1_POSITION = os.getenv("SPONSOR_1_POSITION", "bottom_right")
SPONSOR_2_POSITION = os.getenv("SPONSOR_2_POSITION", "bottom_center")
INTRO_POSITION = os.getenv("INTRO_POSITION", "top_left")  # Not used for overlay, but for future

RESOLUTION = os.getenv('RESOLUTION', '1280x720')
try:
    width, height = map(int, RESOLUTION.lower().split('x'))
except Exception:
    width, height = 1280, 720

VIDEO_ENCODER = 'libx264'  # Hardware encoding disabled, always use software encoder

# Main logo config (always use this path)
MAIN_LOGO_PATH = "/opt/ezrec-backend/assets/ezrec_logo.png"
MAIN_LOGO_POSITION = "bottom_right"  # Always bottom right

# Static logo config - updated to match deployment script paths
STATIC_LOGO_PATH = "/opt/ezrec-backend/assets/ezrec_logo.png"
STATIC_LOGO_POSITION = os.getenv("STATIC_LOGO_POSITION", "bottom_right")
# User asset paths - all assets in single assets folder
USER_LOGO_PATH = "/opt/ezrec-backend/assets/user_logo.png"
INTRO_VIDEO_PATH = "/opt/ezrec-backend/assets/intro.mp4"
SPONSOR_LOGO_1_PATH = "/opt/ezrec-backend/assets/sponsor_logo1.png"
SPONSOR_LOGO_2_PATH = "/opt/ezrec-backend/assets/sponsor_logo2.png"
SPONSOR_LOGO_3_PATH = "/opt/ezrec-backend/assets/sponsor_logo3.png"
SPONSOR_0_POSITION = os.getenv("SPONSOR_0_POSITION", "bottom_left")
SPONSOR_1_POSITION = os.getenv("SPONSOR_1_POSITION", "bottom_right")
SPONSOR_2_POSITION = os.getenv("SPONSOR_2_POSITION", "bottom_center")

LOGO_WIDTH = int(os.getenv('LOGO_WIDTH', '120'))
LOGO_HEIGHT = int(os.getenv('LOGO_HEIGHT', '120'))
# Add these lines for main logo size
MAIN_LOGO_WIDTH = int(os.getenv('MAIN_LOGO_WIDTH', str(LOGO_WIDTH)))
MAIN_LOGO_HEIGHT = int(os.getenv('MAIN_LOGO_HEIGHT', str(LOGO_HEIGHT)))

# Add a simple file validation function that doesn't require FFmpeg
def is_file_readable(file: Path) -> bool:
    """Simple check if file exists and has reasonable size"""
    try:
        if not file.exists():
            return False
        size = file.stat().st_size
        # File should be at least 100KB and not empty
        return size > 100 * 1024
    except Exception:
        return False

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

def s3_signed_url(bucket, key, region, expires=3600):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=region
    )
    return s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expires
    )

def fetch_user_media(user_id: str):
    """
    Fetch intro video, logo, and sponsor logos for the user from user_settings table.
    Returns: (intro_url, logo_url, sponsor_logo_urls)
    """
    try:
        res = supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            # Use correct field names from your table
            intro_path = res.data.get("intro_video_path")
            logo_path = res.data.get("logo_path")
            sponsor1 = res.data.get("sponsor_logo1_path")
            sponsor2 = res.data.get("sponsor_logo2_path")
            sponsor3 = res.data.get("sponsor_logo3_path")
            # Build signed S3 URLs if only key is stored
            bucket = os.getenv("AWS_USER_MEDIA_BUCKET") or os.getenv("AWS_S3_BUCKET")
            region = os.getenv("AWS_REGION", "us-east-1")
            def s3_url(path):
                if not path:
                    return None
                if path.startswith("http"):
                    return path
                # Use signed URL for private S3 object
                return s3_signed_url(bucket, path, region)
            intro_url = s3_url(intro_path)
            logo_url = s3_url(logo_path)
            sponsor_urls = [s3_url(s) for s in [sponsor1, sponsor2, sponsor3] if s]
            return intro_url, logo_url, sponsor_urls
        return None, None, []
    except Exception as e:
        log.error(f"fetch_user_media error: {e}")
        return None, None, []

def download_if_needed(url, path: Path):
    if url and not path.exists():
        try:
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Check file size
                if path.stat().st_size < 1024:  # Arbitrary threshold for a real video/image
                    print(f"Downloaded file {path} is too small, likely corrupt. Deleting.")
                    path.unlink()
            else:
                print(f"Failed to download {url}: HTTP {r.status_code}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            if path.exists():
                path.unlink()
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

    # Check if this is a dual camera recording that needs merging
    if "_merged.mp4" in raw_file.name:
        # This is already a merged file, process normally
        log.info(f"📹 Processing merged dual camera video: {raw_file.name}")
        return process_single_video(raw_file, user_id, date_dir)
    
    # Check if this is a dual camera recording that needs merging
    if "_cam1.mp4" in raw_file.name or "_cam2.mp4" in raw_file.name:
        log.info(f"🎬 Detected dual camera recording: {raw_file.name}")
        return process_dual_camera_video(raw_file, user_id, date_dir)
    
    # Single camera recording - process normally
    log.info(f"📹 Processing single camera video: {raw_file.name}")
    return process_single_video(raw_file, user_id, date_dir)

def process_dual_camera_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    """
    Process dual camera recordings by merging cam1 and cam2 videos side-by-side
    """
    # Extract base filename (e.g., "143022-143322" from "143022-143322_cam1.mp4")
    base_name = raw_file.stem.replace("_cam1", "").replace("_cam2", "")
    
    # Find camera files (support both dual and single camera scenarios)
    cam1_file = date_dir / f"{base_name}_cam1.mp4"
    cam2_file = date_dir / f"{base_name}_cam2.mp4"
    merged_file = date_dir / f"{base_name}_merged.mp4"
    merged_marker = merged_file.with_suffix(".merged")
    merge_error_marker = merged_file.with_suffix(".merge_error")
    
    # Check if we have both camera files
    has_cam1 = cam1_file.exists() and is_file_readable(cam1_file)
    has_cam2 = cam2_file.exists() and is_file_readable(cam2_file)
    
    log.info(f"🔍 Camera file status:")
    log.info(f"   Camera 1: {cam1_file} - {'✅ Available' if has_cam1 else '❌ Missing/Invalid'}")
    log.info(f"   Camera 2: {cam2_file} - {'✅ Available' if has_cam2 else '❌ Missing/Invalid'}")
    
    # Handle single camera scenarios
    if has_cam1 and not has_cam2:
        log.info(f"🔄 Only Camera 1 available. Processing as single camera: {cam1_file}")
        return process_single_video(cam1_file, user_id, date_dir)
    
    if has_cam2 and not has_cam1:
        log.info(f"🔄 Only Camera 2 available. Processing as single camera: {cam2_file}")
        return process_single_video(cam2_file, user_id, date_dir)
    
    if not has_cam1 and not has_cam2:
        log.error(f"❌ No valid camera files found for {base_name}")
        # Create error marker to prevent infinite retries
        error_file = date_dir / f"{base_name}.error"
        error_file.touch()
        return None
    
    log.info(f"🔍 Looking for dual camera files:")
    log.info(f"   Camera 1: {cam1_file}")
    log.info(f"   Camera 2: {cam2_file}")
    log.info(f"   Merged output: {merged_file}")
    
    # At this point, we should have both camera files available
    if not has_cam1 or not has_cam2:
        log.error(f"❌ Camera files validation failed after initial check")
        return None
    
    # Check if merged file already exists
    if merged_file.exists():
        log.info(f"✅ Merged file already exists: {merged_file}")
        if merged_marker.exists():
            log.info(f"✅ .merged marker exists. Proceeding to process merged file.")
            return process_single_video(merged_file, user_id, date_dir)
        elif merge_error_marker.exists():
            log.error(f"❌ Previous merge failed. Skipping.")
            return None
        # If neither marker, treat as legacy and process
        return process_single_video(merged_file, user_id, date_dir)
    
    # --- ENHANCED MERGE LOGIC ---
    log.info(f"🎬 Merging dual camera videos using enhanced_merge.py...")
    try:
        merge_result = merge_videos_with_retry(cam1_file, cam2_file, merged_file, method='side_by_side', max_retries=3)
        if merge_result.success:
            log.info(f"✅ Enhanced merge successful: {merged_file} ({merge_result.file_size:,} bytes)")
            merged_marker.touch()
            return process_single_video(merged_file, user_id, date_dir)
        else:
            log.error(f"❌ Enhanced merge failed: {merge_result.error_message}")
            merge_error_marker.touch()
            return None
    except Exception as e:
        log.error(f"❌ Exception during enhanced merge: {e}")
        merge_error_marker.touch()
        return None

def process_single_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    """
    Process a single video file (either single camera or already merged dual camera)
    """
    output_file = PROCESSED_DIR / date_dir.name / raw_file.name
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Use simplified asset structure - all assets in single folder
    assets_dir = Path("/opt/ezrec-backend/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for downloaded assets in the assets folder with correct names
    intro_path = Path(INTRO_VIDEO_PATH)
    logo_path = Path(USER_LOGO_PATH)
    sponsor_paths = [Path(SPONSOR_LOGO_1_PATH), Path(SPONSOR_LOGO_2_PATH), Path(SPONSOR_LOGO_3_PATH)]
    
    # Also try to fetch from Supabase as fallback if local assets don't exist
    intro_url, logo_url, sponsor_urls = fetch_user_media(user_id)
    if intro_url and not intro_path.exists():
        download_if_needed(intro_url, intro_path)
    if logo_url and not logo_path.exists():
        download_if_needed(logo_url, logo_path)
    for i, sponsor_url in enumerate(sponsor_urls):
        if sponsor_url and not sponsor_paths[i].exists():
            download_if_needed(sponsor_url, sponsor_paths[i])

    # --- Validate intro and logo/sponsor files ---
    def is_valid_video(file: Path):
        try:
            codec, w, h, fps, pix_fmt = get_video_info(file)
            return None not in (codec, w, h, fps, pix_fmt)
        except Exception as e:
            log.warning(f"Video validation failed for {file}: {e}")
            # Try to repair the video file
            try:
                log.info(f"🔧 Attempting to repair corrupted video: {file}")
                backup_path = file.with_suffix('.mp4.backup')
                file.rename(backup_path)
                
                result = subprocess.run([
                    'ffmpeg', '-i', str(backup_path), '-c', 'copy', '-avoid_negative_ts', 'make_zero',
                    str(file)
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and file.exists():
                    log.info(f"✅ Successfully repaired video: {file}")
                    backup_path.unlink()
                    # Try validation again
                    codec, w, h, fps, pix_fmt = get_video_info(file)
                    return None not in (codec, w, h, fps, pix_fmt)
                else:
                    log.error(f"❌ Failed to repair video: {result.stderr}")
                    # Restore original file
                    if backup_path.exists():
                        backup_path.rename(file)
                    return False
            except Exception as repair_error:
                log.error(f"❌ Error during video repair: {repair_error}")
                # Restore original file if backup exists
                backup_path = file.with_suffix('.mp4.backup')
                if backup_path.exists():
                    backup_path.rename(file)
                return False
    
    # Add a simple file validation function that doesn't require FFmpeg
    def is_valid_image(file: Path):
        try:
            from PIL import Image
            with Image.open(file) as img:
                img.verify()
            return True
        except Exception:
            return False

    # Check intro
    if intro_path.exists():
        log.info(f"🔍 Found intro video: {intro_path}")
        log.info(f"📊 Intro video size: {intro_path.stat().st_size} bytes")
        
        # Get video info for debugging
        try:
            codec, w, h, fps, pix_fmt = get_video_info(intro_path)
            log.info(f"📹 Intro video info: codec={codec}, size={w}x{h}, fps={fps}, pix_fmt={pix_fmt}")
        except Exception as e:
            log.error(f"❌ Could not get intro video info: {e}")
        
        if not is_valid_video(intro_path):
            log.error(f"❌ Intro video at {intro_path} is invalid or corrupted. Skipping intro for this video.")
            try:
                intro_path.unlink()
            except Exception:
                pass
            intro_path = None
        else:
            log.info(f"✅ Intro video is valid and ready for concatenation")
    else:
        log.warn(f"⚠️ Intro video not found at {intro_path}")
        intro_path = None

    # Check logo
    if logo_path.exists() and not is_valid_image(logo_path):
        log.error(f"Logo image at {logo_path} is invalid or corrupted. Skipping logo overlay.")
        try:
            logo_path.unlink()
        except Exception:
            pass
        logo_path = None

    # Check sponsor logos
    for i, sponsor_path in enumerate(sponsor_paths):
        if sponsor_path.exists() and not is_valid_image(sponsor_path):
            log.error(f"Sponsor logo {i+1} at {sponsor_path} is invalid or corrupted. Skipping this sponsor overlay.")
            try:
                sponsor_path.unlink()
            except Exception:
                pass
            sponsor_paths[i] = None

    # --- Always add static main logo as overlay input ---
    static_logo_path = Path(STATIC_LOGO_PATH)
    if not static_logo_path.exists():
        log.error(f"Static main logo not found at {STATIC_LOGO_PATH}. Skipping processing.")
        return None
    static_sponsor_paths = [Path(SPONSOR_LOGO_1_PATH), Path(SPONSOR_LOGO_2_PATH), Path(SPONSOR_LOGO_3_PATH)]
    static_sponsor_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]

    # --- Always add main_ezrec_logo.png as overlay input ---
    main_logo_path = Path(MAIN_LOGO_PATH)
    if not main_logo_path.exists():
        log.error(f"Main logo not found at {MAIN_LOGO_PATH}. Skipping processing.")
        return None

    # Sanity check durations
    # max_duration = 600  # 10 minutes in seconds
    raw_duration = get_duration(raw_file)
    # if raw_duration > max_duration:
    #     log.warning(f"Main recording duration too long: {raw_duration:.2f}s. Skipping processing.")
    #     return None
    
    # Check intro duration and trim if needed
    if intro_path and intro_path.exists():
        intro_duration = get_duration(intro_path)
        if intro_duration > 600:
            log.warning(f"Intro video duration too long: {intro_duration:.2f}s. Trimming to 600s.")
            trimmed_intro = intro_path.with_name("intro_trimmed.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(intro_path), "-t", "600", "-c", "copy", str(trimmed_intro)
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
                "-vf", f"scale={width}:{height},fps=30,setsar=1",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-pix_fmt", "yuv420p", str(reencoded_intro)
            ]
            result = subprocess.run(reencode_cmd, capture_output=True)
            if result.returncode != 0:
                log.error(f"Intro re-encode failed: {result.stderr.decode()}")
                return None
            intro_path = reencoded_intro

    # --- Two-pass logic if intro video is present ---
    if intro_path and intro_path.exists():
        sponsor_logo_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]
        # Step 1: Overlay logos on main recording only
        overlay_files = []
        overlay_specs = []
        overlay_positions = []

        # Always add static main logo if present
        if os.path.exists(static_logo_path):
            overlay_files.append(static_logo_path)
            overlay_specs.append({
                'name': 'staticlogo',
                'position': STATIC_LOGO_POSITION,
                'type': 'static_main',
                'no_scale': False,  # <-- Always scale static main logo now
                'width': MAIN_LOGO_WIDTH,
                'height': MAIN_LOGO_HEIGHT
            })
            overlay_positions.append(STATIC_LOGO_POSITION)

        # Add user logo if present
        if logo_path and logo_path.exists():
            overlay_files.append(logo_path)
            overlay_specs.append({
                'name': 'userlogo',
                'position': LOGO_POSITION,
                'type': 'user'
            })
            overlay_positions.append(LOGO_POSITION)

        # Add sponsor logos if present
        for idx, sponsor_logo_path in enumerate(sponsor_paths):
            if sponsor_logo_path and sponsor_logo_path.exists():
                overlay_files.append(sponsor_logo_path)
                overlay_specs.append({
                    'name': f'sponsor{idx}',
                    'position': sponsor_logo_positions[idx],
                    'type': 'sponsor',
                    'idx': idx
                })
                overlay_positions.append(sponsor_logo_positions[idx])

        # Build ffmpeg input args for main recording
        ffmpeg_inputs = ['-i', str(raw_file)]
        for file in overlay_files:
            ffmpeg_inputs += ['-i', str(file)]

        # Build filter chain for overlays (with transparent padding)
        filter_chain = ''
        last_out = '[0:v]'
        for i, spec in enumerate(overlay_specs):
            scaled = f"{spec['name']}_scaled"
            out = f"{spec['name']}_out"
            # Use per-logo width/height if present
            w = spec.get('width', LOGO_WIDTH)
            h = spec.get('height', LOGO_HEIGHT)
            filter_chain += f"[{i+1}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[{scaled}]; "
            pos = spec['position']
            if pos == 'bottom_right':
                x, y = 'main_w-overlay_w-10', 'main_h-overlay_h-10'
            elif pos == 'top_right':
                x, y = 'main_w-overlay_w-10', '10'
            elif pos == 'top_left':
                x, y = '10', '10'
            elif pos == 'bottom_left':
                x, y = '10', 'main_h-overlay_h-10'
            elif pos == 'top_center':
                x, y = '(main_w-overlay_w)/2', '10'
            elif pos == 'bottom_center':
                x, y = '(main_w-overlay_w)/2', 'main_h-overlay_h-10'
            else:
                x, y = '10', '10'  # default
            filter_chain += f"{last_out}[{scaled}]overlay={x}:{y}:format=auto[{out}]; "
            last_out = f'[{out}]'
        # Append setsar=1 to the last output
        filter_chain += f"{last_out}setsar=1[finalout]"
        last_out = '[finalout]'
        filter_chain = filter_chain.strip().rstrip(';')

        # Output path for logo-overlaid main recording
        main_with_logos = raw_file.parent / f"main_with_logos_{raw_file.name}"

        # Run FFmpeg to overlay logos on main recording only
        log.info("[Two-pass] Pass 1: Overlaying logos on main recording only...")
        log.info(f"Overlay filter chain: {filter_chain}")
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            *ffmpeg_inputs,
            '-filter_complex', filter_chain,
            '-map', last_out,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-pix_fmt', 'yuv420p',
            str(main_with_logos)
        ]
        log.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        try:
            start = time.time()
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log.error(f"❌ Logo overlay pass failed with return code: {result.returncode}")
                log.error(f"❌ FFmpeg stderr: {result.stderr}")
                log.error(f"❌ FFmpeg stdout: {result.stdout}")
                return None
            log.info(f"✅ Logo overlay completed in {time.time() - start:.2f}s")
        except Exception as e:
            log.error(f"❌ FFmpeg logo overlay error: {e}")
            return None

        # Step 2: Concat clean intro and logo-overlaid main
        concat_output = raw_file.parent / f"concat_{raw_file.name}"
        # Use simpler concat approach with file list
        concat_list_file = raw_file.parent / "concat_list.txt"
        concat_list_content = f"""file '{intro_path}'
file '{main_with_logos}'"""
        
        with open(concat_list_file, 'w') as f:
            f.write(concat_list_content)
        
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list_file),
            "-c:v", "copy",  # Use copy for faster processing
            str(concat_output)
        ]
        log.info(f"[Two-pass] Pass 2: Concatenating intro and logo-overlaid main video to {concat_output}")
        log.info(f"📹 Intro video: {intro_path}")
        log.info(f"📹 Main video: {main_with_logos}")
        log.info(f"📹 Output: {concat_output}")
        
        try:
            start = time.time()
            log.info(f"🎬 Starting concat process...")
            log.info(f"📋 Concat command: {' '.join(concat_cmd)}")
            
            # Check if input files exist
            if not intro_path.exists():
                log.error(f"❌ Intro video does not exist: {intro_path}")
                return None
            if not main_with_logos.exists():
                log.error(f"❌ Main video does not exist: {main_with_logos}")
                return None
                
            log.info(f"✅ Both input files exist, starting FFmpeg...")
            
            # Check video compatibility before concat
            try:
                intro_info = get_video_info(intro_path)
                main_info = get_video_info(main_with_logos)
                log.info(f"📹 Intro video: codec={intro_info[0]}, size={intro_info[1]}x{intro_info[2]}, fps={intro_info[3]}")
                log.info(f"📹 Main video: codec={main_info[0]}, size={main_info[1]}x{main_info[2]}, fps={main_info[3]}")
                
                # Check if videos are compatible for concat
                if intro_info[0] != main_info[0]:
                    log.warn(f"⚠️ Video codecs don't match: intro={intro_info[0]}, main={main_info[0]}")
                    log.warn(f"⚠️ Using fallback: main video without intro")
                    output_file = PROCESSED_DIR / date_dir.name / raw_file.name
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(main_with_logos), str(output_file))
                    if concat_list_file.exists():
                        concat_list_file.unlink()
                    return output_file
                    
            except Exception as e:
                log.error(f"❌ Error checking video compatibility: {e}")
                # Continue with concat anyway
            
            # Add progress monitoring with timeout
            log.info(f"⏱️ Starting FFmpeg with progress monitoring...")
            
            # Use Popen to monitor progress
            process = subprocess.Popen(
                concat_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor progress for up to 10 minutes
            start_time = time.time()
            timeout = 600  # 10 minutes
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    log.error(f"❌ FFmpeg concat process timed out after {timeout} seconds")
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return None
                
                # Log progress every 30 seconds
                if int(elapsed) % 30 == 0 and elapsed > 0:
                    log.info(f"⏱️ FFmpeg concat still running... ({elapsed:.0f}s elapsed)")
                
                time.sleep(1)
            
            # Get the result
            stdout, stderr = process.communicate()
            result = subprocess.CompletedProcess(
                concat_cmd, 
                process.returncode, 
                stdout, 
                stderr
            )
            
            if result.returncode != 0:
                log.error(f"❌ Concat pass failed with return code: {result.returncode}")
                log.error(f"❌ FFmpeg stderr: {result.stderr}")
                log.error(f"❌ FFmpeg stdout: {result.stdout}")
                
                # Try fallback: use main video without intro
                log.warn(f"⚠️ Trying fallback: using main video without intro")
                output_file = PROCESSED_DIR / date_dir.name / raw_file.name
                output_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(main_with_logos), str(output_file))
                
                # Clean up temp file
                if main_with_logos.exists():
                    main_with_logos.unlink()
                    
                log.info(f"✅ Fallback successful: created video without intro")
                return output_file
                
            log.info(f"✅ Concat completed in {time.time() - start:.2f}s")
        except Exception as e:
            log.error(f"❌ Concat process exception: {str(e)}")
            return None

        # Final output is concat_output
        output_file = PROCESSED_DIR / date_dir.name / raw_file.name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(concat_output), str(output_file))
        # Clean up temp files
        if main_with_logos.exists():
            main_with_logos.unlink()
        if concat_list_file.exists():
            concat_list_file.unlink()
        return output_file
    # --- Single-pass logic if no intro video ---
    input_args = ["-i", str(raw_file), "-i", str(static_logo_path)]
    main_video_idx = 0
    video_inputs = 1
    # For static main logo, do not scale, just overlay at original size
    filter_parts = [f"[{main_video_idx}:v][1:v]overlay={POSITION_MAP[STATIC_LOGO_POSITION]}:format=auto[staticlogo_out]"]
    last_output = "[staticlogo_out]"
    
    # Use downloaded user assets with correct paths
    logo_inputs = []
    if logo_path and logo_path.exists():
        input_args.extend(["-i", str(logo_path)])
        logo_inputs.append(("userlogo", video_inputs + len(logo_inputs) + 1, LOGO_POSITION))
    
    sponsor_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]
    for i, sponsor_path in enumerate(sponsor_paths):
        if sponsor_path and sponsor_path.exists():
            input_args.extend(["-i", str(sponsor_path)])
            logo_inputs.append((f"sponsor{i}", video_inputs + len(logo_inputs) + 1, sponsor_positions[i]))
    
    # LOGGING: Print overlays and positions AFTER logo_inputs is built
    log.info("--- Overlay Chain (Single-pass, actual overlays to be applied) ---")
    log.info(f"Static main logo: {static_logo_path} at {STATIC_LOGO_POSITION}")
    for name, idx, position in logo_inputs:
        log.info(f"Overlay: {name} (input idx {idx}) at {position}")
    log.info("------------------------------")
    # Build filter chain for user assets
    for name, idx, position in logo_inputs:
        scale_filter = f"[{idx}:v]scale={LOGO_WIDTH}:{LOGO_HEIGHT}:force_original_aspect_ratio=decrease,pad={LOGO_WIDTH}:{LOGO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[{name}_scaled]"
        filter_parts.append(scale_filter)
        overlay_position = POSITION_MAP.get(position, "bottom_right")
        overlay_filter = f"{last_output}[{name}_scaled]overlay={overlay_position}:format=auto[{name}_out]"
        filter_parts.append(overlay_filter)
        last_output = f"[{name}_out]"
    
    ffmpeg_base_cmd = ["ffmpeg", "-y"] + input_args
    if filter_parts:
        filter_complex = ";".join(filter_parts)
        ffmpeg_base_cmd.extend(["-filter_complex", filter_complex, "-map", last_output])
    else:
        ffmpeg_base_cmd.extend(["-map", f"{main_video_idx}:v"])
        ffmpeg_base_cmd.extend(["-vf", f"scale={width}:{height}"])
    ffmpeg_base_cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p", str(output_file)]
    log.info(f"Using video encoder: {VIDEO_ENCODER}")
    log.info(f"FFmpeg command: {' '.join(ffmpeg_base_cmd)}")
    try:
        start_time = time.time()
        result = subprocess.run(ffmpeg_base_cmd, check=True, capture_output=True, text=True)
        end_time = time.time()
        processing_time = end_time - start_time
        log.info(f"\u2705 Video processing completed in {processing_time:.1f}s using {VIDEO_ENCODER}")
        if output_file.exists() and output_file.stat().st_size > 1024:
            return output_file
        else:
            log.error("Output file missing or too small")
            return None
    except subprocess.CalledProcessError as e:
        log.error(f"❌ FFmpeg failed with {VIDEO_ENCODER}: {e.stderr}")
        log.error(f"❌ FFmpeg error: {e.stderr}")
    except Exception as e:
        log.error(f"❌ FFmpeg error: {e}")
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

def check_disk_space():
    """Check available disk space and return percentage used"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/opt/ezrec-backend")
        used_percent = (used / total) * 100
        return used_percent, free
    except Exception as e:
        log.error(f"Error checking disk space: {e}")
        return 0, 0

def cleanup_old_files():
    """Clean up old recordings and processed files to free disk space"""
    try:
        # Check disk space first
        used_percent, free_space = check_disk_space()
        log.info(f"📊 Disk usage: {used_percent:.1f}% used, {free_space / (1024**3):.1f} GB free")
        
        # Only cleanup if disk usage is above 80%
        if used_percent < 80:
            return
        
        log.warning(f"⚠️ Disk usage high ({used_percent:.1f}%). Starting cleanup...")
        
        # Clean up old recordings (keep last 7 days)
        recordings_dir = Path("/opt/ezrec-backend/recordings")
        if recordings_dir.exists():
            import datetime
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)
            
            for date_dir in recordings_dir.glob("*"):
                if date_dir.is_dir():
                    try:
                        dir_date = datetime.datetime.strptime(date_dir.name, "%Y-%m-%d")
                        if dir_date < cutoff_date:
                            log.info(f"🗑️ Removing old recordings directory: {date_dir}")
                            shutil.rmtree(date_dir)
                    except ValueError:
                        # Skip non-date directories
                        continue
        
        # Clean up old processed videos (keep last 3 days)
        processed_dir = Path("/opt/ezrec-backend/processed")
        if processed_dir.exists():
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=3)
            
            for date_dir in processed_dir.glob("*"):
                if date_dir.is_dir():
                    try:
                        dir_date = datetime.datetime.strptime(date_dir.name, "%Y-%m-%d")
                        if dir_date < cutoff_date:
                            log.info(f"🗑️ Removing old processed directory: {date_dir}")
                            shutil.rmtree(date_dir)
                    except ValueError:
                        # Skip non-date directories
                        continue
        
        # Clean up old log files (keep last 30 days)
        logs_dir = Path("/opt/ezrec-backend/logs")
        if logs_dir.exists():
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
            
            for log_file in logs_dir.glob("*.log"):
                try:
                    file_time = datetime.datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        log.info(f"🗑️ Removing old log file: {log_file}")
                        log_file.unlink()
                except Exception:
                    continue
        
        log.info("✅ Cleanup completed")
        
    except Exception as e:
        log.error(f"❌ Error during cleanup: {e}")

def is_valid_video(file: Path):
    """Validate video file using FFmpeg"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1",
            str(file)
        ], capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and result.stdout.strip()
    except Exception as e:
        log.error(f"Video validation failed for {file}: {e}")
        return False

def cleanup_orphaned_markers():
    """Clean up orphaned marker files at startup"""
    log.info("🧹 Running startup cleanup of orphaned marker files...")
    cleaned_count = 0
    
    for date_dir in RECORDINGS_DIR.glob("*/"):
        for marker_file in date_dir.glob("*.done"):
            base_path = str(marker_file).replace(".done", "")
            mp4_file = Path(base_path + ".mp4")
            
            if not mp4_file.exists():
                log.warning(f"🚫 Startup cleanup: Found orphaned .done marker: {marker_file.name}")
                
                # Try to extract booking ID and update Supabase status
                try:
                    booking_id = extract_booking_id_from_filename(marker_file.name)
                    update_supabase_status(booking_id, "SkippedMissingFile")
                except Exception as e:
                    log.warning(f"⚠️ Could not update Supabase status for {marker_file.name}: {e}")
                
                # Clean up all related marker files
                for ext in [".done", ".meta", ".lock", ".error", ".completed"]:
                    stale_marker = Path(base_path + ext)
                    if stale_marker.exists():
                        stale_marker.unlink()
                        log.info(f"🧹 Startup cleanup: Removed {stale_marker.name}")
                        cleaned_count += 1
    
    if cleaned_count > 0:
        log.info(f"✅ Startup cleanup completed: removed {cleaned_count} orphaned marker files")
    else:
        log.info("✅ Startup cleanup: no orphaned marker files found")

def main():
    log.info("Video worker started and entering main loop")
    
    # Run startup cleanup
    cleanup_orphaned_markers()
    
    while True:
        retry_pending_uploads()
        cleanup_old_files() # Run cleanup at the start of each interval
        for date_dir in RECORDINGS_DIR.glob("*/"):
            try:
                log.info(f"Scanning directory: {date_dir}")
                
                # First, clean up orphaned marker files (markers without .mp4 files)
                for marker_file in date_dir.glob("*.done"):
                    try:
                        base_path = str(marker_file).replace(".done", "")
                        mp4_file = Path(base_path + ".mp4")
                        
                        if not mp4_file.exists():
                            log.warning(f"🚫 Found orphaned .done marker: {marker_file.name} (no matching .mp4 file)")
                            
                            # Try to extract booking ID and update Supabase status
                            try:
                                booking_id = extract_booking_id_from_filename(marker_file.name)
                                update_supabase_status(booking_id, "SkippedMissingFile")
                            except Exception as e:
                                log.warning(f"⚠️ Could not update Supabase status for {marker_file.name}: {e}")
                            
                            # Clean up all related marker files
                            for ext in [".done", ".meta", ".lock", ".error", ".completed", ".merge_error"]:
                                stale_marker = Path(base_path + ext)
                                if stale_marker.exists():
                                    stale_marker.unlink()
                                    log.info(f"🧹 Removed stale marker file: {stale_marker.name}")
                            
                            continue
                    except Exception as e:
                        log.error(f"❌ Error processing orphaned marker {marker_file.name}: {e}")
                        continue
                
                # Now process valid .mp4 files
                for raw_file in date_dir.glob("*.mp4"):
                    try:
                        done = raw_file.with_suffix(".done")
                        completed = raw_file.with_suffix(".completed")
                        lock = raw_file.with_suffix(".lock")
                        error = raw_file.with_suffix(".error")
                        meta_path = raw_file.with_suffix(".json")
                        log.info(f"Checking {raw_file.name}: done={done.exists()}, completed={completed.exists()}, lock={lock.exists()}, error={error.exists()}, meta={meta_path.exists()}")
                        if not done.exists() or completed.exists() or lock.exists() or error.exists():
                            continue
                        
                        # Acquire file lock to prevent race conditions
                        if not acquire_file_lock(lock, timeout=30):
                            log.warning(f"⚠️ Could not acquire lock for {raw_file.name}, skipping")
                            continue
                        
                        try:
                            # First do a simple file check
                            if not is_file_readable(raw_file):
                                log.error(f"❌ Video file {raw_file.name} is not readable or too small. Skipping.")
                                completed.touch()
                                continue
                            
                            # Try to validate the video file with FFmpeg
                            if not is_valid_video(raw_file):
                                log.error(f"❌ Video file {raw_file.name} is corrupted and cannot be processed. Skipping.")
                                # Create a .completed file to prevent infinite loops
                                completed.touch()
                                continue
                        except Exception as e:
                            log.error(f"❌ Error validating video {raw_file.name}: {e}")
                            # Create a .completed file to prevent infinite loops
                            completed.touch()
                            continue
                        
                        if not meta_path.exists():
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
                                    "recording_id": raw_file.stem,  # Ensure this is always set
                                    "duration_seconds": int(get_duration(raw_file)),
                                    "uploaded_at": None,
                                    "filename": final_file.name,
                                    "storage_path": s3_key,
                                    "booking_id": booking_id  # Include booking_id
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
                                            log.error(f"❌ Error updating booking status: {e}")
                                    else:
                                        log.error(f"❌ Failed to insert video metadata for {raw_file.name}")
                                else:
                                    log.warning(f"⚠️ No internet connection, adding to pending uploads: {raw_file.name}")
                                    add_pending_upload(final_file, s3_key, meta)
                            else:
                                log.error(f"❌ Failed to process video {raw_file.name}")
                        except Exception as e:
                            log.error(f"❌ Error processing video {raw_file.name}: {e}")
                        finally:
                            # Always release the lock
                            release_file_lock(lock)
                    except Exception as e:
                        log.error(f"❌ Error in video processing loop for {raw_file.name}: {e}")
                        continue
            except Exception as e:
                log.error(f"❌ Error processing directory {date_dir}: {e}")
                continue
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
