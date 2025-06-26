#!/usr/bin/env python3
"""
EZREC Backend - Complete Video Recording System for Raspberry Pi
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

# Configuration
class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    CAMERA_ID = os.getenv('CAMERA_ID', '0')
    TEMP_DIR = Path('/opt/ezrec-backend/temp')
    LOG_DIR = Path('/opt/ezrec-backend/logs')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    RECORDING_FPS = int(os.getenv('RECORDING_FPS', '30'))
    BOOKING_CHECK_INTERVAL = 3  # seconds
    STATUS_UPDATE_INTERVAL = 3  # seconds

# Setup logging
def setup_logging():
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
    """Handles all database operations"""
    
    def __init__(self):
        if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.camera_info = None
        self.user_id = None
        self._initialize_camera_info()
    
    def _initialize_camera_info(self):
        """Get camera and user information from database"""
        try:
            response = self.supabase.table('cameras').select('*').eq('id', Config.CAMERA_ID).execute()
            if response.data:
                self.camera_info = response.data[0]
                self.user_id = self.camera_info['user_id']
                logger.info(f"Camera initialized: {self.camera_info['name']} for user {self.user_id}")
            else:
                logger.error(f"Camera with ID {Config.CAMERA_ID} not found")
                raise ValueError(f"Camera {Config.CAMERA_ID} not found")
        except Exception as e:
            logger.error(f"Failed to initialize camera info: {e}")
            raise
    
    def get_active_bookings(self) -> List[Dict]:
        """Get current active bookings for this user"""
        try:
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M:%S')
            
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
        """Update camera status in database"""
        try:
            update_data = {
                'last_heartbeat': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat(),
                **kwargs
            }
            self.supabase.table('cameras').update(update_data).eq('id', Config.CAMERA_ID).execute()
        except Exception as e:
            logger.error(f"Failed to update camera status: {e}")
    
    def update_system_status(self, **kwargs):
        """Update system status in database"""
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
                'last_heartbeat': datetime.utcnow().isoformat(),
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': (disk.used / disk.total) * 100,
                'temperature_celsius': temp_celsius,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'updated_at': datetime.utcnow().isoformat(),
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
        """Get user settings for intro video and logo"""
        try:
            response = self.supabase.table('user_settings').select('*').eq('user_id', self.user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get user settings: {e}")
            return None
    
    def insert_video_record(self, video_data: Dict) -> str:
        """Insert video record into videos table"""
        try:
            video_data['id'] = str(uuid.uuid4())
            video_data['user_id'] = self.user_id
            video_data['camera_id'] = Config.CAMERA_ID
            video_data['created_at'] = datetime.utcnow().isoformat()
            video_data['upload_timestamp'] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('videos').insert(video_data).execute()
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Failed to insert video record: {e}")
            raise

class StorageManager:
    """Handles file storage and Supabase uploads"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.supabase = db_manager.supabase
    
    def download_file(self, bucket: str, path: str, local_path: Path) -> bool:
        """Download file from Supabase storage"""
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
        """Upload file to Supabase storage"""
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
                    return None

class VideoProcessor:
    """Handles video recording and FFmpeg processing"""
    
    def __init__(self, db_manager: DatabaseManager, storage_manager: StorageManager):
        self.db_manager = db_manager
        self.storage_manager = storage_manager
        self.is_recording = False
        self.current_recording = None
        self.recording_thread = None
        
        Config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    def start_recording(self, booking: Dict):
        """Start recording for a booking"""
        if self.is_recording:
            logger.warning("Already recording, skipping new request")
            return
        
        self.is_recording = True
        self.current_recording = {
            'booking': booking,
            'start_time': datetime.now(),
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
        """Stop current recording and process video"""
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
        """Record video using picamera2"""
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
            
            self.current_recording['end_time'] = datetime.now()
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
        """Process video with FFmpeg and upload to Supabase"""
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
            filename = f"recording_{start_time.strftime('%Y%m%d_%H%M%S')}_{recording_id}.mp4"
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
                    'file_url': public_url,
                    'file_size': file_size,
                    'duration_seconds': duration,
                    'recording_date': start_time.date().isoformat(),
                    'recording_start_time': start_time.strftime('%H:%M:%S'),
                    'recording_end_time': self.current_recording['end_time'].strftime('%H:%M:%S')
                }
                
                video_id = self.db_manager.insert_video_record(video_data)
                logger.info(f"Video uploaded successfully: {video_id}")
                
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
        """Process video with FFmpeg"""
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
        """Get video duration in seconds"""
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
        """Clean up temporary files"""
        for file_path in file_paths:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Cleaned up: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {file_path}: {e}")

class EZRECBackend:
    """Main backend service orchestrator"""
    
    def __init__(self):
        self.running = False
        self.db_manager = DatabaseManager()
        self.storage_manager = StorageManager(self.db_manager)
        self.video_processor = VideoProcessor(self.db_manager, self.storage_manager)
        self.current_booking = None
        self.local_booking_cache = None
        
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the backend service"""
        logger.info("Starting EZREC Backend...")
        self.running = True
        
        self.db_manager.update_system_status(
            status='running',
            orchestrator_status='running',
            camera_status='idle',
            uptime_start=datetime.utcnow().isoformat()
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
        """Stop the backend service"""
        logger.info("Stopping EZREC Backend...")
        self.running = False
        
        if self.video_processor.is_recording:
            self.video_processor.stop_recording()
        
        self.db_manager.update_system_status(
            status='stopped',
            orchestrator_status='stopped',
            camera_status='offline'
        )
    
    def _main_loop(self):
        """Main service loop"""
        last_status_update = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Update booking cache every 3 seconds
                self._update_booking_cache()
                self._check_bookings()
                
                # Update system status every 3 seconds
                if current_time - last_status_update >= Config.STATUS_UPDATE_INTERVAL:
                    self.db_manager.update_system_status()
                    last_status_update = current_time
                
                time.sleep(Config.BOOKING_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
    
    def _update_booking_cache(self):
        """Update local booking cache from database"""
        try:
            active_bookings = self.db_manager.get_active_bookings()
            self.local_booking_cache = active_bookings
            logger.debug(f"Updated booking cache: {len(active_bookings)} active bookings")
        except Exception as e:
            logger.error(f"Failed to update booking cache: {e}")
    
    def _check_bookings(self):
        """Check bookings and manage recordings using local cache"""
        try:
            if not self.local_booking_cache:
                if self.video_processor.is_recording:
                    self.video_processor.stop_recording()
                    self.current_booking = None
                return
            
            if self.local_booking_cache and not self.video_processor.is_recording:
                booking = self.local_booking_cache[0]
                if not self.current_booking or self.current_booking['id'] != booking['id']:
                    self.current_booking = booking
                    self.video_processor.start_recording(booking)
            
            elif not self.local_booking_cache and self.video_processor.is_recording:
                self.video_processor.stop_recording()
                self.current_booking = None
                
        except Exception as e:
            logger.error(f"Error checking bookings: {e}")

def main():
    """Main entry point"""
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
        sys.exit(1)

if __name__ == "__main__":
    main() 