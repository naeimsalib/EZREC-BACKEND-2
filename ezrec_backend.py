#!/usr/bin/env python3
"""
EZREC Backend - Complete Video Recording System for Raspberry Pi

This script automates video recording based on bookings from a Supabase database, processes the video, uploads it to Supabase Storage, and updates the database. It is designed to be robust against internet outages and hardware failures.

Key Features:
- Polls bookings from Supabase and caches them locally for offline operation
- Records video using picamera2 (if available)
- Processes video with FFmpeg (intro, logo, encoding)
- Uploads videos to Supabase Storage, with retry on failure
- Updates booking and system status in Supabase
- Logs all actions and errors to file and stdout
- Designed for easy testing and extension
"""

import os
import sys
import time
import json
import logging
import hashlib
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import psutil
import signal
import pytz
import traceback
import socket
from zoneinfo import ZoneInfo

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
except ImportError:
    print("Warning: picamera2 not available")
    Picamera2 = None

from supabase import create_client, Client
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration class for all settings
class Config:
    """
    Loads and stores configuration from environment variables.
    All timeouts, intervals, and paths are configurable here.
    """
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    USER_ID = os.getenv('USER_ID')
    CAMERA_ID = os.getenv('CAMERA_ID', '0')
    TEMP_DIR = Path(os.getenv('TEMP_DIR', '/opt/ezrec-backend/temp'))
    LOG_DIR = Path(os.getenv('LOG_DIR', '/opt/ezrec-backend/logs'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    RECORDING_FPS = int(os.getenv('RECORDING_FPS', '30'))
    BOOKING_CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))  # seconds
    STATUS_UPDATE_INTERVAL = int(os.getenv('STATUS_UPDATE_INTERVAL', '3'))  # seconds
    BOOKING_FETCH_INTERVAL = int(os.getenv('BOOKING_FETCH_INTERVAL', '60')) # seconds
    LOCAL_TZ = ZoneInfo(os.popen('cat /etc/timezone').read().strip()) if os.path.exists('/etc/timezone') else None
    BOOKING_CACHE_FILE = Path(os.getenv('BOOKING_CACHE_FILE', '/opt/ezrec-backend/bookings_cache.json'))
    FAILED_UPLOADS_FILE = Path(os.getenv('FAILED_UPLOADS_FILE', '/opt/ezrec-backend/failed_uploads.json'))

# Setup logging
def setup_logging():
    """
    Sets up logging to both file and stdout, with configurable log level.
    """
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = Config.LOG_DIR / 'ezrec.log'
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class DatabaseManager:
    """
    Handles all database operations with Supabase.
    Abstracts away direct Supabase calls for easier testing/mocking.
    """
    def __init__(self):
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.user_id = Config.USER_ID
        self.camera_info = None
        self._initialize_camera_info()

    def _initialize_camera_info(self):
        """Get camera and user information from database."""
        try:
            response = self.supabase.table('cameras').select('*').eq('id', Config.CAMERA_ID).execute()
            if response.data:
                self.camera_info = response.data[0]
                logger.info(f"Camera initialized: {self.camera_info.get('name', '')}")
            else:
                logger.warning(f"Camera with ID {Config.CAMERA_ID} not found (optional)")
        except Exception as e:
            logger.error(f"Failed to initialize camera info: {e}")

    def get_active_bookings(self) -> List[Dict]:
        """
        Get current active bookings for this user from Supabase.
        Returns a list of booking dicts.
        """
        try:
            now = datetime.now(Config.LOCAL_TZ)
            current_date = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M')
            logger.info(f"Fetching bookings for user_id={self.user_id}, date={current_date}, status=confirmed")
            response = self.supabase.table('bookings').select('*').eq(
                'user_id', self.user_id
            ).eq('date', current_date).eq('status', 'confirmed').execute()
            active_bookings = []
            for booking in response.data:
                if booking['start_time'] <= current_time <= booking['end_time']:
                    active_bookings.append(booking)
            logger.info(f"Found {len(active_bookings)} active bookings for user_id={self.user_id}")
            return active_bookings
        except Exception as e:
            logger.error(f"Failed to get active bookings: {e}")
            return []

    def update_camera_status(self, **kwargs):
        """Update camera status in database."""
        try:
            update_data = {
                'last_heartbeat': datetime.now(Config.LOCAL_TZ).isoformat(),
                'last_seen': datetime.now(Config.LOCAL_TZ).isoformat(),
                **kwargs
            }
            self.supabase.table('cameras').update(update_data).eq('id', Config.CAMERA_ID).execute()
        except Exception as e:
            logger.error(f"Failed to update camera status: {e}")

    def update_system_status(self, **kwargs):
        """Update system status in database."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_celsius = float(f.read().strip()) / 1000.0
            except:
                temp_celsius = None
            update_data = {
                'user_id': self.user_id,
                'camera_id': Config.CAMERA_ID,
                'pi_active': True,
                'last_heartbeat': datetime.now(Config.LOCAL_TZ).isoformat(),
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': (disk.used / disk.total) * 100,
                'temperature_celsius': temp_celsius,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'updated_at': datetime.now(Config.LOCAL_TZ).isoformat(),
                **kwargs
            }
            existing = self.supabase.table('system_status').select('id').eq('camera_id', Config.CAMERA_ID).execute()
            if existing.data:
                self.supabase.table('system_status').update(update_data).eq('camera_id', Config.CAMERA_ID).execute()
            else:
                update_data['id'] = str(uuid.uuid4())
                self.supabase.table('system_status').insert(update_data).execute()
        except Exception as e:
            logger.error(f"Failed to update system status: {e}")

    def get_user_settings(self) -> Optional[Dict]:
        """Get user settings for intro video and logo."""
        try:
            response = self.supabase.table('user_settings').select('*').eq('user_id', self.user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get user settings: {e}")
            return None

    def insert_video_record(self, video_data: Dict) -> str:
        """Insert video record into videos table."""
        try:
            video_data['id'] = str(uuid.uuid4())
            video_data['user_id'] = self.user_id
            video_data['camera_id'] = Config.CAMERA_ID
            video_data['created_at'] = datetime.now(Config.LOCAL_TZ).isoformat()
            video_data['upload_timestamp'] = datetime.now(Config.LOCAL_TZ).isoformat()
            response = self.supabase.table('videos').insert(video_data).execute()
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Failed to insert video record: {e}")
            raise

    def update_booking_status(self, booking_id: str, status: str = 'completed'):
        """Update the status of a booking in the bookings table."""
        try:
            response = self.supabase.table('bookings').update({'status': status}).eq('id', booking_id).execute()
            logger.info(f"Booking {booking_id} status updated to {status}")
            return response
        except Exception as e:
            logger.error(f"Failed to update booking status: {e}")
            return None

class StorageManager:
    """
    Handles file storage and Supabase uploads/downloads.
    Abstracts storage logic for easier testing and mocking.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.supabase = db_manager.supabase
        self.backend = None  # Set by EZRECBackend for upload retry tracking

    def download_file(self, bucket: str, path: str, local_path: Path) -> bool:
        """
        Download a file from Supabase storage to a local path.
        Returns True on success, False on failure.
        """
        try:
            response = self.supabase.storage.from_(bucket).download(path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(response)
            logger.info(f"Downloaded {path} to {local_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download {path}: {e}")
            return False

    def upload_file(self, local_path: Path, bucket: str, remote_path: str) -> Optional[str]:
        """
        Upload a file to Supabase storage. Retries up to 3 times on failure.
        If upload fails, records the failed upload for later retry (if backend is set).
        Returns the public URL on success, or None on failure.
        """
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                with open(local_path, 'rb') as f:
                    response = self.supabase.storage.from_(bucket).upload(remote_path, f)
                public_url = self.supabase.storage.from_(bucket).get_public_url(remote_path)
                logger.info(f"Uploaded {local_path} to {remote_path}")
                return public_url
            except Exception as e:
                retry_count += 1
                logger.warning(f"Upload attempt {retry_count} failed: {e}")
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)  # Exponential backoff
                else:
                    logger.error(f"Failed to upload after {max_retries} attempts")
                    # Record failed upload for retry if backend is set
                    if self.backend:
                        failed_upload = {
                            'local_path': str(local_path),
                            'bucket': bucket,
                            'remote_path': remote_path
                        }
                        if failed_upload not in self.backend.failed_uploads:
                            self.backend.failed_uploads.append(failed_upload)
                            self.backend._save_failed_uploads()
                    return None

class VideoProcessor:
    """
    Handles video recording (with picamera2), FFmpeg processing, and upload logic.
    Orchestrates the full video pipeline for a booking.
    """
    def __init__(self, db_manager: DatabaseManager, storage_manager: StorageManager):
        self.db_manager = db_manager
        self.storage_manager = storage_manager
        self.is_recording = False
        self.current_recording = None
        self.recording_thread = None
        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    def start_recording(self, booking: Dict):
        """
        Start recording for a booking. Spawns a thread for the recording process.
        """
        if self.is_recording:
            logger.warning("Already recording, skipping new request")
            return
        self.is_recording = True
        self.current_recording = {
            'booking': booking,
            'start_time': datetime.now(Config.LOCAL_TZ),
            'recording_id': str(uuid.uuid4())
        }
        logger.info(f"Starting recording for booking {booking['id']}")
        self.db_manager.update_camera_status(is_recording=True)
        self.db_manager.update_system_status(
            is_recording=True,
            current_booking_id=booking['id'],
            camera_status='recording'
        )
        self.recording_thread = threading.Thread(target=self._record_video)
        self.recording_thread.start()

    def stop_recording(self):
        """
        Stop the current recording and start post-processing/upload in a new thread.
        """
        if not self.is_recording:
            return
        logger.info("Stopping recording and starting post-processing")
        self.is_recording = False
        self.db_manager.update_camera_status(is_recording=False)
        self.db_manager.update_system_status(
            is_recording=False,
            camera_status='processing'
        )
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=10)
        threading.Thread(target=self._process_and_upload).start()

    def _record_video(self):
        """
        Record video using picamera2 (if available) and save to a temp file.
        """
        if not Picamera2:
            logger.error("picamera2 not available")
            return
        recording_id = self.current_recording['recording_id']
        raw_video_path = Config.TEMP_DIR / f"raw_{recording_id}.mp4"
        try:
            picam2 = Picamera2()
            config = picam2.create_video_configuration(
                main={"size": (1920, 1080)},
                controls={"FrameRate": Config.RECORDING_FPS}
            )
            picam2.configure(config)
            encoder = H264Encoder(bitrate=10000000)
            output = FileOutput(str(raw_video_path))
            picam2.start_recording(encoder, output)
            logger.info(f"Recording started: {raw_video_path}")
            while self.is_recording:
                time.sleep(0.1)
            picam2.stop_recording()
            picam2.close()
            self.current_recording['end_time'] = datetime.now(Config.LOCAL_TZ)
            self.current_recording['raw_video_path'] = raw_video_path
            logger.info(f"Recording completed: {raw_video_path}")
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            self.is_recording = False
            self.db_manager.update_system_status(
                camera_status='error',
                last_error=str(e)
            )

    def _process_and_upload(self):
        """
        Process the recorded video (FFmpeg: intro, logo, encoding), upload to Supabase, and update DB.
        Cleans up temp files after successful upload.
        """
        try:
            if not self.current_recording or 'raw_video_path' not in self.current_recording:
                logger.error("No recording data available")
                return
            recording_id = self.current_recording['recording_id']
            booking = self.current_recording['booking']
            raw_video_path = self.current_recording['raw_video_path']
            if not raw_video_path.exists():
                logger.error(f"Raw video file not found: {raw_video_path}")
                return
            start_time = self.current_recording['start_time']
            # New filename and path
            date_str = start_time.strftime('%Y%m%d')
            time_str = start_time.strftime('%H%M')
            filename = f"recordings.{date_str}.{time_str}.{booking['id']}.mp4"
            final_video_path = Config.TEMP_DIR / filename
            # Download intro video and logo if available
            intro_path = None
            logo_path = None
            user_settings = self.db_manager.get_user_settings()
            if user_settings:
                if user_settings.get('intro_video_path'):
                    intro_path = Config.TEMP_DIR / f"intro_{recording_id}.mp4"
                    if not self.storage_manager.download_file(
                        'usermedia', user_settings['intro_video_path'], intro_path
                    ):
                        intro_path = None
                if user_settings.get('logo_path'):
                    logo_path = Config.TEMP_DIR / f"logo_{recording_id}.png"
                    if not self.storage_manager.download_file(
                        'usermedia', user_settings['logo_path'], logo_path
                    ):
                        logo_path = None
            # Process video with FFmpeg
            self._process_with_ffmpeg(raw_video_path, final_video_path, intro_path, logo_path)
            duration = self._get_video_duration(final_video_path)
            file_size = final_video_path.stat().st_size
            # Upload to Supabase
            remote_path = f"{self.db_manager.user_id}/{filename}"
            public_url = self.storage_manager.upload_file(final_video_path, 'videos', remote_path)
            if public_url:
                video_data = {
                    'filename': filename,
                    'storage_path': remote_path,
                    'booking_id': booking['id'],
                    'user_id': self.db_manager.user_id,
                    'file_url': public_url,
                    'file_size': file_size,
                    'duration_seconds': duration,
                    'recording_date': start_time.date().isoformat(),
                    'recording_start_time': start_time.strftime('%H:%M'),
                    'recording_end_time': self.current_recording['end_time'].strftime('%H:%M')
                }
                video_id = self.db_manager.insert_video_record(video_data)
                logger.info(f"Video uploaded successfully: {video_id}")
                # Update booking status to completed
                self.db_manager.update_booking_status(booking['id'], status='completed')
                self.db_manager.update_system_status(
                    camera_status='idle',
                    successful_uploads=1,
                    total_recordings=1
                )
                # Clean up local files only after successful upload
                self._cleanup_files([raw_video_path, final_video_path, intro_path, logo_path])
            else:
                logger.error("Failed to upload video - keeping local files")
                self.db_manager.update_system_status(
                    camera_status='error',
                    last_error='Upload failed'
                )
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            self.db_manager.update_system_status(
                camera_status='error',
                last_error=str(e)
            )
        finally:
            self.current_recording = None

    def _process_with_ffmpeg(self, raw_video: Path, output_video: Path, intro_video: Path = None, logo: Path = None):
        """
        Process video with FFmpeg: concatenate intro, overlay logo, encode.
        Falls back to copying raw video if FFmpeg fails.
        """
        try:
            if intro_video and intro_video.exists():
                temp_concat = Config.TEMP_DIR / f"temp_concat_{uuid.uuid4()}.mp4"
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(intro_video),
                    '-i', str(raw_video),
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
                    temp_concat = raw_video
                input_video = temp_concat
            else:
                input_video = raw_video
            if logo and logo.exists():
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_video),
                    '-i', str(logo),
                    '-filter_complex', 'overlay=W-w-10:H-h-10',
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    str(output_video)
                ]
            else:
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_video),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    str(output_video)
                ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"FFmpeg processing failed: {result.stderr}")
                subprocess.run(['cp', str(raw_video), str(output_video)])
            logger.info(f"Video processed successfully: {output_video}")
        except Exception as e:
            logger.error(f"FFmpeg processing error: {e}")
            subprocess.run(['cp', str(raw_video), str(output_video)])

    def _get_video_duration(self, video_path: Path) -> int:
        """
        Get video duration in seconds using ffprobe.
        Returns 0 if duration cannot be determined.
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return int(float(result.stdout.strip()))
        except:
            return 0

    def _cleanup_files(self, file_paths: List[Path]):
        """
        Clean up temporary files after processing/upload.
        """
        for file_path in file_paths:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Cleaned up: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {file_path}: {e}")

class EZRECBackend:
    """
    Main backend service orchestrator.
    Coordinates all components: database, storage, video processing, and system status.
    Handles offline resilience (local booking cache, deferred uploads), signal handling, and main loop.
    Designed for testability and maintainability.
    """
    def __init__(self):
        self.running = False
        self.db_manager = DatabaseManager()
        self.storage_manager = StorageManager(self.db_manager)
        self.storage_manager.backend = self  # For failed upload tracking
        self.video_processor = VideoProcessor(self.db_manager, self.storage_manager)
        self.current_booking = None
        self.local_booking_cache = []
        self.failed_uploads = self._load_failed_uploads()
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGTERM, SIGINT) for graceful exit.
        """
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _is_internet_available(self, host="8.8.8.8", port=53, timeout=3):
        """
        Check if the internet is available by attempting to connect to a public DNS server.
        Returns True if connection succeeds, False otherwise.
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception:
            return False

    def _save_bookings_cache(self):
        """
        Save the current local booking cache to disk for offline use.
        """
        try:
            with open(Config.BOOKING_CACHE_FILE, 'w') as f:
                json.dump(self.local_booking_cache, f)
        except Exception as e:
            logger.warning(f"Failed to save bookings cache: {e}")

    def _load_bookings_cache(self):
        """
        Load the local booking cache from disk (if available).
        """
        if Config.BOOKING_CACHE_FILE.exists():
            try:
                with open(Config.BOOKING_CACHE_FILE, 'r') as f:
                    self.local_booking_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load bookings cache: {e}")

    def _save_failed_uploads(self):
        """
        Save the list of failed uploads to disk for retry after outages.
        """
        try:
            with open(Config.FAILED_UPLOADS_FILE, 'w') as f:
                json.dump(self.failed_uploads, f)
        except Exception as e:
            logger.warning(f"Failed to save failed uploads: {e}")

    def _load_failed_uploads(self):
        """
        Load the list of failed uploads from disk (if available).
        """
        if Config.FAILED_UPLOADS_FILE.exists():
            try:
                with open(Config.FAILED_UPLOADS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load failed uploads: {e}")
        return []

    def start(self):
        """
        Start the backend service: load caches, retry failed uploads, and enter the main loop.
        """
        logger.info("Starting EZREC Backend...")
        self.running = True
        self._load_bookings_cache()
        self._retry_failed_uploads()
        self.db_manager.update_system_status(
            status='running',
            orchestrator_status='running',
            camera_status='idle',
            uptime_start=datetime.now(Config.LOCAL_TZ).isoformat()
        )
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Stop the backend service: stop recording, update status, and save caches.
        """
        logger.info("Stopping EZREC Backend...")
        self.running = False
        if self.video_processor.is_recording:
            self.video_processor.stop_recording()
        self.db_manager.update_system_status(
            status='stopped',
            orchestrator_status='stopped',
            camera_status='offline'
        )
        self._save_bookings_cache()
        self._save_failed_uploads()

    def _main_loop(self):
        """
        Main service loop: fetch bookings, process local bookings, retry uploads, and update status.
        Handles offline resilience and coordinates all system actions.
        """
        last_status_update = 0
        last_booking_fetch = 0
        booking_fetch_interval = Config.BOOKING_FETCH_INTERVAL  # seconds
        while self.running:
            try:
                current_time = time.time()
                # Try to fetch bookings if internet is available and interval passed
                if self._is_internet_available() and (current_time - last_booking_fetch >= booking_fetch_interval):
                    active_bookings = self.db_manager.get_active_bookings()
                    if active_bookings:
                        self.local_booking_cache = active_bookings
                        self._save_bookings_cache()
                    last_booking_fetch = current_time
                # Always process bookings from local cache
                self._process_local_bookings()
                # Try to retry failed uploads if internet is available
                if self._is_internet_available():
                    self._retry_failed_uploads()
                # Update system status every STATUS_UPDATE_INTERVAL seconds
                if current_time - last_status_update >= Config.STATUS_UPDATE_INTERVAL:
                    self.db_manager.update_system_status()
                    last_status_update = current_time
                time.sleep(Config.BOOKING_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)

    def _process_local_bookings(self):
        """
        Check local bookings and manage recordings based on current time.
        Ensures scheduled recordings are not missed even if offline.
        """
        now = datetime.now(Config.LOCAL_TZ)
        current_time = now.strftime('%H:%M')
        current_date = now.strftime('%Y-%m-%d')
        # Only consider bookings for today and current time
        active = [b for b in self.local_booking_cache if b['date'] == current_date and b['start_time'] <= current_time <= b['end_time']]
        if not active:
            if self.video_processor.is_recording:
                self.video_processor.stop_recording()
                self.current_booking = None
            return
        if active and not self.video_processor.is_recording:
            booking = active[0]
            if not self.current_booking or self.current_booking['id'] != booking['id']:
                self.current_booking = booking
                self.video_processor.start_recording(booking)
        elif not active and self.video_processor.is_recording:
            self.video_processor.stop_recording()
            self.current_booking = None

    def _retry_failed_uploads(self):
        """
        Attempt to retry all failed uploads (if any). Removes successful uploads from the queue.
        """
        if not self.failed_uploads:
            return
        logger.info(f"Retrying {len(self.failed_uploads)} failed uploads...")
        still_failed = []
        for upload in self.failed_uploads:
            try:
                local_path = Path(upload['local_path'])
                bucket = upload['bucket']
                remote_path = upload['remote_path']
                if local_path.exists():
                    url = self.storage_manager.upload_file(local_path, bucket, remote_path)
                    if url:
                        logger.info(f"Retried upload succeeded: {local_path}")
                        # Optionally, update DB or perform post-upload actions here
                        local_path.unlink()
                    else:
                        still_failed.append(upload)
                else:
                    logger.warning(f"File for failed upload not found: {local_path}")
            except Exception as e:
                logger.error(f"Retry upload failed: {e}")
                still_failed.append(upload)
        self.failed_uploads = still_failed
        self._save_failed_uploads()

def main():
    """
    Main entry point for the EZREC backend service.
    Initializes and starts the orchestrator. Exits with error code on failure.
    """
    try:
        if not Picamera2:
            logger.error("picamera2 is required but not installed")
            sys.exit(1)
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            logger.error("SUPABASE_URL and SUPABASE_KEY required")
            sys.exit(1)
        backend = EZRECBackend()
        backend.start()
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main() 