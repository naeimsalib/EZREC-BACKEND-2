#!/usr/bin/env python3
"""
Video Processing & Upload Service
- Watches /opt/ezrec-backend/raw_recordings/ for new files
- Fetches latest intro video and logo from Supabase (user_settings)
- Manages local cache for intro/logo (downloads new, deletes old if removed)
- Processes video (concatenates intro, overlays logo)
- Uploads to Supabase Storage, updates DB, retries failed uploads
- Designed to run as a standalone process (systemd service)
"""
import os
import time
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import subprocess
from uuid import UUID
import sys
import pytz
from zoneinfo import ZoneInfo
import uuid

load_dotenv()

# Validate required environment variables
REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"Missing required environment variables: {missing}")
    sys.exit(1)

LOCAL_TZ = ZoneInfo(os.popen('cat /etc/timezone').read().strip()) if os.path.exists('/etc/timezone') else None

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')
RAW_DIR = Path(os.getenv('RAW_RECORDINGS_DIR', '/opt/ezrec-backend/raw_recordings/'))
PROCESSED_DIR = Path(os.getenv('PROCESSED_RECORDINGS_DIR', '/opt/ezrec-backend/processed_recordings/'))
CACHE_DIR = Path(os.getenv('MEDIA_CACHE_DIR', '/opt/ezrec-backend/media_cache/'))
LOG_FILE = Path(os.getenv('VIDEO_WORKER_LOG', '/opt/ezrec-backend/logs/video_worker.log'))
FAILED_UPLOADS_FILE = Path(os.getenv('FAILED_UPLOADS_FILE', '/opt/ezrec-backend/failed_uploads.json'))
CHECK_INTERVAL = int(os.getenv('VIDEO_WORKER_CHECK_INTERVAL', '5'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_user_settings():
    try:
        response = supabase.table('user_settings').select('*').eq('user_id', USER_ID).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to fetch user_settings: {e}")
        return None

def sync_media_file(path_key, cache_name):
    """Download or delete intro/logo as needed. Returns local path or None."""
    user_settings = get_user_settings()
    if not user_settings or not user_settings.get(path_key):
        # Remove local file if it exists
        local_path = CACHE_DIR / cache_name
        if local_path.exists():
            local_path.unlink()
            logger.info(f"Deleted local {cache_name} (no longer in DB)")
        return None
    remote_path = user_settings[path_key]
    local_path = CACHE_DIR / cache_name
    # Download if not present or changed
    if not local_path.exists() or local_path.stat().st_size == 0:
        try:
            data = supabase.storage.from_('usermedia').download(remote_path)
            with open(local_path, 'wb') as f:
                f.write(data)
            logger.info(f"Downloaded {cache_name} from Supabase")
        except Exception as e:
            logger.warning(f"Failed to download {cache_name}: {e}")
            return None
    return local_path

def process_video(raw_path, intro_path, logo_path, output_path):
    """Process video: concatenate intro, overlay logo, encode. Fallback to copy if ffmpeg fails."""
    try:
        input_video = raw_path
        if intro_path and intro_path.exists():
            temp_concat = output_path.parent / f"temp_concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(intro_path),
                '-i', str(raw_path),
                '-filter_complex', '[0:v:0][1:v:0]concat=n=2:v=1[outv]',
                '-map', '[outv]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                str(temp_concat)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"FFmpeg concat failed: {result.stderr}")
                temp_concat = raw_path
            input_video = temp_concat
        if logo_path and logo_path.exists():
            cmd = [
                'ffmpeg', '-y',
                '-i', str(input_video),
                '-i', str(logo_path),
                '-filter_complex', 'overlay=W-w-10:H-h-10',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                str(output_path)
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(input_video),
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                str(output_path)
            ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg processing failed: {result.stderr}")
            # Fallback: try to copy raw video
            try:
                shutil.copy(str(raw_path), str(output_path))
                logger.info(f"Fallback: copied raw video to {output_path}")
            except Exception as e:
                logger.error(f"Fallback copy failed: {e}")
                return False
        logger.info(f"Video processed: {output_path}")
        if intro_path and intro_path.exists() and input_video != raw_path:
            input_video.unlink(missing_ok=True)
        return True
    except Exception as e:
        logger.error(f"Video processing error: {e}")
        return False

def upload_video(local_path, remote_path):
    try:
        with open(local_path, 'rb') as f:
            resp = supabase.storage.from_('videos').upload(remote_path, f)
        url = supabase.storage.from_('videos').get_public_url(remote_path)
        logger.info(f"Uploaded video to {remote_path}")
        return url
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Log full Supabase response if available
        try:
            logger.error(f"Supabase upload response: {resp}")
        except Exception:
            pass
        return None

def update_db(video_meta):
    try:
        supabase.table('videos').insert(video_meta).execute()
        logger.info(f"DB updated for video {video_meta['filename']}")
    except Exception as e:
        logger.error(f"Failed to update DB: {e}")

def update_booking_status(booking_id, status):
    try:
        supabase.table('bookings').update({'status': status}).eq('id', booking_id).execute()
        logger.info(f"Booking {booking_id} status set to '{status}' in Supabase.")
    except Exception as e:
        logger.error(f"Failed to update booking status in Supabase: {e}")

def is_valid_uuid(val):
    try:
        UUID(str(val))
        return True
    except Exception:
        return False

def retry_failed_uploads():
    if not FAILED_UPLOADS_FILE.exists():
        return
    try:
        with open(FAILED_UPLOADS_FILE, 'r') as f:
            failed_uploads = json.load(f)
    except Exception:
        failed_uploads = []
    still_failed = []
    for upload in failed_uploads:
        local_path = Path(upload['local_path'])
        remote_path = upload['remote_path']
        bucket = upload.get('bucket', 'videos')
        if not local_path.exists():
            continue
        url = upload_video(local_path, remote_path)
        if url:
            logger.info(f"Retried upload succeeded: {local_path}")
            try:
                local_path.unlink()
            except Exception:
                pass
        else:
            still_failed.append(upload)
    with open(FAILED_UPLOADS_FILE, 'w') as f:
        json.dump(still_failed, f)

def get_video_duration(video_path):
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def main():
    logger.info("Video Worker Service started")
    while True:
        retry_failed_uploads()
        for raw_file in RAW_DIR.glob('*.mp4'):
            # Only process files older than 30 seconds
            if raw_file.stat().st_mtime > time.time() - 30:
                continue
            # Use lock file to prevent double-processing
            lock_file = raw_file.with_suffix('.lock')
            if lock_file.exists():
                continue
            try:
                lock_file.touch()
                # Extract booking_id and validate
                try:
                    booking_id = raw_file.name.split('_')[1]
                    if not is_valid_uuid(booking_id):
                        logger.warning(f"Invalid booking_id: {booking_id}")
                        continue
                except Exception:
                    booking_id = None
                # Only process if booking status is 'completed'
                booking_status = None
                if booking_id:
                    try:
                        resp = supabase.table('bookings').select('status').eq('id', booking_id).execute()
                        if resp.data and resp.data[0]['status'] != 'completed':
                            continue
                        booking_status = resp.data[0]['status'] if resp.data else None
                    except Exception:
                        continue
                # Handle stale files (older than 6 hours)
                if raw_file.stat().st_mtime < time.time() - 21600:
                    logger.warning(f"Stale raw file: {raw_file}")
                    raw_file.unlink(missing_ok=True)
                    continue
                # Prepare output path with UUID and timestamp
                unique_id = str(uuid.uuid4())
                timestamp = datetime.now(LOCAL_TZ).strftime('%Y%m%d_%H%M%S')
                output_file = PROCESSED_DIR / f"processed_{timestamp}_{unique_id}.mp4"
                # Sync intro and logo
                intro_path = sync_media_file('intro_video_path', 'intro.mp4')
                logo_path = sync_media_file('logo_path', 'logo.png')
                # Process video
                if not process_video(raw_file, intro_path, logo_path, output_file):
                    continue
                # After processing, update booking status to 'video_processed'
                if booking_id:
                    update_booking_status(booking_id, 'video_processed')
                # Upload
                remote_path = f"{USER_ID}/{output_file.name}"
                url = upload_video(output_file, remote_path)
                # Validate upload
                if not url or not url.startswith('http'):
                    logger.error(f"Upload failed or invalid URL for {output_file}")
                    # Save failed upload info for retry
                    failed_uploads = []
                    if FAILED_UPLOADS_FILE.exists():
                        try:
                            with open(FAILED_UPLOADS_FILE, 'r') as f:
                                failed_uploads = json.load(f)
                        except Exception:
                            pass
                    failed_uploads.append({
                        'local_path': str(output_file),
                        'remote_path': remote_path,
                        'bucket': 'videos'
                    })
                    with open(FAILED_UPLOADS_FILE, 'w') as f:
                        json.dump(failed_uploads, f)
                    logger.error(f"Failed to upload {output_file}; will retry later.")
                    continue
                duration = get_video_duration(output_file)
                video_meta = {
                    'filename': output_file.name,
                    'storage_path': remote_path,
                    'user_id': USER_ID,
                    'file_url': url,
                    'file_size': output_file.stat().st_size,
                    'created_at': datetime.now(LOCAL_TZ).isoformat(),
                    'upload_timestamp': datetime.now(LOCAL_TZ).isoformat(),
                    'duration_seconds': duration,
                }
                update_db(video_meta)
                # After upload, update booking status to 'video_uploaded'
                if booking_id:
                    update_booking_status(booking_id, 'video_uploaded')
                raw_file.unlink(missing_ok=True)
                output_file.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Error processing {raw_file}: {e}")
            finally:
                if lock_file.exists():
                    lock_file.unlink()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main() 