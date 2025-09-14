#!/usr/bin/env python3
"""
EZREC Dual Camera Recorder - Clean Architecture
- Uses direct camera detection for reliable camera access
- Records from both cameras simultaneously using threads
- Merges recordings using FFmpeg
- Robust error handling and logging
- USER PREFERENCE: Camera must be properly released to prevent stuck processes
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

current_session = None


# Monkey patch Picamera2 to fix _preview attribute error
try:
    from picamera2 import Picamera2
    import libcamera
    
    # Store the original close method
    original_close = Picamera2.close
    
    def safe_close(self):
        """Safe close method that handles missing _preview attribute"""
        try:
            if hasattr(self, '_preview'):
                return original_close(self)
            else:
                # If _preview doesn't exist, just clean up what we can
                if hasattr(self, '_camera'):
                    self._camera = None
                if hasattr(self, '_encoder'):
                    self._encoder = None
        except Exception as e:
            # Silently ignore errors during cleanup
            pass
    
    # Replace the close method
    Picamera2.close = safe_close
    
    # Also patch the __del__ method to be safer
    original_del = Picamera2.__del__
    
    def safe_del(self):
        """Safe destructor that handles missing attributes"""
        try:
            if hasattr(self, '_preview'):
                return original_del(self)
        except Exception:
            # Silently ignore errors during destruction
            pass
    
    Picamera2.__del__ = safe_del
    
except ImportError:
    pass  # Picamera2 not available, continue without it

# Timezone configuration
TIMEZONE = pytz.timezone("America/New_York")  # Adjust as needed

# 🔧 Ensure API utils can be imported
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

try:
    from booking_utils import update_booking_status
except ImportError:
    def update_booking_status(booking_id: str, status: str) -> bool:
        """Fallback function if booking_utils is not available"""
        print(f"⚠️ update_booking_status not available for booking {booking_id}")
        return False

# Load environment
dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

# Environment variables
TIMEZONE_NAME = os.getenv("LOCAL_TIMEZONE") or os.getenv("SYSTEM_TIMEZONE") or "America/New_York"
LOCAL_TZ = pytz.timezone(TIMEZONE_NAME)

# Camera rotation configuration
CAMERA_ROTATION = int(os.getenv("CAMERA_ROTATION", "0"))  # 0 degrees by default (rotation handled in merge)

# Validate rotation value (only 0, 90, 180, 270 are valid for hardware rotation)
if CAMERA_ROTATION not in [0, 90, 180, 270]:
    print(f"⚠️ Invalid CAMERA_ROTATION={CAMERA_ROTATION}. Using 0 degrees instead.")
    CAMERA_ROTATION = 0

# Enhanced merge rotation (for 45-degree support)
ENHANCED_MERGE_ROTATE_DEGREES = float(os.getenv("ENHANCED_MERGE_ROTATE_DEGREES", "45.0"))  # 45 degrees for seamless merge

# Merge configuration
MERGE_METHOD = os.getenv("MERGE_METHOD", "side_by_side")
ENABLE_DISTORTION_CORRECTION = os.getenv("ENABLE_DISTORTION_CORRECTION", "true").lower() == "true"

REQUIRED_KEYS = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "USER_ID", "CAMERA_ID"]
missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print(f"❌ Missing required environment variables: {missing}")
    sys.exit(1)

# Configuration constants as per integration plan
CAM_IDS = [0, 1]
RESOLUTION = (1920, 1080)
FRAMERATE = 30
BITRATE = 6_000_000
OUTPUT_DIR = Path("/opt/ezrec-backend/recordings")

USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Debug: Check if the key is loaded correctly
print(f"🔍 Debug: SUPABASE_SERVICE_ROLE_KEY loaded: {'YES' if SUPABASE_KEY else 'NO'}")
if SUPABASE_KEY:
    print(f"🔍 Debug: Key starts with: {SUPABASE_KEY[:20]}...")
    print(f"🔍 Debug: Key length: {len(SUPABASE_KEY)}")
else:
    print(f"🔍 Debug: SUPABASE_SERVICE_ROLE_KEY is None or empty")
BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
RECORDINGS_DIR = Path('/opt/ezrec-backend/recordings/')
LOG_FILE = Path('/opt/ezrec-backend/logs/dual_recorder.log')
CHECK_INTERVAL = int(os.getenv('BOOKING_CHECK_INTERVAL', '5'))  # Check every 5 seconds

# Camera configuration
CAMERA_0_SERIAL = os.getenv('CAMERA_0_SERIAL', '88000')
CAMERA_1_SERIAL = os.getenv('CAMERA_1_SERIAL', '80000')
CAMERA_0_NAME = os.getenv('CAMERA_0_NAME', 'left')
CAMERA_1_NAME = os.getenv('CAMERA_1_NAME', 'right')
DUAL_CAMERA_MODE = os.getenv('DUAL_CAMERA_MODE', 'true').lower() == 'true'
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

# Initialize Supabase client with proper error handling
try:
    # Use SERVICE_ROLE_KEY for write operations (updates to cameras table)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase client initialized successfully with service role key")
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize Supabase client: {e}")
    logger.warning("⚠️ System will work in local mode only")
    supabase = None

logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
logger.info(f"🎬 Merge method: {MERGE_METHOD}")

# Global flag to prevent recursion
_status_update_in_progress = False

def set_is_recording(value: bool):
    """Update recording status in status.json with recursion protection"""
    global _status_update_in_progress
    
    if _status_update_in_progress:
        logger.warning("⚠️ Status update already in progress, skipping to prevent recursion")
        return
    
    _status_update_in_progress = True
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
        status["last_update"] = datetime.now().isoformat()
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
        logger.debug(f"📝 Updated recording status: {value}")
    except Exception as e:
        logger.error(f"❌ Failed to update recording status: {e}")
    finally:
        _status_update_in_progress = False

def emit_event(event_type: str, booking_id: str, **kwargs):
    """Emit an event file for inter-service communication"""
    try:
        events_dir = Path("/opt/ezrec-backend/events")
        events_dir.mkdir(parents=True, exist_ok=True)
        
        event_file = events_dir / f"{event_type}_{booking_id}.event"
        
        # Create event with metadata
        event_data = {
            "event_type": event_type,
            "booking_id": booking_id,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        with open(event_file, 'w') as f:
            json.dump(event_data, f, indent=2)
        
        logger.info(f"📤 Emitted {event_type} event for booking {booking_id}")
        return event_file
    except Exception as e:
        logger.error(f"❌ Failed to emit {event_type} event: {e}")
        return None

def detect_cameras():
    """Detect available cameras by trying to access them directly and return camera indices"""
    try:
        from picamera2 import Picamera2
        
        logger.info("🔍 Detecting cameras by direct access...")
        
        # Try to detect cameras by attempting to create Picamera2 instances with explicit indices
        available_cameras = []
        
        # Try to detect multiple cameras by attempting different indices
        for i in range(4):  # Try indices 0-3
            try:
                # Use explicit camera index to properly detect distinct cameras
                temp_cam = Picamera2(camera_num=i)
                
                # Try to get camera properties safely
                try:
                    props = temp_cam.camera_properties
                    serial = props.get('SerialNumber', f'unknown_{i}')
                except AttributeError:
                    # Fallback if camera_properties is not available
                    serial = f'unknown_{i}'
                
                temp_cam.close()
                logger.info(f"📷 Camera {i}: Serial {serial}")
                available_cameras.append((i, serial))
                
            except Exception as e:
                logger.debug(f"Camera {i} not available: {e}")
                # Continue trying other indices instead of breaking
                continue
        
        # Check if we have multiple cameras available
        if len(available_cameras) >= 2:
            # We have multiple cameras - use them separately
            camera_0_index = available_cameras[0][0]
            camera_1_index = available_cameras[1][0]
            logger.info(f"✅ Using separate cameras: Camera 0 (index {camera_0_index}) and Camera 1 (index {camera_1_index})")
        elif len(available_cameras) == 1:
            # Only one camera available - use single camera mode
            logger.warning(f"⚠️ Only 1 camera detected. Using single camera mode.")
            camera_0_index = available_cameras[0][0]
            camera_1_index = None  # No second camera
            logger.info(f"✅ Single camera mode: Camera 0 (index {camera_0_index})")
        else:
            logger.error(f"❌ No cameras detected")
            return None, None
        
        return camera_0_index, camera_1_index
                
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
                self.logger.info(f"🔧 Initializing {self.camera_name} camera (index {self.camera_index}, attempt: {attempt + 1}/{self.max_retries})")
                
                # Create Picamera2 instance with explicit camera index
                self.picamera2 = Picamera2(camera_num=self.camera_index)
                
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
                
                # Apply rotation if needed (using controls instead of transform)
                if CAMERA_ROTATION != 0:
                    config["controls"]["Rotation"] = CAMERA_ROTATION
                
                self.picamera2.configure(config)
                self.picamera2.start()
                
                # Create encoder with proper MP4 compatibility (matching working test script)
                from picamera2.encoders import H264Encoder
                self.encoder = H264Encoder(bitrate=6000000)
                
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
        
    def start_recording(self):
        """Start recording in a separate thread with health monitoring"""
        if self.recording:
            self.logger.warning(f"⚠️ {self.camera_name} camera already recording")
            return False

        def run_and_update_thread():
            self.thread = threading.current_thread()
            self._record_loop()

        self.thread = threading.Thread(target=run_and_update_thread, name=f"{self.camera_name}_recorder")
        self.thread.daemon = True
        self.thread.start()

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
            
            # Start recording with proper MP4 configuration
            try:
                self.picamera2.start_recording(self.encoder, str(self.output_path))
            except Exception as e:
                if "GLOBAL_HEADER" in str(e):
                    # Try alternative encoder configuration (matching working test script)
                    self.logger.warning(f"⚠️ GLOBAL_HEADER error, trying alternative encoder config")
                    from picamera2.encoders import H264Encoder
                    self.encoder = H264Encoder(bitrate=4000000)
                    self.picamera2.start_recording(self.encoder, str(self.output_path))
                else:
                    raise e
            
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
        """Stop recording with timeout and ensure proper cleanup"""
        self.recording = False
        
        # Force stop the camera hardware immediately
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    # Give more time for proper MP4 finalization
                    time.sleep(5)  # Increased from 2s to 5s for better MP4 finalization
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
                self.logger.info(f"✅ {self.camera_name} camera hardware released")
        except Exception as e:
            self.logger.error(f"❌ Error force-stopping {self.camera_name} camera: {e}")
        
        if self.thread:
            # Wait for thread to finish with timeout
            self.thread.join(timeout=15)  # Increased timeout for better cleanup
            
            if self.thread.is_alive():
                self.logger.warning(f"⚠️ {self.camera_name} camera thread did not stop gracefully within timeout")
                # Force kill the thread if it's still alive
                try:
                    import _thread
                    _thread.interrupt_main()
                except:
                    pass
            else:
                self.logger.info(f"✅ {self.camera_name} camera thread stopped gracefully")
        
        # Final cleanup check and MP4 validation
        if self.output_path.exists():
            size = self.output_path.stat().st_size
            self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
            
            # Validate MP4 file structure
            if self._validate_mp4_file():
                self.success = True
                self.logger.info(f"✅ {self.camera_name} MP4 file validated successfully")
            else:
                self.logger.error(f"❌ {self.camera_name} MP4 file validation failed")
                self.success = False
        else:
            self.logger.error(f"❌ {self.camera_name} recording file not found")
    
    def _validate_mp4_file(self):
        """Validate that the MP4 file is properly finalized"""
        try:
            if not self.output_path.exists():
                return False
            
            # Check file size (minimum 100KB)
            if self.output_path.stat().st_size < 100 * 1024:
                self.logger.warning(f"⚠️ {self.camera_name} file too small for valid MP4")
                return False
            
            # Use ffprobe to check if it's a valid MP4
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', str(self.output_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.info(f"✅ {self.camera_name} MP4 file is valid")
                return True
            else:
                self.logger.error(f"❌ {self.camera_name} MP4 validation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ {self.camera_name} MP4 validation error: {e}")
            return False
    
    def stop_recording_internal(self):
        """Internal method to stop recording with enhanced cleanup"""
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    time.sleep(5)  # Increased time for proper MP4 finalization
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
                self.logger.info(f"✅ {self.camera_name} camera hardware released")
            
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
                
                # Validate MP4 file structure
                if self._validate_mp4_file():
                    self.success = True
                    self.logger.info(f"✅ {self.camera_name} MP4 file validated successfully")
                else:
                    self.logger.error(f"❌ {self.camera_name} MP4 file validation failed")
                    self.success = False
            else:
                self.logger.error(f"❌ {self.camera_name} recording file not found")
                
        except Exception as e:
            self.logger.error(f"❌ Error stopping {self.camera_name} camera: {e}")
            # Force cleanup even on error
            try:
                if self.picamera2:
                    self.picamera2.close()
                    self.picamera2 = None
            except:
                pass

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
            logger.info(f"🔧 Merge method: {method}")
            logger.info(f"🔧 Input rotation: {ENHANCED_MERGE_ROTATE_DEGREES}°")
            logger.info(f"🔧 Distortion correction: {'enabled' if ENABLE_DISTORTION_CORRECTION else 'disabled'}")
            
            # Create enhanced merger with rotation and distortion correction setting
            from enhanced_merge import EnhancedVideoMerger
            merger = EnhancedVideoMerger(
                max_retries=3,
                timeout=300,
                feather_width=100,
                edge_trim=5,
                enable_distortion_correction=ENABLE_DISTORTION_CORRECTION,
                input_rotate_degrees=ENHANCED_MERGE_ROTATE_DEGREES
            )
            
            result = merger.merge_videos(video1_path, video2_path, output_path, method)
            
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
            # Advanced feathered blend merge for seamless wide-angle effect
            # Creates 100px feathered overlap with linear alpha gradient
            filter_complex = (
                '[0:v]crop=w=in_w-100:h=in_h:x=0:y=0[left]; '
                '[0:v]crop=w=100:h=in_h:x=in_w-100:y=0[overlapL]; '
                '[1:v]crop=w=100:h=in_h:x=0:y=0[overlapR]; '
                '[1:v]crop=w=in_w-100:h=in_h:x=100:y=0[right]; '
                '[overlapL][overlapR]blend=all_expr=\'A*(1-x/w)+B*(x/w)\'[blended]; '
                '[left][blended][right]hstack=inputs=3,format=yuv420p[out]'
            )
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264', 
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                str(output_path)
            ]
        elif method == 'stacked':
            # Top-bottom merge with 100px feathered blend
            filter_complex = (
                '[0:v]crop=w=in_w:h=in_h-100:x=0:y=0[top]; '
                '[0:v]crop=w=in_w:h=100:x=0:y=in_h-100[overlapT]; '
                '[1:v]crop=w=in_w:h=100:x=0:y=0[overlapB]; '
                '[1:v]crop=w=in_w:h=in_h-100:x=0:y=100[bottom]; '
                '[overlapT][overlapB]blend=all_expr=\'A*(1-y/h)+B*(y/h)\'[blended]; '
                '[top][blended][bottom]vstack=inputs=3,format=yuv420p[out]'
            )
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                str(output_path)
            ]

        logger.info(f"🎬 Merging videos using legacy {method} method...")
        logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"✅ Successfully merged videos: {output_path} ({file_size:,} bytes)")
            
            # Log FFmpeg stderr for debugging (even on success)
            if result.stderr:
                logger.info(f"📋 FFmpeg stderr: {result.stderr}")
            
            # ✅ Validate merged file size (should be reasonable)
            min_merged_size = 1024 * 1024  # 1MB minimum
            if file_size < min_merged_size:
                logger.warning(f"⚠️ Merged file seems small: {file_size:,} bytes (expected >{min_merged_size:,})")
            
            # ✅ Validate duration to ensure no truncation
            try:
                duration_result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', str(output_path)
                ], capture_output=True, text=True, timeout=30)
                
                if duration_result.returncode == 0:
                    merged_duration = float(duration_result.stdout.strip())
                    logger.info(f"📊 Merged video duration: {merged_duration:.2f} seconds")
                    
                    # Check if duration is reasonable (should be close to input durations)
                    # Get input durations for comparison
                    try:
                        dur1_result = subprocess.run([
                            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                            '-of', 'csv=p=0', str(video1_path)
                        ], capture_output=True, text=True, timeout=30)
                        dur2_result = subprocess.run([
                            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                            '-of', 'csv=p=0', str(video2_path)
                        ], capture_output=True, text=True, timeout=30)
                        
                        if dur1_result.returncode == 0 and dur2_result.returncode == 0:
                            dur1 = float(dur1_result.stdout.strip())
                            dur2 = float(dur2_result.stdout.strip())
                            expected_duration = max(dur1, dur2)  # Should match the longer input
                            
                            logger.info(f"📊 Input durations: {dur1:.2f}s, {dur2:.2f}s")
                            logger.info(f"📊 Expected merged duration: {expected_duration:.2f}s")
                            
                            if abs(merged_duration - expected_duration) > 2.0:
                                logger.warning(f"⚠️ Duration mismatch! Expected ~{expected_duration:.2f}s, got {merged_duration:.2f}s")
                            else:
                                logger.info(f"✅ Duration validation passed")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not validate input durations: {e}")
                else:
                    logger.warning(f"⚠️ Could not get merged video duration: {duration_result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ Duration validation error: {e}")
            
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
                    logger.warning(f"⚠️ Merged video validation failed: {validate_result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ Could not validate merged video: {e}")
            
            return True
        else:
            logger.error(f"❌ Merge failed with return code: {result.returncode}")
            logger.error(f"❌ FFmpeg stderr: {result.stderr}")
            logger.error(f"❌ FFmpeg stdout: {result.stdout}")
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
            if camera0_index is None:
                logger.error("❌ Failed to detect cameras")
                return False
            
            # Create camera recorders based on available cameras
            self.camera0_recorder = CameraRecorder(camera0_index, CAMERA_0_NAME, self.camera0_file)
            
            if camera1_index is not None:
                self.camera1_recorder = CameraRecorder(camera1_index, CAMERA_1_NAME, self.camera1_file)
                logger.info("🎥 Starting dual camera recordings...")
            else:
                self.camera1_recorder = None
                logger.info("🎥 Starting single camera recording...")
            
            # Start recording on available cameras SIMULTANEOUSLY
            logger.info("🎬 Starting both cameras simultaneously...")
            
            # Start both camera threads at the same time
            if self.camera0_recorder:
                self.camera0_recorder.thread = threading.Thread(target=self.camera0_recorder._record_loop)
                self.camera0_recorder.thread.daemon = True
                self.camera0_recorder.thread.start()
            
            if self.camera1_recorder:
                self.camera1_recorder.thread = threading.Thread(target=self.camera1_recorder._record_loop)
                self.camera1_recorder.thread.daemon = True
                self.camera1_recorder.thread.start()
            
            # Wait for both cameras to initialize and start recording
            time.sleep(3)  # Give both cameras time to initialize
            
            # Check if both cameras started successfully
            cam0_started = (self.camera0_recorder and self.camera0_recorder.thread and 
                           self.camera0_recorder.thread.is_alive() and 
                           self.camera0_recorder.recording)
            
            cam1_started = (self.camera1_recorder and self.camera1_recorder.thread and 
                           self.camera1_recorder.thread.is_alive() and 
                           self.camera1_recorder.recording)
            
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
        """Stop dual camera recording with enhanced cleanup"""
        logger.info("🛑 Stopping dual camera recording")
        
        try:
            # Stop camera recordings with proper cleanup
            if self.camera0_recorder:
                logger.info("🛑 Stopping camera 0 recording...")
                self.camera0_recorder.stop_recording()
            if self.camera1_recorder:
                logger.info("🛑 Stopping camera 1 recording...")
                self.camera1_recorder.stop_recording()
            else:
                logger.info("🛑 Single camera mode - only camera 0 was recording")
            
            self.active = False
            
            # Wait for files to be finalized
            time.sleep(3)
            
            # Force cleanup any remaining camera resources
            try:
                import subprocess
                # Kill any remaining camera processes
                subprocess.run(['pkill', '-f', 'picamera2'], capture_output=True, timeout=5)
                logger.info("✅ Forced cleanup of any remaining camera processes")
            except Exception as e:
                logger.warning(f"⚠️ Error during forced cleanup: {e}")
            
            # Check recording results
            logger.info("🔍 Checking camera recording files...")
            
            cam0_success = self.camera0_recorder.success if self.camera0_recorder else False
            cam1_success = self.camera1_recorder.success if self.camera1_recorder else False
            
            # Determine recording mode
            dual_camera_mode = self.camera1_recorder is not None
            logger.info(f"📊 Recording mode: {'Dual camera' if dual_camera_mode else 'Single camera'}")
            
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
            
            # Handle different recording scenarios
            if cam0_success and cam1_success:
                # Both cameras recorded successfully - merge them
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
                            # Emit upload trigger event for video_worker instead of direct upload
                            upload_event_file = emit_event("upload_pending", self.booking["id"], merged=str(self.merged_file))
                            if upload_event_file:
                                logger.info(f"📤 Upload trigger emitted: {upload_event_file}")
                            else:
                                logger.warning(f"⚠️ Failed to emit upload_pending event")
                            
                            # ✅ Create .done marker only after validation
                            done_marker = self.merged_file.with_suffix('.done')
                            done_marker.touch()
                            logger.info(f"✅ Created .done marker: {done_marker}")
                            
                            # Emit recording_complete event as per integration plan
                            emit_event("recording_complete", self.booking["id"], 
                                     out0=str(self.camera0_file), 
                                     out1=str(self.camera1_file),
                                     merged=str(self.merged_file))
                            
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
                    
            elif cam0_success and not cam1_success:
                # Only camera 0 recorded successfully - use it as the merged file
                logger.info("⚠️ Only camera 0 recorded successfully, using it as merged video")
                
                try:
                    # Copy the single camera recording as the merged file
                    import shutil
                    shutil.copy2(self.camera0_file, self.merged_file)
                    
                    if self.merged_file.exists():
                        merged_size = self.merged_file.stat().st_size
                        logger.info(f"✅ Created single camera merged video: {self.merged_file.name} ({merged_size:,} bytes)")
                        
                        # Save metadata first
                        metadata = self.save_metadata()
                        
                        # Trigger auto-upload if enabled
                        if metadata:
                            trigger_upload(self.merged_file, metadata)
                        
                        # Create .done marker
                        done_marker = self.merged_file.with_suffix('.done')
                        done_marker.touch()
                        logger.info(f"✅ Created .done marker: {done_marker}")
                        
                        # Emit recording_complete event for single camera (cam0 only)
                        emit_event("recording_complete", self.booking["id"], 
                                 out0=str(self.camera0_file), 
                                 out1=None,
                                 merged=str(self.merged_file))
                        
                        # Clean up individual camera file
                        self.camera0_file.unlink(missing_ok=True)
                        logger.info("✅ Cleaned up individual camera file")
                        
                    else:
                        logger.error("❌ Failed to create single camera merged file")
                        error_marker = self.merged_file.with_suffix('.error')
                        error_marker.touch()
                        logger.error("🔧 Created .error marker due to copy failure")
                        
                except Exception as e:
                    logger.error(f"❌ Error creating single camera merged file: {e}")
                    error_marker = self.merged_file.with_suffix('.error')
                    error_marker.touch()
                    logger.error("🔧 Created .error marker due to copy error")
                    
            elif not cam0_success and cam1_success:
                # Only camera 1 recorded successfully - use it as the merged file
                logger.info("⚠️ Only camera 1 recorded successfully, using it as merged video")
                
                try:
                    # Copy the single camera recording as the merged file
                    import shutil
                    shutil.copy2(self.camera1_file, self.merged_file)
                    
                    if self.merged_file.exists():
                        merged_size = self.merged_file.stat().st_size
                        logger.info(f"✅ Created single camera merged video: {self.merged_file.name} ({merged_size:,} bytes)")
                        
                        # Save metadata first
                        metadata = self.save_metadata()
                        
                        # Trigger auto-upload if enabled
                        if metadata:
                            trigger_upload(self.merged_file, metadata)
                        
                        # Create .done marker
                        done_marker = self.merged_file.with_suffix('.done')
                        done_marker.touch()
                        logger.info(f"✅ Created .done marker: {done_marker}")
                        
                        # Emit recording_complete event for single camera (cam1 only)
                        emit_event("recording_complete", self.booking["id"], 
                                 out0=None, 
                                 out1=str(self.camera1_file),
                                 merged=str(self.merged_file))
                        
                        # Clean up individual camera file
                        self.camera1_file.unlink(missing_ok=True)
                        logger.info("✅ Cleaned up individual camera file")
                        
                    else:
                        logger.error("❌ Failed to create single camera merged file")
                        error_marker = self.merged_file.with_suffix('.error')
                        error_marker.touch()
                        logger.error("🔧 Created .error marker due to copy failure")
                        
                except Exception as e:
                    logger.error(f"❌ Error creating single camera merged file: {e}")
                    error_marker = self.merged_file.with_suffix('.error')
                    error_marker.touch()
                    logger.error("🔧 Created .error marker due to copy error")
                    
            else:
                logger.error("❌ Both camera recordings failed")
                # Create error marker to prevent infinite retries
                error_marker = self.merged_file.with_suffix('.error')
                error_marker.touch()
                logger.error("🔧 Created .error marker due to both cameras failing")
            
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
    """Handle graceful shutdown with enhanced camera cleanup"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    
    # Stop active recording session
    if 'current_session' in globals() and current_session and current_session.active:
        logger.info("🛑 Stopping active recording before exit...")
        try:
            current_session.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping recording during exit: {e}")
    
    # Force cleanup any remaining camera resources
    try:
        import subprocess
        logger.info("🛑 Force cleaning up camera resources...")
        subprocess.run(['pkill', '-f', 'picamera2'], capture_output=True, timeout=5)
        subprocess.run(['pkill', '-f', 'dual_recorder'], capture_output=True, timeout=5)
        logger.info("✅ Camera cleanup completed")
    except Exception as e:
        logger.warning(f"⚠️ Error during camera cleanup: {e}")
    
    # Update final status
    try:
        set_is_recording(False)
    except Exception as e:
        logger.error(f"❌ Error updating final status: {e}")
    
    # Release /dev/video* devices if stuck (edge case cleanup)
    try:
        subprocess.run(['fuser', '-k', '/dev/video0'], capture_output=True)
        subprocess.run(['fuser', '-k', '/dev/video1'], capture_output=True)
        logger.info("✅ Force-released /dev/video* devices")
    except Exception as e:
        logger.warning(f"⚠️ Could not release video devices: {e}")
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
    logger.info(f"🔍 Checking {len(bookings)} bookings at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"🔍 Looking for user_id: {USER_ID}, camera_id: {CAMERA_ID}")
    
    for i, booking in enumerate(bookings):
        try:
            start_time = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
            end_time = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
            booking_user_id = booking.get("user_id")
            booking_camera_id = booking.get("camera_id")
            
            logger.info(f"🔍 Booking {i}: {booking.get('id', 'unknown')}")
            logger.info(f"   User ID: {booking_user_id} (expected: {USER_ID})")
            logger.info(f"   Camera ID: {booking_camera_id} (expected: {CAMERA_ID})")
            logger.info(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"   Now: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Check if booking matches our criteria
            user_match = booking_user_id == USER_ID
            camera_match = booking_camera_id == CAMERA_ID
            time_match = start_time <= now <= end_time
            
            logger.info(f"   User match: {user_match}, Camera match: {camera_match}, Time match: {time_match}")
            
            if user_match and camera_match and time_match:
                logger.info(f"✅ Found active booking: {booking.get('id', 'unknown')}")
                return booking
                
        except Exception as e:
            logger.error(f"❌ Error processing booking {i}: {e}")
            continue
    
    logger.info("❌ No active booking found")
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
        available_cameras = []
        
        # Try to create a Picamera2 instance (auto-detects first camera)
        try:
            temp_cam = Picamera2(camera_num=0)  # Use explicit camera index
            
            # Try to get camera properties safely
            try:
                props = temp_cam.camera_properties
                serial = props.get('SerialNumber', 'unknown_0')
            except AttributeError:
                # Fallback if camera_properties is not available
                serial = 'unknown_0'
            
            temp_cam.close()
            logger.info(f"📷 Camera 0: Serial {serial}")
            available_cameras.append((0, serial))
            
        except Exception as e:
            logger.debug(f"Camera 0 not available: {e}")
        
        # For dual camera setup, we'll use the same camera twice for testing
        if len(available_cameras) > 0:
            logger.info(f"📷 Camera 1: Using same camera for dual setup")
            available_cameras.append((1, available_cameras[0][1]))
        
        logger.info(f"📷 Found {len(available_cameras)} camera(s)")
        
        if len(available_cameras) < 2:
            logger.error(f"❌ Only {len(available_cameras)} camera(s) detected. Need at least 2 for dual recording.")
            return False
        
        # Test the available camera
        for index, serial in available_cameras:
            try:
                logger.info(f"🔧 Testing camera {index}...")
                camera = Picamera2(camera_num=index)  # Use explicit camera index
                
                # Test basic configuration with error handling
                try:
                    config = camera.create_video_configuration(
                        main={"size": (1920, 1080), "format": "YUV420"}
                    )
                    camera.configure(config)
                    camera.start()
                    camera.stop()
                    camera.close()
                    logger.info(f"✅ Camera {index} (Serial: {serial}) is working correctly")
                except AttributeError as attr_e:
                    # Handle _preview attribute error
                    logger.warning(f"⚠️ Camera {index} has compatibility issues: {attr_e}")
                    camera.close()
                    logger.info(f"✅ Camera {index} (Serial: {serial}) - basic compatibility OK")
                except Exception as config_e:
                    logger.error(f"❌ Camera {index} configuration failed: {config_e}")
                    camera.close()
                    return False
                
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
    """Create FFmpeg merge command with FIXED crop width calculations"""
    
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
    
    # FIXED: Work only with per-source dimensions
    output_height = max(height1, height2)
    feather_width = 100  # Fixed feather width
    edge_trim = 5  # Fixed edge trim
    
    # Calculate visible (non-feather) areas for each source
    left_visible = width1 - feather_width
    right_visible = width2 - feather_width
    
    # Validate crop dimensions to prevent FFmpeg errors
    for name, w, max_w in [("left_visible", left_visible, width1),
                          ("right_visible", right_visible, width2)]:
        if w <= 0 or w > max_w:
            raise ValueError(f"{name} width={w} invalid for source dimensions (max: {max_w})")
    
    # Calculate bitrate (higher for dual camera)
    target_bitrate = "8000k"  # 8 Mbps for dual camera
    
    logger.info(f"🎨 Using feathered blend merge:")
    logger.info(f"   - Source dimensions: {width1}x{height1}, {width2}x{height2}")
    logger.info(f"   - Feather width: {feather_width}px")
    logger.info(f"   - Edge trim: {edge_trim}px")
    logger.info(f"   - Method: {method}")
    logger.info(f"   - Left visible: {left_visible}px, Right visible: {right_visible}px")
    
    if method == 'side_by_side':
        # FIXED: Advanced feathered blend merge with correct crop calculations
        filter_complex = (
            f'[0:v]crop=w={left_visible - edge_trim}:h={output_height}:x=0:y=0[left]; '
            f'[0:v]crop=w={feather_width}:h={output_height}:x={left_visible - edge_trim}:y=0[overlapL]; '
            f'[1:v]crop=w={feather_width}:h={output_height}:x=0:y=0[overlapR]; '
            f'[1:v]crop=w={right_visible - edge_trim}:h={output_height}:x={feather_width + edge_trim}:y=0[right]; '
            f'[overlapL][overlapR]blend=all_expr=\'A*(1-x/w)+B*(x/w)\'[blended]; '
            f'[left][blended][right]hstack=inputs=3,format=yuv420p[v]'
        )
        # Calculate final output width correctly
        final_width = (left_visible - edge_trim) + feather_width + (right_visible - edge_trim)
    elif method == 'stacked':
        # FIXED: Top-bottom merge with correct crop calculations
        top_visible = height1 - feather_width
        bottom_visible = height2 - feather_width
        
        # Validate vertical crop dimensions
        for name, h, max_h in [("top_visible", top_visible, height1),
                              ("bottom_visible", bottom_visible, height2)]:
            if h <= 0 or h > max_h:
                raise ValueError(f"{name} height={h} invalid for source dimensions (max: {max_h})")
        
        filter_complex = (
            f'[0:v]crop=w={width1}:h={top_visible - edge_trim}:x=0:y=0[top]; '
            f'[0:v]crop=w={width1}:h={feather_width}:x=0:y={top_visible - edge_trim}[overlapT]; '
            f'[1:v]crop=w={width2}:h={feather_width}:x=0:y=0[overlapB]; '
            f'[1:v]crop=w={width2}:h={bottom_visible - edge_trim}:x=0:y={feather_width + edge_trim}[bottom]; '
            f'[overlapT][overlapB]blend=all_expr=\'A*(1-y/h)+B*(y/h)\'[blended]; '
            f'[top][blended][bottom]vstack=inputs=3,format=yuv420p[v]'
        )
        # Calculate final output height correctly
        final_height = (top_visible - edge_trim) + feather_width + (bottom_visible - edge_trim)
    else:
        # Default to side-by-side with FIXED calculations
        filter_complex = (
            f'[0:v]crop=w={left_visible - edge_trim}:h={output_height}:x=0:y=0[left]; '
            f'[0:v]crop=w={feather_width}:h={output_height}:x={left_visible - edge_trim}:y=0[overlapL]; '
            f'[1:v]crop=w={feather_width}:h={output_height}:x=0:y=0[overlapR]; '
            f'[1:v]crop=w={right_visible - edge_trim}:h={output_height}:x={feather_width + edge_trim}:y=0[right]; '
            f'[overlapL][overlapR]blend=all_expr=\'A*(1-x/w)+B*(x/w)\'[blended]; '
            f'[left][blended][right]hstack=inputs=3,format=yuv420p[v]'
        )
        final_width = (left_visible - edge_trim) + feather_width + (right_visible - edge_trim)
    
    # Log the complete filter for debugging
    logger.debug(f"🔧 Complete filter_complex: {filter_complex}")
    
    cmd = [
        'ffmpeg', '-y',  # Overwrite output file
        '-i', str(video1_path),
        '-i', str(video2_path),
        '-filter_complex', filter_complex,
        '-map', '[v]',  # Map the output from our filter
        '-c:v', 'libx264',
        '-preset', 'fast',  # Match dual_record_test.py
        '-crf', '23',  # Good quality
        '-pix_fmt', 'yuv420p',  # Ensure compatibility
        str(output_path)
    ]
    


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
                    # Enhanced health check - check for stuck camera processes
                    try:
                        disk_usage = psutil.disk_usage('/')
                        logger.info(f"📊 Health check - Disk usage: {disk_usage.percent:.1f}% used, {disk_usage.free / (1024**3):.1f} GB free")
                        
                        # Check for stuck camera processes
                        import subprocess
                        result = subprocess.run(['pgrep', '-f', 'picamera2'], capture_output=True, text=True)
                        if result.returncode == 0:
                            camera_pids = result.stdout.strip().split('\n')
                            if len(camera_pids) > 2:  # More than expected
                                logger.warning(f"⚠️ Found {len(camera_pids)} camera processes, cleaning up...")
                                subprocess.run(['pkill', '-f', 'picamera2'], capture_output=True, timeout=5)
                                logger.info("✅ Cleaned up stuck camera processes")
                    except Exception as e:
                        logger.warning(f"⚠️ Health check failed: {e}")
                    last_health_check = current_time
                
                bookings = load_bookings()
                now = datetime.now(LOCAL_TZ)
                logger.info(f"📋 Loaded {len(bookings)} bookings from cache")
                active_booking = get_active_booking(bookings)
                
                if active_booking:
                    logger.info(f"🎯 Active booking found: {active_booking.get('id', 'unknown')}")
                else:
                    logger.info("⏳ No active booking found, waiting...")
                
                if current_session:
                    end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
                    logger.info(f"📊 Session status - Active: {current_session.active}, End time: {end_time}, Current time: {now}")
                    # Stop if end time has passed (regardless of active status)
                    if now > end_time:
                        logger.info(f"🛑 Booking ended at {end_time}, stopping recording (current time: {now})")
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