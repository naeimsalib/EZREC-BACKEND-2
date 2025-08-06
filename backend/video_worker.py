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

try:
    from booking_utils import update_booking_status
except ImportError:
    def update_booking_status(booking_id: str, status: str) -> bool:
        """Fallback function if booking_utils is not available"""
        log.warning(f"⚠️ update_booking_status not available for booking {booking_id}")
        return False

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
# Setup logging FIRST before any other operations
LOG_FILE = "/opt/ezrec-backend/logs/video_worker.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger("video_worker")

for var in required_env_vars:
    if not os.getenv(var):
        raise RuntimeError(f"Missing env: {var}")

# Initialize Supabase client with proper error handling
try:
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )
    log.info("✅ Supabase client initialized successfully")
except Exception as e:
    log.warning(f"⚠️ Failed to initialize Supabase client: {e}")
    log.warning("⚠️ System will work in local mode only")
    supabase = None

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
    handlers=[
        logging.FileHandler(LOG_FILE), 
        logging.StreamHandler()
    ]
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

# Logo configuration - all from environment variables
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

# Logo paths from environment variables
MAIN_LOGO_PATH = os.getenv("MAIN_LOGO_PATH", "/opt/ezrec-backend/assets/ezrec_logo.png")
USER_LOGO_PATH = os.getenv("USER_LOGO_PATH", "/opt/ezrec-backend/assets/user_logo.png")
SPONSOR_LOGO_1_PATH = os.getenv("SPONSOR_LOGO_1_PATH", "/opt/ezrec-backend/assets/sponsor_logo1.png")
SPONSOR_LOGO_2_PATH = os.getenv("SPONSOR_LOGO_2_PATH", "/opt/ezrec-backend/assets/sponsor_logo2.png")
SPONSOR_LOGO_3_PATH = os.getenv("SPONSOR_LOGO_3_PATH", "/opt/ezrec-backend/assets/sponsor_logo3.png")

# Logo positions from environment variables
MAIN_LOGO_POSITION = os.getenv("MAIN_LOGO_POSITION", "bottom_right")  # Always bottom right
USER_LOGO_POSITION = os.getenv("USER_LOGO_POSITION", "top_right")
SPONSOR_1_POSITION = os.getenv("SPONSOR_1_POSITION", "bottom_left")
SPONSOR_2_POSITION = os.getenv("SPONSOR_2_POSITION", "bottom_center")
SPONSOR_3_POSITION = os.getenv("SPONSOR_3_POSITION", "top_left")

# Logo sizes from environment variables
LOGO_WIDTH = int(os.getenv('LOGO_WIDTH', '120'))
LOGO_HEIGHT = int(os.getenv('LOGO_HEIGHT', '120'))
MAIN_LOGO_WIDTH = int(os.getenv('MAIN_LOGO_WIDTH', '400'))
MAIN_LOGO_HEIGHT = int(os.getenv('MAIN_LOGO_HEIGHT', '400'))
USER_LOGO_WIDTH = int(os.getenv('USER_LOGO_WIDTH', '120'))
USER_LOGO_HEIGHT = int(os.getenv('USER_LOGO_HEIGHT', '120'))
SPONSOR_LOGO_WIDTH = int(os.getenv('SPONSOR_LOGO_WIDTH', '120'))
SPONSOR_LOGO_HEIGHT = int(os.getenv('SPONSOR_LOGO_HEIGHT', '120'))

# Intro video path
INTRO_VIDEO_PATH = os.getenv("INTRO_VIDEO_PATH", "/opt/ezrec-backend/assets/intro.mp4")

# Static logo config
STATIC_LOGO_PATH = "/opt/ezrec-backend/main_ezrec_logo.png"
STATIC_LOGO_POSITION = os.getenv("STATIC_LOGO_POSITION", "bottom_right")
STATIC_SPONSOR_0_PATH = "/opt/ezrec-backend/static/sponsor_logo_1.png"
STATIC_SPONSOR_1_PATH = "/opt/ezrec-backend/static/sponsor_logo_2.png"
STATIC_SPONSOR_2_PATH = "/opt/ezrec-backend/static/sponsor_logo_3.png"
STATIC_SPONSOR_0_POSITION = os.getenv("STATIC_SPONSOR_0_POSITION", "top_right")
STATIC_SPONSOR_1_POSITION = os.getenv("STATIC_SPONSOR_1_POSITION", "bottom_center")
STATIC_SPONSOR_2_POSITION = os.getenv("STATIC_SPONSOR_2_POSITION", "bottom_right")

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

        ], capture_output=True, text=True, timeout=30)
        info = _json.loads(result.stdout)
        stream = info['streams'][0]
        codec = stream.get('codec_name')
        width = int(stream.get('width'))
        height = int(stream.get('height'))
        pix_fmt = stream.get('pix_fmt')
        
        if result.returncode != 0:
            log.error(f"❌ FFprobe failed for {file}: {result.stderr}")
            return None
            
        info = _json.loads(result.stdout)
        if not info.get('streams') or len(info['streams']) == 0:
            log.error(f"❌ No video streams found in {file}")
            return None
            
        stream = info['streams'][0]
        codec = stream.get('codec_name')
        width = stream.get('width')
        height = stream.get('height')
        pix_fmt = stream.get('pix_fmt')
        
        # Validate required fields
        if not all([codec, width, height, pix_fmt]):
            log.error(f"❌ Missing required video info for {file}: codec={codec}, width={width}, height={height}, pix_fmt={pix_fmt}")
            return None
            
        # Convert to integers
        try:
            width = int(width)
            height = int(height)
        except (ValueError, TypeError):
            log.error(f"❌ Invalid width/height for {file}: width={width}, height={height}")
            return None
        

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

            
        return (codec, width, height, fps, pix_fmt)
    except subprocess.TimeoutExpired:
        log.error(f"❌ FFprobe timeout for {file}")
        return None
    except Exception as e:
        log.error(f"❌ Could not get video info for {file}: {e}")
        return None


def process_video(raw_file: Path, user_id: str, date_dir: Path) -> Path:
    """
    Optimized video processing with hardware acceleration and single-pass operation.

    Ensures compatibility with OpenCV-generated MP4 files.


    Tries multiple encoders in order: h264_v4l2m2m, h264_omx, libx264.
    Logs full FFmpeg error output for each attempt.
    """
    output_file = PROCESSED_DIR / date_dir.name / raw_file.name
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # --- Validate input video format for OpenCV compatibility ---
    log.info(f"🔍 Validating input video format: {raw_file}")
    codec, width, height, fps, pix_fmt = get_video_info(raw_file)
    
    if codec is None:
        log.error(f"❌ Could not read video info from {raw_file}")
        return None
    
    log.info(f"📹 Input video: {codec} {width}x{height} @ {fps:.1f}fps, {pix_fmt}")
    
    # Check if video needs format conversion for FFmpeg compatibility
    needs_conversion = False
    if codec != 'h264':
        log.warning(f"⚠️ Video codec {codec} may not be optimal for processing")
        needs_conversion = True
    if pix_fmt != 'yuv420p':
        log.warning(f"⚠️ Pixel format {pix_fmt} may cause compatibility issues")
        needs_conversion = True
    
    # Convert if needed
    if needs_conversion:
        log.info("🔄 Converting video to H.264 yuv420p for optimal compatibility...")
        converted_file = raw_file.parent / f"converted_{raw_file.name}"
        convert_cmd = [
            "ffmpeg", "-y", "-i", str(raw_file),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", str(converted_file)
        ]
        try:
            result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                log.error(f"❌ Video conversion failed: {result.stderr}")
                return None
            log.info("✅ Video conversion completed")
            raw_file = converted_file
        except subprocess.TimeoutExpired:
            log.error("❌ Video conversion timed out")
            return None
        except Exception as e:
            log.error(f"❌ Video conversion error: {e}")
            return None


    # Use local cache for user media
    user_media_dir = MEDIA_CACHE_DIR / user_id
    user_media_dir.mkdir(parents=True, exist_ok=True)
    # --- Always fetch latest user media from Supabase and download if needed ---
    intro_url, logo_url, sponsor_urls = fetch_user_media(user_id)
    intro_path = user_media_dir / "intro.mp4"
    logo_path = user_media_dir / "logo.png"
    sponsor_paths = [user_media_dir / f"sponsor_logo{i+1}.png" for i in range(3)]
    # Download intro
    if intro_url:
        download_if_needed(intro_url, intro_path)
    # Download logo
    if logo_url:
        download_if_needed(logo_url, logo_path)
    # Download sponsors
    for i, sponsor_url in enumerate(sponsor_urls):
        if sponsor_url:
            download_if_needed(sponsor_url, sponsor_paths[i])

    # --- Validate intro and logo/sponsor files ---
    def is_valid_video(file: Path):
        codec, w, h, fps, pix_fmt = get_video_info(file)
        return None not in (codec, w, h, fps, pix_fmt)
    def is_valid_image(file: Path):
        try:
            from PIL import Image
            with Image.open(file) as img:
                img.verify()
            return True
        except Exception:
            return False

    # Check intro
    if intro_path.exists() and not is_valid_video(intro_path):
        log.error(f"Intro video at {intro_path} is invalid or corrupted. Skipping intro for this video.")
        try:
            intro_path.unlink()
        except Exception:
            pass
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
    static_sponsor_paths = [Path(STATIC_SPONSOR_0_PATH), Path(STATIC_SPONSOR_1_PATH), Path(STATIC_SPONSOR_2_PATH)]
    static_sponsor_positions = [STATIC_SPONSOR_0_POSITION, STATIC_SPONSOR_1_POSITION, STATIC_SPONSOR_2_POSITION]

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
                'main_logo': True  # <-- Mark this as main logo to use different sizing
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
            # Use main logo sizing for main logo, regular sizing for others
            if spec.get('main_logo'):
                filter_chain += f"[{i+1}:v]scale={MAIN_LOGO_WIDTH}:{MAIN_LOGO_HEIGHT}:force_original_aspect_ratio=decrease,pad={MAIN_LOGO_WIDTH}:{MAIN_LOGO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[{scaled}]; "
            else:
                filter_chain += f"[{i+1}:v]scale={LOGO_WIDTH}:{LOGO_HEIGHT}:force_original_aspect_ratio=decrease,pad={LOGO_WIDTH}:{LOGO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[{scaled}]; "
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
            result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=600)
            if result.returncode != 0:
                log.error(f"Logo overlay pass failed: {result.stderr.decode()}")
                return None
            log.info(f"✅ Logo overlay completed in {time.time() - start:.2f}s")
        except subprocess.TimeoutExpired:
            log.error("❌ FFmpeg logo overlay step timed out.")
            return None
        except Exception as e:
            log.error(f"❌ FFmpeg logo overlay error: {e}")
            return None

        # Step 2: Concat clean intro and logo-overlaid main
        concat_output = raw_file.parent / f"concat_{raw_file.name}"
        concat_cmd = [
            "ffmpeg", "-y", "-threads", "2",
            "-i", str(intro_path), "-i", str(main_with_logos),
            "-filter_complex",
            f"[0:v]scale={width}:{height},format=yuv420p[intro];"
            f"[1:v]scale={width}:{height},format=yuv420p[main];"
            f"[intro][main]concat=n=2:v=1:a=0[concat]",
            "-map", "[concat]",
            "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", str(concat_output)
        ]
        log.info(f"[Two-pass] Pass 2: Concatenating intro and logo-overlaid main video to {concat_output}")
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

        # Final output is concat_output
        output_file = PROCESSED_DIR / date_dir.name / raw_file.name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(concat_output), str(output_file))
        # Clean up temp file
        if main_with_logos.exists():
            main_with_logos.unlink()
        return output_file
    # --- Single-pass logic if no intro video ---
    input_args = ["-i", str(raw_file), "-i", str(static_logo_path)]
    main_video_idx = 0
    video_inputs = 1
    # For static main logo, scale to main logo size
    filter_parts = [f"[1:v]scale={MAIN_LOGO_WIDTH}:{MAIN_LOGO_HEIGHT}:force_original_aspect_ratio=decrease,pad={MAIN_LOGO_WIDTH}:{MAIN_LOGO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x00000000[staticlogo_scaled]"]
    filter_parts.append(f"[{main_video_idx}:v][staticlogo_scaled]overlay={POSITION_MAP[STATIC_LOGO_POSITION]}:format=auto[staticlogo_out]")
    last_output = "[staticlogo_out]"
    static_logo_inputs = []
    for i, static_sponsor_path in enumerate(static_sponsor_paths):
        if static_sponsor_path.exists():
            input_args.extend(["-i", str(static_sponsor_path)])
            static_logo_inputs.append((f"staticsponsor{i}", video_inputs + len(static_logo_inputs) + 1, static_sponsor_positions[i]))
    for name, idx, position in static_logo_inputs:
        scale_filter = f"[{idx}:v]scale=iw*0.15:ih*0.15[{name}_scaled]"
        filter_parts.append(scale_filter)
        overlay_position = POSITION_MAP.get(position, "top_right")
        overlay_filter = f"{last_output}[{name}_scaled]overlay={overlay_position}:format=auto[{name}_out]"
        filter_parts.append(overlay_filter)
        last_output = f"[{name}_out]"
    logo_inputs = []
    if logo_path and logo_path.exists():
        input_args.extend(["-i", str(logo_path)])
        logo_inputs.append(("logo", video_inputs + len(static_logo_inputs) + 1, LOGO_POSITION))
    sponsor_positions = [SPONSOR_0_POSITION, SPONSOR_1_POSITION, SPONSOR_2_POSITION]
    for i, sponsor_path in enumerate(sponsor_paths):
        if sponsor_path and sponsor_path.exists():
            input_args.extend(["-i", str(sponsor_path)])
            logo_inputs.append((f"sponsor{i}", video_inputs + len(static_logo_inputs) + len(logo_inputs) + 1, sponsor_positions[i]))
    # LOGGING: Print overlays and positions AFTER logo_inputs is built
    log.info("--- Overlay Chain (Single-pass, actual overlays to be applied) ---")
    log.info(f"Static main logo: {static_logo_path} at {STATIC_LOGO_POSITION}")
    for i, static_sponsor_path in enumerate(static_sponsor_paths):
        if static_sponsor_path.exists():
            log.info(f"Static sponsor {i}: {static_sponsor_path} at {static_sponsor_positions[i]}")
    for name, idx, position in logo_inputs:
        log.info(f"Overlay: {name} (input idx {idx}) at {position}")
    log.info("------------------------------")
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
        log.error(f"FFmpeg error: {e.stderr}")
    except subprocess.TimeoutExpired:
        log.error(f"FFmpeg processing timed out after 30 minutes")
    except Exception as e:
        log.error(f"FFmpeg error: {e}")
    log.error("FFmpeg processing failed. Video not processed.")
    return None

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
    try:
        # Validate input file
        if not raw_file.exists():
            log.error(f"❌ Input file does not exist: {raw_file}")
            return None
            
        if not is_file_readable(raw_file):
            log.error(f"❌ Input file is not readable: {raw_file}")
            return None
            
        # Check file size
        file_size = raw_file.stat().st_size
        if file_size == 0:
            log.error(f"❌ Input file is empty: {raw_file}")
            return None
            
        log.info(f"📹 Processing video: {raw_file.name} ({file_size:,} bytes)")
        
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
                video_info = get_video_info(file)
                if video_info is None:
                    return False
                codec, w, h, fps, pix_fmt = video_info
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
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and file.exists():
                        log.info(f"✅ Successfully repaired video: {file}")
                        backup_path.unlink()
                        # Try validation again
                        video_info = get_video_info(file)
                        if video_info is None:
                            return False
                        codec, w, h, fps, pix_fmt = video_info
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
                video_info = get_video_info(intro_path)
                if video_info is not None:
                    codec, w, h, fps, pix_fmt = video_info
                    log.info(f"📹 Intro video info: codec={codec}, size={w}x{h}, fps={fps}, pix_fmt={pix_fmt}")
                else:
                    log.error(f"❌ Could not get intro video info")
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
        if logo_path.exists():
            log.info(f"🔍 Found user logo: {logo_path}")
            if not is_valid_image(logo_path):
                log.error(f"❌ User logo at {logo_path} is invalid. Skipping logo overlay.")
                logo_path = None
            else:
                log.info(f"✅ User logo is valid")
        else:
            log.warn(f"⚠️ User logo not found at {logo_path}")
            logo_path = None

        # Check sponsor logos
        valid_sponsor_paths = []
        for i, sponsor_path in enumerate(sponsor_paths):
            if sponsor_path.exists():
                log.info(f"🔍 Found sponsor logo {i+1}: {sponsor_path}")
                if not is_valid_image(sponsor_path):
                    log.error(f"❌ Sponsor logo {i+1} at {sponsor_path} is invalid. Skipping.")
                else:
                    log.info(f"✅ Sponsor logo {i+1} is valid")
                    valid_sponsor_paths.append(sponsor_path)
            else:
                log.warn(f"⚠️ Sponsor logo {i+1} not found at {sponsor_path}")

        # --- PROCESSING LOGIC ---
        # If we have an intro video, use the two-pass approach
        if intro_path and intro_path.exists():
            log.info(f"🎬 Using two-pass approach with intro video")
            
            # Build overlay specifications
            overlay_specs = []
            if logo_path:
                overlay_specs.append({
                    'name': 'user_logo',
                    'path': logo_path,
                    'position': 'bottom_right',
                    'width': LOGO_WIDTH,
                    'height': LOGO_HEIGHT
                })
            
            # Add sponsor logos
            for i, sponsor_path in enumerate(valid_sponsor_paths):
                overlay_specs.append({
                    'name': f'sponsor{i+1}',
                    'path': sponsor_path,
                    'position': ['bottom_left', 'bottom_right', 'bottom_center'][i % 3],
                    'width': LOGO_WIDTH,
                    'height': LOGO_HEIGHT
                })
            
            # Build filter chain for logo overlays
            filter_chain = ""
            ffmpeg_inputs = ['-i', str(raw_file)]
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

            # Step 1: Re-encode the original merged video to fix DTS timestamp issues BEFORE logo overlay
            log.info(f"🔧 Re-encoding original merged video to fix DTS timestamp issues...")
            merged_reencoded = raw_file.parent / f"reencoded_{raw_file.name}"
            
            reencode_cmd = [
                'ffmpeg', '-y',
                '-i', str(raw_file),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(merged_reencoded)
            ]
            
            log.info(f"🎬 Re-encode command: {' '.join(reencode_cmd)}")
            
            # Run re-encode with timeout
            try:
                reencode_process = subprocess.Popen(
                    reencode_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                reencode_start_time = time.time()
                reencode_timeout = 300  # 5 minutes timeout
                
                while reencode_process.poll() is None:
                    if time.time() - reencode_start_time > reencode_timeout:
                        log.error(f"❌ Re-encode timed out after {reencode_timeout}s")
                        reencode_process.terminate()
                        raise Exception(f"Re-encode timed out after {reencode_timeout}s")
                    time.sleep(1)
                
                reencode_stdout, reencode_stderr = reencode_process.communicate()
                
                if reencode_process.returncode == 0:
                    log.info(f"✅ Re-encode completed successfully in {time.time() - reencode_start_time:.2f}s")
                else:
                    log.error(f"❌ Re-encode failed with return code {reencode_process.returncode}")
                    log.error(f"❌ Re-encode stderr: {reencode_stderr}")
                    raise Exception(f"Re-encode failed: {reencode_stderr}")
            except Exception as e:
                log.error(f"❌ Re-encode error: {e}")
                return None
            
            # Use the re-encoded video for logo overlay
            video_for_logos = merged_reencoded if merged_reencoded.exists() else raw_file
            
            # Step 2: Overlay logos on the re-encoded video with improved quality
            log.info(f"🎨 Adding logo overlays with improved quality...")
            
            # Get video dimensions for overlay positioning
            video_info = get_video_info(video_for_logos)
            if video_info is None:
                log.error(f"❌ Could not get video info for {video_for_logos}")
                return None
            
            codec, width, height, fps, pix_fmt = video_info
            log.info(f"📹 Video dimensions: {width}x{height}")
            
            # Build overlay filter chain
            overlay_filters = []
            input_count = 1  # Start with 1 input (the video)
            
            # Add logo inputs and build filter chain
            logo_files = []
            if (assets_dir / "ezrec_logo.png").exists():
                logo_files.append(str(assets_dir / "ezrec_logo.png"))
            if (assets_dir / "user_logo.png").exists():
                logo_files.append(str(assets_dir / "user_logo.png"))
            if (assets_dir / "sponsor_logo1.png").exists():
                logo_files.append(str(assets_dir / "sponsor_logo1.png"))
            if (assets_dir / "sponsor_logo2.png").exists():
                logo_files.append(str(assets_dir / "sponsor_logo2.png"))
            if (assets_dir / "sponsor_logo3.png").exists():
                logo_files.append(str(assets_dir / "sponsor_logo3.png"))
            
            # Build filter chain for logo overlays
            filter_chain = ""
            ffmpeg_inputs = ['-i', str(video_for_logos)]
            last_out = '[0:v]'
            
            for i, logo_file in enumerate(logo_files):
                scaled = f"logo{i}_scaled"
                out = f"logo{i}_out"
                filter_chain += f"[{i+1}:v]scale=200:200:force_original_aspect_ratio=decrease,pad=200:200:(ow-iw)/2:(oh-ih)/2:color=0x00000000[{scaled}]; "
                
                # Position logos in different corners
                positions = [
                    ('main_w-overlay_w-10', 'main_h-overlay_h-10'),  # bottom right
                    ('10', 'main_h-overlay_h-10'),                   # bottom left
                    ('10', '10'),                                    # top left
                    ('main_w-overlay_w-10', '10'),                   # top right
                    ('(main_w-overlay_w)/2', 'main_h-overlay_h-10')  # bottom center
                ]
                x, y = positions[i % len(positions)]
                
                filter_chain += f"{last_out}[{scaled}]overlay={x}:{y}[{out}]; "
                last_out = f"[{out}]"
                ffmpeg_inputs.extend(['-i', logo_file])
            
            # Remove trailing semicolon and space
            filter_chain = filter_chain.rstrip('; ')
            
            # Create output file
            main_with_logos = raw_file.parent / f"with_logos_{raw_file.name}"
            
            # Build FFmpeg command
            logo_cmd = [
                'ffmpeg', '-y'
            ] + ffmpeg_inputs + [
                '-filter_complex', filter_chain,
                '-map', last_out,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(main_with_logos)
            ]
            
            log.info(f"🎨 Logo overlay command: {' '.join(logo_cmd)}")
            
            # Run logo overlay with timeout
            try:
                logo_process = subprocess.Popen(
                    logo_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logo_start_time = time.time()
                logo_timeout = 300  # 5 minutes timeout
                
                while logo_process.poll() is None:
                    if time.time() - logo_start_time > logo_timeout:
                        log.error(f"❌ Logo overlay timed out after {logo_timeout}s")
                        logo_process.terminate()
                        raise Exception(f"Logo overlay timed out after {logo_timeout}s")
                    time.sleep(1)
                
                logo_stdout, logo_stderr = logo_process.communicate()
                
                if logo_process.returncode == 0:
                    log.info(f"✅ Logo overlay completed successfully in {time.time() - logo_start_time:.2f}s")
                    if logo_stderr:
                        log.info(f"📋 Logo overlay stderr: {logo_stderr}")
                    
                    # Check for silent failures in logo overlay
                    if main_with_logos.exists():
                        logo_output_size = main_with_logos.stat().st_size
                        log.info(f"🔎 Logo overlay output: {main_with_logos}, size: {logo_output_size:,} bytes")
                        if logo_output_size == 0:
                            log.error(f"❌ Logo overlay output file is empty!")
                            return None
                    else:
                        log.error(f"❌ Logo overlay output file does not exist: {main_with_logos}")
                        return None
                else:
                    log.error(f"❌ Logo overlay failed with return code: {logo_process.returncode}")
                    log.error(f"❌ Logo overlay stderr: {logo_stderr}")
                    return None
            except subprocess.TimeoutExpired:
                log.error(f"❌ Logo overlay timed out")
                return None
            except Exception as e:
                log.error(f"❌ Logo overlay error: {e}")
                return None
            
            # DON'T clean up re-encoded video - we need it for concat!
            log.info(f"🔧 Keeping re-encoded video for concat: {merged_reencoded}")
            
            # Step 3: Re-encode intro video to fix timestamp corruption
            log.info(f"🔧 Re-encoding intro video to fix timestamp corruption...")
            intro_reencoded = raw_file.parent / f"intro_reencoded_{intro_path.name}"
            
            intro_reencode_cmd = [
                'ffmpeg', '-y',
                '-i', str(intro_path),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(intro_reencoded)
            ]
            
            log.info(f"🎬 Intro re-encode command: {' '.join(intro_reencode_cmd)}")
            
            # Run intro re-encode with timeout
            try:
                intro_reencode_process = subprocess.Popen(
                    intro_reencode_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                intro_reencode_start_time = time.time()
                intro_reencode_timeout = 300  # 5 minutes timeout
                
                while intro_reencode_process.poll() is None:
                    if time.time() - intro_reencode_start_time > intro_reencode_timeout:
                        log.error(f"❌ Intro re-encode timed out after {intro_reencode_timeout}s")
                        intro_reencode_process.terminate()
                        raise Exception(f"Intro re-encode timed out after {intro_reencode_timeout}s")
                    time.sleep(1)
                
                intro_reencode_stdout, intro_reencode_stderr = intro_reencode_process.communicate()
                
                if intro_reencode_process.returncode == 0:
                    log.info(f"✅ Intro re-encode completed successfully in {time.time() - intro_reencode_start_time:.2f}s")
                    if intro_reencode_stderr:
                        log.info(f"📋 Intro re-encode stderr: {intro_reencode_stderr}")
                else:
                    log.error(f"❌ Intro re-encode failed with return code {intro_reencode_process.returncode}")
                    log.error(f"❌ Intro re-encode stderr: {intro_reencode_stderr}")
                    raise Exception(f"Intro re-encode failed: {intro_reencode_stderr}")
                    
            except subprocess.TimeoutExpired:
                log.error(f"❌ Intro re-encode timed out")
                return None
            except Exception as e:
                log.error(f"❌ Intro re-encode error: {e}")
                return None
            
            # Step 4: Concat clean intro and logo-overlaid main
            concat_output = raw_file.parent / f"concat_{raw_file.name}"
            
            # Using filter-based concat instead of demuxer - no concat list file needed
            log.info(f"📋 Using filter-based concat for different resolutions")
            log.info(f"📋   Intro video: {intro_reencoded}")
            log.info(f"📋   Main video: {main_with_logos}")
            
            # Verify both input files exist and get detailed info
            if not intro_reencoded.exists():
                log.error(f"❌ Re-encoded intro video does not exist: {intro_reencoded}")
                raise Exception(f"Re-encoded intro video does not exist: {intro_reencoded}")
            
            if not main_with_logos.exists():
                log.error(f"❌ Main video with logos does not exist: {main_with_logos}")
                raise Exception(f"Main video with logos does not exist: {main_with_logos}")
            
            # Get detailed file info
            intro_size = intro_reencoded.stat().st_size
            main_size = main_with_logos.stat().st_size
            log.info(f"📊 File sizes:")
            log.info(f"📊   Intro video: {intro_size} bytes")
            log.info(f"📊   Main video: {main_size} bytes")
            
            # Validate both videos with ffprobe before concat to ensure compatibility
            try:
                # Check intro video
                intro_ffprobe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,avg_frame_rate,width,height,pix_fmt', '-of', 'default=noprint_wrappers=1:nokey=1', str(intro_reencoded)]
                intro_result = subprocess.run(intro_ffprobe_cmd, capture_output=True, text=True, timeout=30)
                if intro_result.returncode != 0:
                    log.error(f"❌ Intro video validation failed: {intro_result.stderr}")
                    raise Exception(f"Intro video validation failed: {intro_result.stderr}")
                log.info(f"✅ Intro video validation passed")
                
                # Check main video
                main_ffprobe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,avg_frame_rate,width,height,pix_fmt', '-of', 'default=noprint_wrappers=1:nokey=1', str(main_with_logos)]
                main_result = subprocess.run(main_ffprobe_cmd, capture_output=True, text=True, timeout=30)
                if main_result.returncode != 0:
                    log.error(f"❌ Main video validation failed: {main_result.stderr}")
                    raise Exception(f"Main video validation failed: {main_result.stderr}")
                log.info(f"✅ Main video validation passed")
                
                # Compare video properties to ensure compatibility
                intro_info = intro_result.stdout.strip().split('\n')
                main_info = main_result.stdout.strip().split('\n')
                
                if len(intro_info) >= 5 and len(main_info) >= 5:
                    log.info(f"📊 Video compatibility check:")
                    log.info(f"   Intro: codec={intro_info[0]}, fps={intro_info[1]}, width={intro_info[2]}, height={intro_info[3]}, pix_fmt={intro_info[4]}")
                    log.info(f"   Main:  codec={main_info[0]}, fps={main_info[1]}, width={main_info[2]}, height={main_info[3]}, pix_fmt={main_info[4]}")
                    
                    # Check if properties match (they should for safe concat)
                    if (intro_info[0] != main_info[0] or 
                        intro_info[1] != main_info[1] or 
                        intro_info[2] != main_info[2] or 
                        intro_info[3] != main_info[3] or 
                        intro_info[4] != main_info[4]):
                        log.warning(f"⚠️ Video properties don't match - re-encoding will fix this")
                    else:
                        log.info(f"✅ Video properties match - safe for concat")
                        
            except Exception as e:
                log.error(f"❌ Error validating videos with ffprobe: {e}")
                raise Exception(f"Error validating videos: {e}")
            
            log.info(f"✅ Both input files exist, starting FFmpeg...")
            
            # Step 4: Normalize both videos to identical properties before concat
            log.info(f"🔧 Normalizing videos to identical properties for safe concat...")
            
            # Get target properties from main video
            main_info = get_video_info(main_with_logos)
            if main_info is None:
                log.error(f"❌ Could not get main video info for normalization")
                return None
            
            main_codec, main_width, main_height, main_fps, main_pix_fmt = main_info
            log.info(f"📊 Target properties: {main_width}x{main_height}, {main_fps}fps, {main_pix_fmt}")
            
            # Normalize intro video to match main video properties
            intro_normalized = raw_file.parent / f"intro_normalized_{intro_reencoded.name}"
            intro_normalize_cmd = [
                'ffmpeg', '-y',
                '-i', str(intro_reencoded),
                '-vf', f'scale={main_width}:{main_height}:force_original_aspect_ratio=decrease,pad={main_width}:{main_height}:(ow-iw)/2:(oh-ih)/2',
                '-r', str(main_fps),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(intro_normalized)
            ]
            
            log.info(f"🎬 Intro normalization command: {' '.join(intro_normalize_cmd)}")
            
            try:
                intro_normalize_result = subprocess.run(intro_normalize_cmd, capture_output=True, text=True, timeout=300)
                if intro_normalize_result.returncode != 0:
                    log.error(f"❌ Intro normalization failed: {intro_normalize_result.stderr}")
                    return None
                log.info(f"✅ Intro video normalized successfully")
            except Exception as e:
                log.error(f"❌ Intro normalization error: {e}")
                return None
            
            # Normalize main video to ensure consistent properties
            main_normalized = raw_file.parent / f"main_normalized_{main_with_logos.name}"
            main_normalize_cmd = [
                'ffmpeg', '-y',
                '-i', str(main_with_logos),
                '-r', str(main_fps),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                str(main_normalized)
            ]
            
            log.info(f"🎬 Main normalization command: {' '.join(main_normalize_cmd)}")
            
            try:
                main_normalize_result = subprocess.run(main_normalize_cmd, capture_output=True, text=True, timeout=300)
                if main_normalize_result.returncode != 0:
                    log.error(f"❌ Main normalization failed: {main_normalize_result.stderr}")
                    return None
                log.info(f"✅ Main video normalized successfully")
            except Exception as e:
                log.error(f"❌ Main normalization error: {e}")
                return None
            
            # Step 5: Use concat demuxer with normalized videos (more reliable than filter)
            log.info(f"🎬 Using concat demuxer with normalized videos...")
            
            # Create concat list file
            concat_list_file = raw_file.parent / "concat_list_normalized.txt"
            concat_list_content = f"""file '{intro_normalized}'
file '{main_normalized}'"""
            
            with open(concat_list_file, 'w') as f:
                f.write(concat_list_content)
            
            log.info(f"📋 Concat list content: {concat_list_content}")
            
            # Run concat with demuxer (more reliable for matching videos)
            concat_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_list_file),
                '-c', 'copy',  # Use copy since videos are now identical
                str(concat_output)
            ]
            
            log.info(f"🎬 Concat command: {' '.join(concat_cmd)}")
            
            # Run FFmpeg with progress monitoring and capture stderr for debugging
            try:
                process = subprocess.Popen(
                    concat_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Monitor progress with timeout
                start_time = time.time()
                timeout = 600  # 10 minutes timeout
                
                while process.poll() is None:
                    if time.time() - start_time > timeout:
                        log.error(f"❌ FFmpeg concat timed out after {timeout}s")
                        process.terminate()
                        raise Exception(f"FFmpeg concat timed out after {timeout}s")
                    time.sleep(1)
                
                # Get the result and stderr for debugging
                stdout, stderr = process.communicate()
                
                # Check result
                if process.returncode == 0:
                    log.info(f"✅ Concat completed successfully in {time.time() - start_time:.2f}s")
                    if stderr:
                        log.info(f"📋 FFmpeg stderr: {stderr}")
                    
                    # Verify the concat output file
                    if concat_output.exists():
                        output_size = concat_output.stat().st_size
                        log.info(f"🔎 Concat file created: {concat_output}, size: {output_size:,} bytes")
                        if output_size == 0:
                            log.error(f"❌ Concat output file is empty!")
                            raise Exception("Concat output file is empty")
                        
                        # Enhanced verification: check video properties
                        final_info = get_video_info(concat_output)
                        if final_info:
                            final_codec, final_width, final_height, final_fps, final_pix_fmt = final_info
                            log.info(f"📊 Final video properties: {final_width}x{final_height}, {final_fps}fps, {final_pix_fmt}")
                        else:
                            log.warning(f"⚠️ Could not get final video properties")
                    else:
                        log.error(f"❌ Concat output file does not exist: {concat_output}")
                        raise Exception(f"Concat output file does not exist: {concat_output}")
                else:
                    log.error(f"❌ FFmpeg concat failed with return code {process.returncode}")
                    log.error(f"❌ FFmpeg stderr: {stderr}")
                    raise Exception(f"FFmpeg concat failed: {stderr}")
            except subprocess.TimeoutExpired:
                log.error(f"❌ FFmpeg concat timed out")
                return None
            except Exception as e:
                log.error(f"❌ FFmpeg concat error: {e}")
                return None
            

            
            # Clean up temporary files
            try:
                if intro_reencoded.exists():
                    intro_reencoded.unlink()
                    log.info(f"🧹 Cleaned up re-encoded intro video: {intro_reencoded}")
                if intro_normalized.exists():
                    intro_normalized.unlink()
                    log.info(f"🧹 Cleaned up normalized intro video: {intro_normalized}")
                if main_normalized.exists():
                    main_normalized.unlink()
                    log.info(f"🧹 Cleaned up normalized main video: {main_normalized}")
                if concat_list_file.exists():
                    concat_list_file.unlink()
                    log.info(f"🧹 Cleaned up concat list file: {concat_list_file}")
            except Exception as e:
                log.warn(f"⚠️ Failed to clean up temporary files: {e}")
            
            # Verify the final video duration with enhanced logging
            if concat_output.exists():
                final_duration = get_duration(concat_output)
                intro_duration = get_duration(intro_normalized) if intro_normalized.exists() else get_duration(intro_reencoded) if intro_reencoded.exists() else get_duration(intro_path)
                main_duration = get_duration(main_normalized) if main_normalized.exists() else get_duration(main_with_logos)
                expected_duration = intro_duration + main_duration
                
                log.info(f"📊 Duration verification:")
                log.info(f"📊   Intro video: {intro_duration:.2f}s")
                log.info(f"📊   Main video: {main_duration:.2f}s")
                log.info(f"📊   Expected total: {expected_duration:.2f}s")
                log.info(f"📊   Final video: {final_duration:.2f}s")
                
                # Enhanced duration validation with tolerance
                duration_diff = abs(final_duration - expected_duration)
                tolerance = 1.0  # 1 second tolerance for rounding differences
                
                if duration_diff > tolerance:
                    log.error(f"❌ Duration mismatch! Expected {expected_duration:.2f}s, got {final_duration:.2f}s (diff: {duration_diff:.2f}s)")
                    log.error(f"❌ This indicates the concat failed - video may be truncated")
                    
                    # Additional debugging: check individual file durations
                    log.info(f"🔍 Debugging individual file durations:")
                    if intro_normalized.exists():
                        log.info(f"   Normalized intro: {get_duration(intro_normalized):.2f}s")
                    if main_normalized.exists():
                        log.info(f"   Normalized main: {get_duration(main_normalized):.2f}s")
                    
                    # Try to identify which part was truncated
                    if final_duration < intro_duration:
                        log.error(f"❌ Final video is shorter than intro - intro may have been truncated")
                    elif final_duration < main_duration:
                        log.error(f"❌ Final video is shorter than main - main may have been truncated")
                    else:
                        log.error(f"❌ Unexpected duration mismatch - investigate further")
                else:
                    log.info(f"✅ Duration verification passed (difference: {duration_diff:.2f}s)")
                    
                    # Try to debug by checking the actual concat output file
                    try:
                        ffprobe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(concat_output)]
                        result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            log.info(f"✅ Final video is valid (ffprobe check passed)")
                            log.info(f"📊 Final video size: {concat_output.stat().st_size} bytes")
                        else:
                            log.error(f"❌ Final video is corrupted: {result.stderr}")
                    except Exception as e:
                        log.error(f"❌ Error checking final video: {e}")
                    
                    # Additional quality check
                    output_size = concat_output.stat().st_size
                    if output_size < 1024 * 1024:  # Less than 1MB
                        log.error(f"❌ Final video too small: {output_size:,} bytes")
                        return None
                    else:
                        log.info(f"✅ Final video size: {output_size:,} bytes")
            else:
                log.error(f"❌ Final concat video does not exist: {concat_output}")
                raise Exception(f"Final concat video does not exist: {concat_output}")

            # Final output is concat_output
            output_file = PROCESSED_DIR / date_dir.name / raw_file.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(concat_output), str(output_file))
            
            # Clean up temp files
            try:
                if merged_reencoded.exists():
                    merged_reencoded.unlink()
                    log.info(f"🧹 Cleaned up re-encoded video: {merged_reencoded}")
                if intro_reencoded.exists():
                    intro_reencoded.unlink()
                    log.info(f"🧹 Cleaned up re-encoded intro: {intro_reencoded}")
            except Exception as e:
                log.warn(f"⚠️ Failed to clean up temp files: {e}")
            
            return output_file
            
        else:
            # No intro video - use single-pass approach
            log.info(f"🎬 Using single-pass approach without intro video")
            
            # Build overlay specifications
            overlay_specs = []
            if logo_path:
                overlay_specs.append({
                    'name': 'user_logo',
                    'path': logo_path,
                    'position': 'bottom_right',
                    'width': LOGO_WIDTH,
                    'height': LOGO_HEIGHT
                })
            
            # Add sponsor logos
            for i, sponsor_path in enumerate(valid_sponsor_paths):
                overlay_specs.append({
                    'name': f'sponsor{i+1}',
                    'path': sponsor_path,
                    'position': ['bottom_left', 'bottom_right', 'bottom_center'][i % 3],
                    'width': LOGO_WIDTH,
                    'height': LOGO_HEIGHT
                })
            
            # Build filter chain for logo overlays
            filter_chain = ""
            ffmpeg_inputs = ['-i', str(raw_file)]
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
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    log.error(f"❌ Logo overlay pass failed with return code: {result.returncode}")
                    log.error(f"❌ FFmpeg stderr: {result.stderr}")
                    log.error(f"❌ FFmpeg stdout: {result.stdout}")
                    return None
                log.info(f"✅ Logo overlay completed in {time.time() - start:.2f}s")
            except subprocess.TimeoutExpired:
                log.error(f"❌ Logo overlay timed out")
                return None
            except Exception as e:
                log.error(f"❌ FFmpeg logo overlay error: {e}")
                return None

            # Final output is main_with_logos
            output_file = PROCESSED_DIR / date_dir.name / raw_file.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(main_with_logos), str(output_file))
            return output_file
            
    except Exception as e:
        log.error(f"❌ Error in process_single_video: {e}")
        return None


def insert_video_metadata(payload: dict) -> bool:
    headers = {
        "apikey": os.getenv("SUPABASE_ANON_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
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
