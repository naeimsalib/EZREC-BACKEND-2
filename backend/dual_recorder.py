#!/usr/bin/env python3
"""
EZREC Dual Camera Recorder - Clean Architecture
- Uses direct camera detection for reliable camera access
- Records from both cameras simultaneously using threads
- Merges recordings using FFmpeg
- Robust error handling and logging
"""

import os
import sys
import time
import json
import logging
import signal
import pytz
import psutil
import threading
import subprocess
from pathlib import Path
from dateutil import parser
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# 🔧 Ensure API utils can be imported
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

from booking_utils import update_booking_status

# Load environment
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

# Environment variables
TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE") or os.getenv("SYSTEM_TIMEZONE") or "UTC"
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)

REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"❌ Missing required environment variables: {missing}")
    sys.exit(1)

USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
RECORDINGS_DIR = Path('/opt/ezrec-backend/recordings/')
LOG_FILE = Path('/opt/ezrec-backend/logs/dual_recorder.log')
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '3'))

# Camera configuration
CAMERA_0_SERIAL = os.getenv('CAMERA_0_SERIAL', '88000')
CAMERA_1_SERIAL = os.getenv('CAMERA_1_SERIAL', '80000')
CAMERA_0_NAME = os.getenv('CAMERA_0_NAME', 'left')
CAMERA_1_NAME = os.getenv('CAMERA_1_NAME', 'right')
DUAL_CAMERA_MODE = os.getenv('DUAL_CAMERA_MODE', 'true').lower() == 'true'
MERGE_METHOD = os.getenv('MERGE_METHOD', 'side_by_side')
AUTO_UPLOAD = os.getenv('AUTO_UPLOAD', 'false').lower() == 'true'

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'dual_recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ dual_recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

def setup_rotating_logger(log_file: Path, max_bytes: int = 10*1024*1024, backup_count: int = 5):
    """Set up a rotating file handler for logging"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count
    )
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)
    
    return rotating_handler

# Set up logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        setup_rotating_logger(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
logger.info(f"🎬 Merge method: {MERGE_METHOD}")

def set_is_recording(value: bool):
    """Update recording status in status.json"""
    try:
        status_path = Path("/opt/ezrec-backend/status.json")
        status = {}
        if status_path.exists():
            try:
                with open(status_path) as f:
                    status = json.load(f)
            except Exception:
                status = {}
        status["is_recording"] = value
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to update recording status: {e}")

def detect_cameras():
    """Detect available cameras by trying to access them directly and return camera indices"""
    try:
        from picamera2 import Picamera2
        
        logger.info("🔍 Detecting cameras by direct access...")
        
        # Try to detect cameras by attempting to create Picamera2 instances
        max_cameras = 4  # Try up to 4 camera indices
        available_cameras = []
        
        for i in range(max_cameras):
            try:
                # Try to create a Picamera2 instance
                temp_cam = Picamera2(index=i)
                props = temp_cam.camera_properties
                temp_cam.close()
                
                serial = props.get('SerialNumber', f'unknown_{i}')
                logger.info(f"📷 Camera {i}: Serial {serial}")
                available_cameras.append((i, serial))
                
            except Exception as e:
                logger.debug(f"Camera {i} not available: {e}")
                continue
        
        logger.info(f"🔍 Found {len(available_cameras)} camera(s)")
        
        if len(available_cameras) < 2:
            logger.warning(f"⚠️ Only {len(available_cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return None, None
        
        # Try to match cameras to configured serials
        camera_0_index = None
        camera_1_index = None
        
        for index, serial in available_cameras:
            if serial == CAMERA_0_SERIAL:
                camera_0_index = index
                logger.info(f"✅ Matched Camera 0 ({CAMERA_0_NAME}) to camera index {index}")
            elif serial == CAMERA_1_SERIAL:
                camera_1_index = index
                logger.info(f"✅ Matched Camera 1 ({CAMERA_1_NAME}) to camera index {index}")
        
        if camera_0_index is not None and camera_1_index is not None:
            logger.info("✅ Both cameras detected and matched to serials")
            return camera_0_index, camera_1_index
        else:
            logger.warning("⚠️ Could not match cameras to configured serials")
            # Fallback: use first two available cameras
            if len(available_cameras) >= 2:
                logger.info("🔄 Using first two cameras as fallback")
                return available_cameras[0][0], available_cameras[1][0]
            else:
                logger.error("❌ Not enough cameras available")
                return None, None
                
    except ImportError as e:
        logger.error(f"❌ Picamera2 not available: {e}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Camera detection failed: {e}")
        return None, None

class CameraRecorder:
    """Thread-safe camera recorder for a single camera"""
    
    def __init__(self, camera_index, camera_name, output_path):
        self.camera_index = camera_index
        self.camera_name = camera_name
        self.output_path = output_path
        self.picamera2 = None
        self.encoder = None
        self.recording = False
        self.thread = None
        self.error = None
        self.success = False
        self.retry_count = 0
        self.max_retries = 3
        
        # Set up logging for this camera
        self.log_file = f"/tmp/{camera_name.lower()}_camera_debug.log"
        self.logger = self._setup_camera_logger()
    
    def _setup_camera_logger(self):
        """Set up dedicated logger for this camera"""
        logger = logging.getLogger(f"{self.camera_name.lower()}_camera")
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def initialize_camera(self):
        """Initialize the camera with proper configuration and retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"🔧 Initializing {self.camera_name} camera (index: {self.camera_index}, attempt: {attempt + 1}/{self.max_retries})")
                
                # Create Picamera2 instance using camera index
                self.picamera2 = Picamera2(index=self.camera_index)
                
                # Configure camera
                config = self.picamera2.create_video_configuration(
                    main={"size": (1920, 1080), "format": "YUV420"},
                    controls={
                        "FrameDurationLimits": (33333, 1000000),
                        "ExposureTime": 33333,
                        "AnalogueGain": 1.0,
                        "NoiseReductionMode": 0
                    }
                )
                
                self.picamera2.configure(config)
                self.picamera2.start()
                
                # Create encoder
                from picamera2.encoders import H264Encoder
                self.encoder = H264Encoder(
                    bitrate=6000000,
                    repeat=False,
                    iperiod=30,
                    qp=25
                )
                
                self.logger.info(f"✅ {self.camera_name} camera initialized successfully")
                return True
                
            except Exception as e:
                self.error = str(e)
                self.logger.error(f"❌ {self.camera_name} camera initialization failed (attempt {attempt + 1}): {e}")
                
                # Clean up failed attempt
                if self.picamera2:
                    try:
                        self.picamera2.close()
                        self.picamera2 = None
                    except:
                        pass
                
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        self.logger.error(f"❌ {self.camera_name} camera failed to initialize after {self.max_retries} attempts")
        return False
    
    def start_recording(self):
        """Start recording in a separate thread with health monitoring"""
        if self.thread and self.thread.is_alive():
            self.logger.warning(f"⚠️ {self.camera_name} camera already recording")
            return False
        
        self.thread = threading.Thread(target=self._record_loop)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait a moment and check if thread started successfully
        time.sleep(0.5)
        if not self.thread.is_alive():
            self.logger.error(f"❌ {self.camera_name} camera thread failed to start")
            return False
        
        self.logger.info(f"✅ {self.camera_name} camera recording thread started successfully")
        return True
    
    def _record_loop(self):
        """Main recording loop with enhanced error handling"""
        try:
            if not self.initialize_camera():
                self.logger.error(f"❌ {self.camera_name} camera initialization failed, cannot record")
                return
            
            self.logger.info(f"🎥 Starting {self.camera_name} camera recording")
            self.recording = True
            
            # Start recording
            self.picamera2.start_recording(self.encoder, str(self.output_path))
            
            # Keep recording until stopped with health monitoring
            last_log_time = time.time()
            while self.recording:
                time.sleep(1)
                
                # Log progress every 10 seconds
                current_time = time.time()
                if current_time - last_log_time >= 10:
                    if self.output_path.exists():
                        size = self.output_path.stat().st_size
                        self.logger.info(f"📹 {self.camera_name} recording: {size} bytes")
                        last_log_time = current_time
                    else:
                        self.logger.warning(f"⚠️ {self.camera_name} recording file not found")
                
                # Check if thread is still healthy
                if not self.thread or not self.thread.is_alive():
                    self.logger.error(f"❌ {self.camera_name} recording thread died unexpectedly")
                    break
            
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ {self.camera_name} camera recording error: {e}")
        finally:
            self.stop_recording_internal()
    
    def stop_recording(self):
        """Stop recording with timeout"""
        self.recording = False
        if self.thread:
            self.thread.join(timeout=15)  # Increased timeout for graceful shutdown
            if self.thread.is_alive():
                self.logger.warning(f"⚠️ {self.camera_name} camera thread did not stop gracefully")
    
    def stop_recording_internal(self):
        """Internal method to stop recording"""
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    time.sleep(2)  # Give time for file finalization
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
            
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
                self.success = True
            else:
                self.logger.error(f"❌ {self.camera_name} recording file not found")
                
        except Exception as e:
            self.logger.error(f"❌ Error stopping {self.camera_name} camera: {e}")

    def _get_video_info(self, video_path: Path) -> dict:
        """Get video information using ffprobe"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(video_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"⚠️ Error getting video info for {video_path}: {e}")
            return {}

# Import enhanced merge functionality
try:
    from enhanced_merge import merge_videos_with_retry, MergeResult
    ENHANCED_MERGE = True
    logger.info("✅ Using enhanced merge functionality")
except ImportError:
    ENHANCED_MERGE = False
    logger.warning("⚠️ Enhanced merge not available, using legacy merge")

def merge_videos(video1_path: Path, video2_path: Path, output_path: Path, method: str = 'side_by_side'):
    """Merge two video files using enhanced merge with retry logic"""
    
    if ENHANCED_MERGE:
        # Use enhanced merge with retry logic
        try:
            logger.info(f"🎬 Using enhanced merge for {video1_path.name} and {video2_path.name}")
            result = merge_videos_with_retry(video1_path, video2_path, output_path, method, max_retries=3)
            
            if result.success:
                logger.info(f"✅ Enhanced merge successful: {result.file_size:,} bytes")
                if result.duration:
                    logger.info(f"🎬 Video duration: {result.duration:.2f} seconds")
                return True
            else:
                logger.error(f"❌ Enhanced merge failed: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Enhanced merge error: {e}")
            # Fall back to legacy merge
    
    # Legacy merge method (fallback)
    try:
        # Validate merge method
        if method not in ["side_by_side", "stacked"]:
            logger.warning(f"⚠️ Unknown MERGE_METHOD '{method}', defaulting to side_by_side")
            method = "side_by_side"
        
        # Log file sizes before merge for debugging
        if video1_path.exists():
            size1 = video1_path.stat().st_size
            logger.info(f"📊 {video1_path.name}: {size1:,} bytes")
        else:
            logger.error(f"❌ {video1_path.name} does not exist")
            return False
            
        if video2_path.exists():
            size2 = video2_path.stat().st_size
            logger.info(f"📊 {video2_path.name}: {size2:,} bytes")
        else:
            logger.error(f"❌ {video2_path.name} does not exist")
            return False
        
        # Validate minimum file sizes (500KB each)
        min_size = 500 * 1024  # 500KB
        if size1 < min_size:
            logger.error(f"❌ {video1_path.name} too small: {size1:,} bytes (min: {min_size:,})")
            return False
        if size2 < min_size:
            logger.error(f"❌ {video2_path.name} too small: {size2:,} bytes (min: {min_size:,})")
            return False
        
        if method == 'side_by_side':
            # Side-by-side merge (horizontal stack)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-an',  # 🚫 disable audio to avoid errors
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-movflags', '+faststart',  # ✅ Ensure proper MP4 moov atom
                str(output_path)
            ]
        elif method == 'stacked':
            # Top-bottom merge (vertical stack)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]vstack=inputs=2[v]',
                '-map', '[v]',
                '-an',  # 🚫 disable audio to avoid errors
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-movflags', '+faststart',  # ✅ Ensure proper MP4 moov atom
                str(output_path)
            ]

        logger.info(f"🎬 Merging videos using legacy {method} method...")
        logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"✅ Successfully merged videos: {output_path} ({file_size:,} bytes)")
            
            # ✅ Validate merged file size (should be reasonable)
            min_merged_size = 1024 * 1024  # 1MB minimum
            if file_size < min_merged_size:
                logger.warning(f"⚠️ Merged file seems small: {file_size:,} bytes (expected >{min_merged_size:,})")
            
            # ✅ Validate MP4 structure with ffprobe
            try:
                validate_result = subprocess.run([
                    'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_name,width,height', '-of', 'json',
                    str(output_path)
                ], capture_output=True, text=True, timeout=30)
                
                if validate_result.returncode == 0:
                    logger.info(f"✅ Merged video validation passed")
                    return True
                else:
                    logger.error(f"❌ Merged video validation failed: {validate_result.stderr}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error validating merged video: {e}")
                return False
        else:
            logger.error(f"❌ Failed to merge videos (exit code {result.returncode})")
            logger.error(f"🔧 FFmpeg stderr:\n{result.stderr}")
            logger.error(f"🔧 FFmpeg stdout:\n{result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ FFmpeg merge timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"❌ Error merging videos: {e}")
        return False

class DualRecordingSession:
    """Manages dual camera recording session"""
    
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RECORDINGS_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        
        # Create recordings directory
        try:
            self.date_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created/verified recordings directory: {self.date_folder}")
        except PermissionError as e:
            logger.error(f"❌ Permission denied creating {self.date_folder}: {e}")
            logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create recordings directory {self.date_folder}: {e}")
            raise
        
        # Parse booking times
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        
        # Enhanced file naming with user and camera IDs for traceability
        user_id = booking.get("user_id", "unknown")
        camera_id = booking.get("camera_id", "unknown")
        self.filename_base = f"{self.filename_base}_{user_id}_{camera_id}"
        
        # File paths
        self.camera0_file = self.date_folder / f"{self.filename_base}_{CAMERA_0_NAME}.mp4"
        self.camera1_file = self.date_folder / f"{self.filename_base}_{CAMERA_1_NAME}.mp4"
        self.merged_file = self.date_folder / f"{self.filename_base}_merged.mp4"
        
        # Camera recorders
        self.camera0_recorder = None
        self.camera1_recorder = None
        self.active = False
        self.recording_start_time = None

    def start(self):
        """Start dual camera recording with enhanced error handling"""
        try:
            logger.info(f"🎬 Starting dual camera recording session: {self.filename_base}")
            
            # Detect cameras
            camera0_index, camera1_index = detect_cameras()
            if camera0_index is None or camera1_index is None:
                logger.error("❌ Failed to detect cameras")
                return False
            
            # Create camera recorders
            self.camera0_recorder = CameraRecorder(camera0_index, CAMERA_0_NAME, self.camera0_file)
            self.camera1_recorder = CameraRecorder(camera1_index, CAMERA_1_NAME, self.camera1_file)
            
            # Start recording on both cameras with individual error handling
            logger.info("🎥 Starting camera recordings...")
            
            cam0_started = self.camera0_recorder.start_recording()
            cam1_started = self.camera1_recorder.start_recording()
            
            # Handle partial success scenarios
            if not cam0_started and not cam1_started:
                logger.error("❌ Both cameras failed to start recording")
                return False
            
            if not cam0_started:
                logger.warning("⚠️ Camera 0 failed to start, continuing with Camera 1 only")
                self.camera0_recorder = None
            
            if not cam1_started:
                logger.warning("⚠️ Camera 1 failed to start, continuing with Camera 0 only")
                self.camera1_recorder = None
            
            # Wait a moment and check thread health
            time.sleep(2)
            
            active_cameras = 0
            if self.camera0_recorder and self.camera0_recorder.thread and self.camera0_recorder.thread.is_alive():
                active_cameras += 1
                logger.info("✅ Camera 0 recording thread is healthy")
            else:
                logger.warning("⚠️ Camera 0 recording thread is not healthy")
            
            if self.camera1_recorder and self.camera1_recorder.thread and self.camera1_recorder.thread.is_alive():
                active_cameras += 1
                logger.info("✅ Camera 1 recording thread is healthy")
            else:
                logger.warning("⚠️ Camera 1 recording thread is not healthy")
            
            if active_cameras == 0:
                logger.error("❌ No camera recording threads are healthy")
                return False
            
            self.active = True
            self.recording_start_time = datetime.now(LOCAL_TZ)
            logger.info(f"✅ Dual camera recording started successfully with {active_cameras} active camera(s)")
            
            # Update booking status
            try:
                update_booking_status(self.booking["id"], "Recording")
                logger.info(f"📡 Updated booking status to Recording")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
            # Update camera status
            try:
                supabase.table('cameras').update({
                    'is_recording': True,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'online'
                }).eq('id', CAMERA_ID).execute()
                logger.info(f"📡 Updated camera status")
            except Exception as e:
                logger.error(f"❌ Failed to update camera status: {e}")
            
            set_is_recording(True)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording session: {e}")
            return False

    def stop(self):
        """Stop dual camera recording"""
        logger.info("🛑 Stopping dual camera recording")
        
        try:
            # Stop camera recordings
            if self.camera0_recorder:
                self.camera0_recorder.stop_recording()
            if self.camera1_recorder:
                self.camera1_recorder.stop_recording()
            
            self.active = False
            
            # Wait for files to be finalized
            time.sleep(3)
            
            # Check recording results
            logger.info("🔍 Checking camera recording files...")
            
            cam0_success = self.camera0_recorder.success if self.camera0_recorder else False
            cam1_success = self.camera1_recorder.success if self.camera1_recorder else False
            
            if self.camera0_file.exists():
                cam0_size = self.camera0_file.stat().st_size
                logger.info(f"✅ {CAMERA_0_NAME} recording: {self.camera0_file.name} ({cam0_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_0_NAME} recording file missing: {self.camera0_file}")
            
            if self.camera1_file.exists():
                cam1_size = self.camera1_file.stat().st_size
                logger.info(f"✅ {CAMERA_1_NAME} recording: {self.camera1_file.name} ({cam1_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_1_NAME} recording file missing: {self.camera1_file}")
            
            # Merge videos if both cameras recorded successfully
            if cam0_success and cam1_success:
                logger.info("✅ Both camera recordings completed")
                
                if merge_videos(self.camera0_file, self.camera1_file, self.merged_file, MERGE_METHOD):
                    logger.info(f"✅ Successfully created merged video: {self.merged_file}")
                    
                    # ✅ Validate merged file before creating .done marker
                    if self.merged_file.exists():
                        merged_size = self.merged_file.stat().st_size
                        logger.info(f"📊 Merged file size: {merged_size:,} bytes")
                        
                        # Ensure merged file is substantial (>1MB)
                        if merged_size > 1024 * 1024:
                            # Save metadata first
                            metadata = self.save_metadata()
                            
                            # Trigger auto-upload if enabled
                            if metadata:
                                trigger_upload(self.merged_file, metadata)
                            
                            # ✅ Create .done marker only after validation
                            done_marker = self.merged_file.with_suffix('.done')
                            done_marker.touch()
                            logger.info(f"✅ Created .done marker: {done_marker}")
                            
                            # Clean up individual camera files
                            self.camera0_file.unlink(missing_ok=True)
                            self.camera1_file.unlink(missing_ok=True)
                            logger.info("✅ Cleaned up individual camera files")
                            
                        else:
                            logger.error(f"❌ Merged file too small: {merged_size:,} bytes. Not creating .done marker.")
                            # Create error marker to prevent infinite retries
                            error_marker = self.merged_file.with_suffix('.error')
                            error_marker.touch()
                            logger.error("🔧 Created .error marker due to small merged file")
                    else:
                        logger.error("❌ Merged file not found after successful merge")
                        # Create error marker to prevent infinite retries
                        error_marker = self.merged_file.with_suffix('.error')
                        error_marker.touch()
                        logger.error("🔧 Created .error marker due to missing merged file")
                        
                else:
                    logger.error("❌ Failed to merge videos")
                    # Create error marker to prevent infinite retries
                    error_marker = self.merged_file.with_suffix('.error')
                    error_marker.touch()
                    logger.error("🔧 Created .error marker due to merge failure")
            else:
                logger.warning("⚠️ One or both camera recordings failed")
                # Create error marker to prevent infinite retries
                error_marker = self.merged_file.with_suffix('.error')
                error_marker.touch()
                logger.error("🔧 Created .error marker to prevent infinite retries")
            
            # Update booking status
            try:
                update_booking_status(self.booking["id"], "RecordingFinished")
            except Exception as e:
                logger.error(f"❌ Failed to update booking status: {e}")
            
            # Update camera status
            try:
                supabase.table('cameras').update({
                    'is_recording': False,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'online'
                }).eq('id', CAMERA_ID).execute()
                set_is_recording(False)
            except Exception as e:
                logger.error(f"❌ Failed to update camera status: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error stopping dual recording: {e}")

    def save_metadata(self):
        """Save metadata for the merged recording and return the metadata dict"""
        try:
            metadata_path = self.merged_file.with_suffix(".json")
            metadata = {
                "booking_id": self.booking["id"],
                "user_id": self.booking.get("user_id"),
                "camera_id": self.booking.get("camera_id"),
                "start_time": self.booking["start_time"],
                "end_time": self.booking["end_time"],
                "recording_start": self.recording_start_time.isoformat() if self.recording_start_time else None,
                "recording_end": datetime.now(LOCAL_TZ).isoformat(),
                "file_path": str(self.merged_file),
                "file_size": self.merged_file.stat().st_size if self.merged_file.exists() else 0,
                "camera_0_serial": CAMERA_0_SERIAL,
                "camera_1_serial": CAMERA_1_SERIAL,
                "merge_method": MERGE_METHOD,
                "dual_camera": True
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"📝 Metadata saved to: {metadata_path}")
            return metadata
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")
            return None

def trigger_upload(merged_file: Path, metadata: dict):
    """Trigger immediate upload of the merged video file"""
    try:
        if not AUTO_UPLOAD:
            logger.info("📤 Auto-upload disabled, skipping immediate upload")
            return True
            
        logger.info("📤 Auto-upload enabled, triggering immediate upload...")
        
        # Import upload functionality from video_worker
        try:
            from video_worker import upload_file_chunked, insert_video_metadata
        except ImportError:
            logger.warning("⚠️ video_worker module not available, skipping auto-upload")
            return True
        
        # Generate S3 key
        user_id = metadata.get("user_id")
        date_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        s3_key = f"{user_id}/{date_str}/{merged_file.name}"
        
        # Upload to S3
        s3_url = upload_file_chunked(merged_file, s3_key)
        if s3_url:
            # Update metadata with upload info
            metadata["video_url"] = s3_url
            metadata["uploaded_at"] = datetime.now(LOCAL_TZ).isoformat()
            metadata["storage_path"] = s3_key
            
            # Insert into database
            if insert_video_metadata(metadata):
                logger.info(f"✅ Auto-upload completed successfully: {s3_url}")
                return True
            else:
                logger.error("❌ Failed to insert video metadata")
                return False
        else:
            logger.error("❌ Failed to upload video to S3")
            return False
            
    except Exception as e:
        logger.error(f"❌ Auto-upload error: {e}")
        return False

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    if 'current_session' in globals() and current_session and current_session.active:
        logger.info("🛑 Stopping active recording before exit...")
        try:
            current_session.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping recording during exit: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Import enhanced booking manager
try:
    from booking_manager import BookingManager, BookingStatus, CameraStatus
    ENHANCED_BOOKING_MANAGER = True
    logger.info("✅ Using enhanced booking manager")
except ImportError:
    ENHANCED_BOOKING_MANAGER = False
    logger.warning("⚠️ Enhanced booking manager not available, using legacy mode")

def get_active_booking(bookings):
    """Get the currently active booking with overlap protection"""
    if ENHANCED_BOOKING_MANAGER:
        # Use enhanced booking manager
        try:
            manager = BookingManager(BOOKING_CACHE_FILE, USER_ID, CAMERA_ID)
            active_booking = manager.get_active_booking()
            if active_booking:
                return active_booking.__dict__
        except Exception as e:
            logger.error(f"❌ Error getting active booking from enhanced manager: {e}")
    
    # Fallback to legacy method
    now = datetime.now(LOCAL_TZ)
    for booking in bookings:
        try:
            start_time = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
            end_time = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        except Exception:
            continue
        if booking.get("user_id") == USER_ID and booking.get("camera_id") == CAMERA_ID and start_time <= now <= end_time:
            return booking
    return None

def load_bookings():
    """Load bookings from cache file"""
    if not BOOKING_CACHE_FILE.exists():
        return []
    try:
        with open(BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            # Handle both old and new formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'bookings' in data:
                return data['bookings']
            else:
                return []
    except Exception:
        return []

def validate_camera_setup():
    """Validate camera setup and return detailed information"""
    try:
        from picamera2 import Picamera2
        
        logger.info("🔍 Validating camera setup...")
        
        # Try to detect cameras by attempting to create Picamera2 instances
        max_cameras = 4  # Try up to 4 camera indices
        available_cameras = []
        
        for i in range(max_cameras):
            try:
                # Try to create a Picamera2 instance
                temp_cam = Picamera2(index=i)
                props = temp_cam.camera_properties
                temp_cam.close()
                
                serial = props.get('SerialNumber', f'unknown_{i}')
                logger.info(f"📷 Camera {i}: Serial {serial}")
                available_cameras.append((i, serial))
                
            except Exception as e:
                logger.debug(f"Camera {i} not available: {e}")
                continue
        
        logger.info(f"📷 Found {len(available_cameras)} camera(s)")
        
        if len(available_cameras) < 2:
            logger.error(f"❌ Only {len(available_cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return False
        
        # Test each available camera individually
        for index, serial in available_cameras:
            try:
                logger.info(f"🔧 Testing camera {index}...")
                camera = Picamera2(index=index)
                
                # Test basic configuration
                config = camera.create_video_configuration(
                    main={"size": (1920, 1080), "format": "YUV420"}
                )
                camera.configure(config)
                camera.start()
                camera.stop()
                camera.close()
                
                logger.info(f"✅ Camera {index} (Serial: {serial}) is working correctly")
                
            except Exception as e:
                logger.error(f"❌ Camera {index} test failed: {e}")
                return False
        
        # Check environment variables
        logger.info(f"🔧 Environment configuration:")
        logger.info(f"   CAMERA_0_SERIAL: {CAMERA_0_SERIAL}")
        logger.info(f"   CAMERA_1_SERIAL: {CAMERA_1_SERIAL}")
        logger.info(f"   CAMERA_0_NAME: {CAMERA_0_NAME}")
        logger.info(f"   CAMERA_1_NAME: {CAMERA_1_NAME}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Picamera2 not available: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Camera validation failed: {e}")
        return False

def run_camera_health_check():
    """Run comprehensive camera health check before recording"""
    try:
        logger.info("🔍 Running camera health check...")
        
        # Import camera health checker
        try:
            from camera_health_check import CameraHealthChecker
            checker = CameraHealthChecker()
            
            # Run health check
            success = checker.run_full_health_check({
                "camera_0": CAMERA_0_SERIAL,
                "camera_1": CAMERA_1_SERIAL
            })
            
            if success:
                logger.info("✅ Camera health check passed")
                return True
            else:
                logger.error("❌ Camera health check failed")
                return False
                
        except ImportError as e:
            logger.warning(f"⚠️ Camera health checker not available: {e}")
            logger.info("🔄 Skipping health check, proceeding with basic validation")
            return validate_camera_setup()
        except Exception as e:
            logger.error(f"❌ Camera health check error: {e}")
            logger.info("🔄 Falling back to basic camera validation")
            return validate_camera_setup()
            
    except Exception as e:
        logger.error(f"❌ Error running camera health check: {e}")
        return validate_camera_setup()

def _create_merge_command(video1_path: Path, video2_path: Path, 
                        output_path: Path, method: str = 'side_by_side') -> list:
    """Create FFmpeg merge command with timestamp overlay for debugging"""
    
    # Get video info for optimal settings
    def get_video_info(video_path: Path) -> dict:
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(video_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
        except Exception:
            return {}
    
    info1 = get_video_info(video1_path)
    info2 = get_video_info(video2_path)
    
    # Determine optimal resolution and bitrate
    width1 = height1 = width2 = height2 = 1920
    if info1.get('streams'):
        stream1 = info1['streams'][0]
        width1 = int(stream1.get('width', 1920))
        height1 = int(stream1.get('height', 1080))
    
    if info2.get('streams'):
        stream2 = info2['streams'][0]
        width2 = int(stream2.get('width', 1920))
        height2 = int(stream2.get('height', 1080))
    
    # Use the larger dimensions for output
    output_width = max(width1, width2)
    output_height = max(height1, height2)
    
    # Calculate bitrate (higher for dual camera)
    target_bitrate = "8000k"  # 8 Mbps for dual camera
    
    if method == 'side_by_side':
        # Side-by-side merge with timestamp overlay for debugging
        filter_complex = (
            f'[0:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v1];'
            f'[1:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v2];'
            f'[v1][v2]hstack=inputs=2:shortest=1[v]'
        )
        output_width *= 2  # Double width for side-by-side
    elif method == 'stacked':
        # Top-bottom merge with timestamp overlay
        filter_complex = (
            f'[0:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v1];'
            f'[1:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v2];'
            f'[v1][v2]vstack=inputs=2:shortest=1[v]'
        )
        output_height *= 2  # Double height for stacked
    else:
        # Default to side-by-side with timestamp overlay
        filter_complex = (
            f'[0:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v1];'
            f'[1:v]drawtext=text=\'%{{pts\\:localtime\\:%T}}\':fontsize=24:fontcolor=white:'
            f'x=10:y=10:box=1:boxcolor=black@0.5[v2];'
            f'[v1][v2]hstack=inputs=2:shortest=1[v]'
        )
        output_width *= 2
    
    cmd = [
        'ffmpeg', '-y',  # Overwrite output file
        '-i', str(video1_path),
        '-i', str(video2_path),
        '-filter_complex', filter_complex,
        '-map', '[v]',
        '-an',  # No audio to avoid errors
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Fast encoding
        '-crf', '23',  # Good quality
        '-b:v', target_bitrate,
        '-maxrate', target_bitrate,
        '-bufsize', '16000k',
        '-pix_fmt', 'yuv420p',  # Ensure compatibility
        '-movflags', '+faststart',  # Optimize for streaming
        '-metadata', f'merge_method={method}',
        '-metadata', f'camera1={video1_path.name}',
        '-metadata', f'camera2={video2_path.name}',
        str(output_path)
    ]
    
    return cmd

def main():
    """Main application loop with graceful exit handling"""
    logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
    logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
    logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
    logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
    logger.info(f"🎬 Merge method: {MERGE_METHOD}")
    
    # Run camera health check before starting
    if not run_camera_health_check():
        logger.warning("⚠️ Camera health check failed, but continuing anyway...")
        logger.info("🔄 Will attempt to detect cameras during recording")
    
    # Validate camera setup
    if not validate_camera_setup():
        logger.warning("⚠️ Camera setup validation failed, but continuing anyway...")
        logger.info("🔄 Will attempt to detect cameras during recording")
    
    # Verify recordings directory permissions
    try:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = RECORDINGS_DIR / "test_write.tmp"
        test_file.touch()
        test_file.unlink()
        logger.info(f"✅ Recordings directory is writable: {RECORDINGS_DIR}")
    except PermissionError as e:
        logger.error(f"❌ Permission denied accessing recordings directory: {RECORDINGS_DIR}")
        logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to access recordings directory: {RECORDINGS_DIR} - {e}")
        sys.exit(1)
    
    # Verify camera configuration
    if not CAMERA_0_SERIAL or CAMERA_0_SERIAL == "auto":
        logger.error("❌ CAMERA_0_SERIAL not properly configured")
        sys.exit(1)
    if not CAMERA_1_SERIAL or CAMERA_1_SERIAL == "auto":
        logger.error("❌ CAMERA_1_SERIAL not properly configured")
        sys.exit(1)
    
    logger.info("✅ Camera configuration verified")
    
    current_session = None
    last_health_check = time.time()
    health_check_interval = 300  # Check health every 5 minutes
    
    try:
        while True:
            try:
                # Periodic health monitoring
                current_time = time.time()
                if current_time - last_health_check >= health_check_interval:
                    # Simple health check - log system status
                    try:
                        disk_usage = psutil.disk_usage('/')
                        logger.info(f"📊 Health check - Disk usage: {disk_usage.percent:.1f}% used, {disk_usage.free / (1024**3):.1f} GB free")
                    except Exception as e:
                        logger.warning(f"⚠️ Health check failed: {e}")
                    last_health_check = current_time
                
                bookings = load_bookings()
                now = datetime.now(LOCAL_TZ)
                active_booking = get_active_booking(bookings)
                
                if current_session:
                    end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
                    # Add overlap protection: only stop if end time has passed AND session is active
                    if now > end_time and current_session.active:
                        logger.info(f"🛑 Booking ended, stopping recording")
                        current_session.stop()
                        current_session = None
                        
                if not current_session and active_booking:
                    # Additional overlap protection: ensure no active session before starting new one
                    if current_session is None or not current_session.active:
                        logger.info(f"🎬 Starting recording for booking: {active_booking['id']}")
                        current_session = DualRecordingSession(active_booking)
                        if not current_session.start():
                            logger.error(f"❌ Failed to start recording session")
                            current_session = None
                        
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                import traceback
                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error in main loop: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
    finally:
        # Ensure graceful cleanup
        logger.info("🛑 Performing graceful shutdown...")
        if current_session and current_session.active:
            logger.info("🛑 Stopping active recording before exit...")
            try:
                current_session.stop()
            except Exception as e:
                logger.error(f"❌ Error stopping recording during exit: {e}")
        
        # Update final status
        try:
            set_is_recording(False)
            logger.info("✅ Shutdown completed successfully")
        except Exception as e:
            logger.error(f"❌ Error during final status update: {e}")
        
        sys.exit(0)

if __name__ == "__main__":
    main() 