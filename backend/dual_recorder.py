#!/usr/bin/env python3
"""
Dual Camera Recorder Service
- Uses separate processes for each camera to avoid resource conflicts
- Records from both cameras simultaneously
- Merges recordings into a single video file
"""

import os
import sys
import time
import json
import logging
import signal
import pytz
import psutil
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

dotenv_path = "/opt/ezrec-backend/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"❌ .env file not found at {dotenv_path}")
    sys.exit(1)

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

# Avoid double processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'dual_recorder.py' in ' '.join(proc.info['cmdline']) and proc.info['pid'] != os.getpid():
            print("❌ dual_recorder.py is already running.")
            sys.exit(1)
    except Exception:
        continue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
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

def merge_videos(video1_path: Path, video2_path: Path, output_path: Path, method: str = 'side_by_side'):
    """
    Merge two video files using FFmpeg
    """
    try:
        if method == 'side_by_side':
            # Side-by-side merge
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                str(output_path)
            ]
        elif method == 'picture_in_picture':
            # Picture-in-picture merge
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]scale2ref=iw/4:ih/4[main][pip];[main][pip]overlay=W-w-10:H-h-10',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                str(output_path)
            ]
        else:
            raise ValueError(f"Unknown merge method: {method}")

        logger.info(f"🎬 Merging videos using {method} method...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            logger.info(f"✅ Successfully merged videos: {output_path}")
            return True
        else:
            logger.error(f"❌ Failed to merge videos: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error merging videos: {e}")
        return False

def create_single_camera_recorder(camera_serial: str, camera_name: str, output_file: Path):
    """
    Create a Python script for single camera recording
    """
    logger.info(f"🔧 Creating recorder script for {camera_name} camera (Serial: {camera_serial})")
    
    script_content = f'''#!/usr/bin/env python3
"""
Single Camera Recorder for {camera_name} camera
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging for this camera script
camera_name = "{camera_name}"
log_file = f"/tmp/{{camera_name.lower()}}_camera_debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(f"{{camera_name.lower()}}_camera")

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
except ImportError as e:
    logger.error(f"❌ Picamera2 not available: {{e}}")
    sys.exit(1)

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

def signal_handler(sig, frame):
    print("🛑 Received termination signal")
    if 'camera' in globals():
        try:
            camera.stop_recording()
            camera.stop()
            camera.close()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    camera_serial = "{camera_serial}"
    output_file = "{output_file}"
    
    logger.info(f"📷 Starting {{camera_name}} camera recording (Serial: {{camera_serial}})")
    logger.info(f"📁 Output file: {{output_file}}")
    logger.info(f"📝 Debug log: {{log_file}}")
    
    try:
        # Initialize camera with retry logic
        logger.info(f"🔧 Initializing camera with serial: {{camera_serial}}")
        
        # Kill any existing camera processes that might be using the device
        logger.info("🔪 Killing any existing camera processes...")
        os.system("sudo fuser -k /dev/video* 2>/dev/null || true")
        time.sleep(2)
        
        # Initialize camera with multiple retries
        camera = None
        for attempt in range(3):
            try:
                camera = Picamera2()
                
                # Configure camera with serial-specific settings
                config = camera.create_video_configuration(
                    main={{"size": (1920, 1080), "format": "YUV420"}},
                    controls={{
                        "FrameDurationLimits": (33333, 1000000),
                        "ExposureTime": 33333,
                        "AnalogueGain": 1.0,
                        "NoiseReductionMode": 0
                    }}
                )
                
                logger.info(f"⚙️ Configuring camera...")
                camera.configure(config)
                camera.start()
                
                logger.info(f"✅ Camera initialized successfully on attempt {{attempt + 1}}")
                break
                
            except Exception as e:
                logger.warning(f"⚠️ Camera initialization attempt {{attempt + 1}} failed: {{e}}")
                if camera:
                    try:
                        camera.close()
                    except:
                        pass
                if attempt < 2:
                    logger.info(f"🔄 Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    raise Exception(f"Failed to initialize camera after 3 attempts: {{e}}")
        
        # Create encoder
        encoder = H264Encoder(
            bitrate=6000000,
            repeat=False,
            iperiod=30,
            qp=25
        )
        
        # Start recording
        logger.info(f"🎥 Starting recording to: {{output_file}}")
        camera.start_recording(encoder, str(output_file))
        time.sleep(1.0)
        
        logger.info(f"✅ {{camera_name}} camera recording started")
        
        # Keep recording until interrupted
        while True:
            time.sleep(1)
            # Check if file exists and has content
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                if file_size > 0:
                    logger.info(f"📹 Recording in progress: {{file_size}} bytes written")
            
    except Exception as e:
        logger.error(f"❌ Error in {{camera_name}} camera: {{e}}")
        import traceback
        logger.error(f"📋 Traceback: {{traceback.format_exc()}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    script_path = Path(f"/tmp/camera_{camera_name.lower()}_recorder.py")
    logger.info(f"📝 Writing script to: {script_path}")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    script_path.chmod(0o755)
    logger.info(f"✅ Created executable script: {script_path}")
    
    return script_path

class DualRecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RECORDINGS_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        
        # 🔧 Add better error handling for directory creation
        try:
            self.date_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created/verified recordings directory: {self.date_folder}")
        except PermissionError as e:
            logger.error(f"❌ Permission denied creating {self.date_folder}: {e}")
            logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
            logger.error(f"🔧 Then: sudo chmod -R 775 {RECORDINGS_DIR}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create recordings directory {self.date_folder}: {e}")
            raise
        start_dt = parser.isoparse(booking["start_time"]).astimezone(LOCAL_TZ)
        end_dt = parser.isoparse(booking["end_time"]).astimezone(LOCAL_TZ)
        self.filename_base = f"{start_dt.strftime('%H%M%S')}-{end_dt.strftime('%H%M%S')}"
        
        # Individual camera files
        self.camera0_file = self.date_folder / f"{self.filename_base}_{CAMERA_0_NAME}.mp4"
        self.camera1_file = self.date_folder / f"{self.filename_base}_{CAMERA_1_NAME}.mp4"
        
        # Merged output file
        self.merged_file = self.date_folder / f"{self.filename_base}_merged.mp4"
        
        # Process tracking
        self.camera0_process = None
        self.camera1_process = None
        self.active = False
        self.recording_start_time = None

    def start(self):
        try:
            logger.info(f"🎬 Starting dual camera recording to {self.merged_file}")
            logger.info(f"📷 Camera 0: {self.camera0_file}")
            logger.info(f"📷 Camera 1: {self.camera1_file}")
            
            # Create recorder scripts for each camera
            logger.info(f"🔧 Creating camera recorder scripts...")
            script0 = create_single_camera_recorder(CAMERA_0_SERIAL, CAMERA_0_NAME, self.camera0_file)
            script1 = create_single_camera_recorder(CAMERA_1_SERIAL, CAMERA_1_NAME, self.camera1_file)
            
            logger.info(f"📝 Created scripts: {script0}, {script1}")
            
            # Verify scripts exist and are executable
            if not script0.exists() or not script1.exists():
                logger.error("❌ Failed to create camera recorder scripts")
                return False
            
            # Start cameras sequentially with delays to avoid resource conflicts
            logger.info(f"📷 Starting left camera process...")
            self.camera0_process = subprocess.Popen(
                [sys.executable, str(script0)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for first camera to initialize
            time.sleep(5.0)
            
            # Check if first camera started successfully
            if self.camera0_process.poll() is not None:
                stdout, stderr = self.camera0_process.communicate()
                logger.error(f"❌ Camera 0 process failed to start")
                logger.error(f"📤 Camera 0 stdout: {stdout}")
                logger.error(f"📥 Camera 0 stderr: {stderr}")
                return False
            
            logger.info(f"✅ Camera 0 process started successfully")
            
            # Check if first camera file is being created
            time.sleep(2.0)  # Give camera time to start writing
            if self.camera0_file.exists():
                logger.info(f"✅ {CAMERA_0_NAME} camera file created: {self.camera0_file.stat().st_size} bytes")
            else:
                logger.warning(f"⚠️ {CAMERA_0_NAME} camera file not found after 7s")
            
            # Wait additional time before starting second camera
            time.sleep(3.0)
            
            logger.info(f"📷 Starting right camera process...")
            self.camera1_process = subprocess.Popen(
                [sys.executable, str(script1)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for second camera to initialize
            time.sleep(5.0)
            
            # Check if second camera started successfully
            if self.camera1_process.poll() is not None:
                stdout, stderr = self.camera1_process.communicate()
                logger.error(f"❌ Camera 1 process failed to start")
                logger.error(f"📤 Camera 1 stdout: {stdout}")
                logger.error(f"📥 Camera 1 stderr: {stderr}")
                # Stop first camera if second failed
                if self.camera0_process.poll() is None:
                    self.camera0_process.terminate()
                    self.camera0_process.wait()
                return False
            
            logger.info(f"✅ Camera 1 process started successfully")
            
            # Check if second camera file is being created
            time.sleep(2.0)  # Give camera time to start writing
            if self.camera1_file.exists():
                logger.info(f"✅ {CAMERA_1_NAME} camera file created: {self.camera1_file.stat().st_size} bytes")
            else:
                logger.warning(f"⚠️ {CAMERA_1_NAME} camera file not found after 7s")
            
            # Final check that both processes are running
            if self.camera0_process.poll() is None and self.camera1_process.poll() is None:
                self.active = True
                logger.info(f"🎬 Both camera processes started successfully")
                
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
                
                return True
            else:
                logger.error(f"❌ One or both camera processes failed to start")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start recording session: {e}")
            return False

    def stop(self):
        logger.info("🛑 Stopping dual camera recording")
        
        try:
            # Stop camera processes
            if self.camera0_process and self.camera0_process.poll() is None:
                logger.info(f"🛑 Stopping {CAMERA_0_NAME} camera process...")
                self.camera0_process.terminate()
                self.camera0_process.wait(timeout=10)
            
            if self.camera1_process and self.camera1_process.poll() is None:
                logger.info(f"🛑 Stopping {CAMERA_1_NAME} camera process...")
                self.camera1_process.terminate()
                self.camera1_process.wait(timeout=10)
            
            self.active = False
            
            # Wait for files to be finalized
            time.sleep(2)
            
            # Check if both camera files exist and log details
            logger.info("🔍 Checking camera recording files...")
            cam0_exists = self.camera0_file.exists()
            cam1_exists = self.camera1_file.exists()
            
            if cam0_exists:
                cam0_size = self.camera0_file.stat().st_size
                logger.info(f"✅ {CAMERA_0_NAME} recording: {self.camera0_file.name} ({cam0_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_0_NAME} recording file missing: {self.camera0_file}")
            
            if cam1_exists:
                cam1_size = self.camera1_file.stat().st_size
                logger.info(f"✅ {CAMERA_1_NAME} recording: {self.camera1_file.name} ({cam1_size} bytes)")
            else:
                logger.error(f"❌ {CAMERA_1_NAME} recording file missing: {self.camera1_file}")
            
            if cam0_exists and cam1_exists:
                logger.info("✅ Both camera recordings completed")
                
                # Merge the videos
                if merge_videos(self.camera0_file, self.camera1_file, self.merged_file, MERGE_METHOD):
                    logger.info(f"✅ Successfully created merged video: {self.merged_file}")
                    
                    # Create .done marker for video worker
                    done_marker = self.merged_file.with_suffix('.done')
                    done_marker.touch()
                    
                    # Save metadata
                    self.save_metadata()
                    
                    # Clean up individual camera files
                    self.camera0_file.unlink(missing_ok=True)
                    self.camera1_file.unlink(missing_ok=True)
                    
                else:
                    logger.error("❌ Failed to merge videos")
            else:
                logger.warning("⚠️ One or both camera recordings are missing")
                # Create error marker to prevent infinite retries
                error_marker = self.merged_file.with_suffix('.error')
                error_marker.touch()
                logger.error("🔧 Created .error marker to prevent infinite retries")
            
            # Update booking status
            update_booking_status(self.booking["id"], "RecordingFinished")
            
            # Update camera status
            supabase.table('cameras').update({
                'is_recording': False,
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                'status': 'online'
            }).eq('id', CAMERA_ID).execute()
            
            try:
                set_is_recording(False)
            except Exception as e:
                logger.error(f"❌ Failed to update recording status: {e}")
                logger.error(f"🔧 This is likely a permission issue with status.json")
            
        except Exception as e:
            logger.error(f"❌ Error stopping dual recording: {e}")

    def save_metadata(self):
        """Save metadata for the merged recording"""
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
                "merge_method": MERGE_METHOD
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"📝 Metadata saved to: {metadata_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")

def handle_exit(sig, frame):
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

def get_active_booking(bookings):
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
    if not BOOKING_CACHE_FILE.exists():
        return []
    try:
        with open(BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def main():
    logger.info(f"📡 Dual Recorder started [Timezone: {TIMEZONE_NAME}]")
    logger.info(f"📄 Watching bookings cache: {BOOKING_CACHE_FILE}")
    logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
    logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
    logger.info(f"🎬 Merge method: {MERGE_METHOD}")
    
    # 🔧 Verify recordings directory permissions
    try:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = RECORDINGS_DIR / "test_write.tmp"
        test_file.touch()
        test_file.unlink()
        logger.info(f"✅ Recordings directory is writable: {RECORDINGS_DIR}")
    except PermissionError as e:
        logger.error(f"❌ Permission denied accessing recordings directory: {RECORDINGS_DIR}")
        logger.error(f"🔧 Fix: Run: sudo chown -R michomanoly14892:video {RECORDINGS_DIR}")
        logger.error(f"🔧 Then: sudo chmod -R 775 {RECORDINGS_DIR}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to access recordings directory: {RECORDINGS_DIR} - {e}")
        sys.exit(1)
    
    # Verify camera serials are set
    if not CAMERA_0_SERIAL or CAMERA_0_SERIAL == "auto":
        logger.error("❌ CAMERA_0_SERIAL not properly configured")
        sys.exit(1)
    if not CAMERA_1_SERIAL or CAMERA_1_SERIAL == "auto":
        logger.error("❌ CAMERA_1_SERIAL not properly configured")
        sys.exit(1)
    
    logger.info("✅ Camera configuration verified")
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    current_session = None
    
    while True:
        try:
            bookings = load_bookings()
            now = datetime.now(LOCAL_TZ)
            active_booking = get_active_booking(bookings)
            
            if current_session:
                end_time = parser.isoparse(current_session.booking["end_time"]).astimezone(LOCAL_TZ)
                if now > end_time:
                    logger.info(f"🛑 Booking ended, stopping recording")
                    current_session.stop()
                    current_session = None
                    
            if not current_session and active_booking:
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

if __name__ == "__main__":
    main() 