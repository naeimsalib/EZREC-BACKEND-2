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
from pathlib import Path
from dotenv import load_dotenv

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
except ImportError as e:
    print(f"❌ Picamera2 not available: {{e}}")
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
    
    print(f"📷 Starting {camera_name} camera recording (Serial: {{camera_serial}})")
    print(f"📁 Output file: {{output_file}}")
    
    try:
        # Initialize camera
        print(f"🔧 Initializing camera with serial: {{camera_serial}}")
        camera = Picamera2()
        
        # Configure camera
        print(f"⚙️ Configuring camera...")
        config = camera.create_video_configuration(
            main={{"size": (1920, 1080), "format": "YUV420"}},
            controls={{
                "FrameDurationLimits": (33333, 1000000),
                "ExposureTime": 33333,
                "AnalogueGain": 1.0,
                "NoiseReductionMode": 0
            }}
        )
        
        camera.configure(config)
        camera.start()
        
        # Create encoder
        print(f"🎬 Creating encoder...")
        encoder = H264Encoder(
            bitrate=6000000,
            repeat=False,
            iperiod=30,
            qp=25
        )
        
        # Start recording
        print(f"🎥 Starting recording to {{output_file}}")
        camera.start_recording(encoder, str(output_file))
        time.sleep(1.0)
        
        print(f"✅ {camera_name} camera recording started")
        
        # Keep recording until interrupted
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ Error in {camera_name} camera: {{e}}")
        import traceback
        print(f"📋 Traceback: {{traceback.format_exc()}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    script_path = Path(f"/tmp/camera_{camera_name}_recorder.py")
    logger.info(f"📝 Writing script to: {script_path}")
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        logger.info(f"✅ Created executable script: {script_path}")
        return script_path
    except Exception as e:
        logger.error(f"❌ Failed to create script {script_path}: {e}")
        raise

class DualRecordingSession:
    def __init__(self, booking):
        self.booking = booking
        self.date_folder = RECORDINGS_DIR / datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        self.date_folder.mkdir(parents=True, exist_ok=True)
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
            if not script0.exists():
                logger.error(f"❌ Camera 0 script not created: {script0}")
                return False
            if not script1.exists():
                logger.error(f"❌ Camera 1 script not created: {script1}")
                return False
            
            # Start camera 0 process with error capture
            logger.info(f"📷 Starting {CAMERA_0_NAME} camera process...")
            self.camera0_process = subprocess.Popen([
                sys.executable, str(script0)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for camera 0 to initialize
            time.sleep(3)
            
            # Check camera 0 process status
            if self.camera0_process.poll() is not None:
                stdout, stderr = self.camera0_process.communicate()
                logger.error(f"❌ Camera 0 process failed to start")
                logger.error(f"📤 Camera 0 stdout: {stdout}")
                logger.error(f"📥 Camera 0 stderr: {stderr}")
                return False
            
            # Start camera 1 process with error capture
            logger.info(f"📷 Starting {CAMERA_1_NAME} camera process...")
            self.camera1_process = subprocess.Popen([
                sys.executable, str(script1)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait for both processes to start
            time.sleep(2)
            
            # Check camera 1 process status
            if self.camera1_process.poll() is not None:
                stdout, stderr = self.camera1_process.communicate()
                logger.error(f"❌ Camera 1 process failed to start")
                logger.error(f"📤 Camera 1 stdout: {stdout}")
                logger.error(f"📥 Camera 1 stderr: {stderr}")
                # Stop camera 0 if it's still running
                if self.camera0_process.poll() is None:
                    self.camera0_process.terminate()
                    self.camera0_process.wait(timeout=5)
                return False
            
            # Check if both processes are running
            if (self.camera0_process.poll() is None and 
                self.camera1_process.poll() is None):
                
                self.active = True
                self.recording_start_time = datetime.now(LOCAL_TZ)
                logger.info("✅ Dual camera recording started successfully")
                
                # Update booking status
                update_booking_status(self.booking["id"], "Recording")
                
                # Update camera status
                supabase.table('cameras').update({
                    'is_recording': True,
                    'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                    'status': 'online'
                }).eq('id', CAMERA_ID).execute()
                
                set_is_recording(True)
                return True
            else:
                logger.error("❌ One or both camera processes failed to start")
                # Get error output from failed processes
                if self.camera0_process.poll() is not None:
                    stdout, stderr = self.camera0_process.communicate()
                    logger.error(f"📤 Camera 0 stdout: {stdout}")
                    logger.error(f"📥 Camera 0 stderr: {stderr}")
                if self.camera1_process.poll() is not None:
                    stdout, stderr = self.camera1_process.communicate()
                    logger.error(f"📤 Camera 1 stdout: {stdout}")
                    logger.error(f"📥 Camera 1 stderr: {stderr}")
                self.stop()
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start dual recording: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            self.stop()
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
            
            # Check if both camera files exist
            if self.camera0_file.exists() and self.camera1_file.exists():
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
            
            # Update booking status
            update_booking_status(self.booking["id"], "RecordingFinished")
            
            # Update camera status
            supabase.table('cameras').update({
                'is_recording': False,
                'last_seen': datetime.now(LOCAL_TZ).isoformat(),
                'status': 'online'
            }).eq('id', CAMERA_ID).execute()
            
            set_is_recording(False)
            
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