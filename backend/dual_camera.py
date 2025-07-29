#!/usr/bin/env python3
"""
EZREC Dual Camera Recording Service
Clean architecture implementation with modular design
"""

import os
import sys
import time
import json
import logging
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Add API directory to path for imports
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logging.error("❌ Picamera2 not available")

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

# Configuration
@dataclass
class CameraConfig:
    """Camera configuration settings"""
    CAM_IDS = [0, 1]
    RESOLUTION = (1920, 1080)  # Full HD
    FRAMERATE = 30
    BITRATE = 6_000_000  # 6 Mbps
    OUTPUT_DIR = Path("/opt/ezrec-backend/recordings")
    BOOKING_CACHE_FILE = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    LOG_FILE = Path("/opt/ezrec-backend/logs/dual_camera.log")

# Setup logging
def setup_logging():
    """Setup rotating file logger"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory
    CameraConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        CameraConfig.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)
    
    # Setup logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[rotating_handler, logging.StreamHandler()]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

class CameraRecorder:
    """Thread-safe camera recorder for a single camera"""
    
    def __init__(self, camera_id: int, camera_name: str, output_path: Path):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.output_path = output_path
        self.picamera2 = None
        self.encoder = None
        self.recording = False
        self.thread = None
        self.error = None
        self.success = False
        
        # Setup dedicated logger for this camera
        self.logger = logging.getLogger(f"{camera_name.lower()}_camera")
    
    def initialize_camera(self) -> bool:
        """Initialize camera with proper configuration"""
        try:
            self.logger.info(f"🔧 Initializing {self.camera_name} camera (ID: {self.camera_id})")
            
            # Create Picamera2 instance
            self.picamera2 = Picamera2(camera_num=self.camera_id)
            
            # Configure camera
            config = self.picamera2.create_video_configuration(
                main={"size": CameraConfig.RESOLUTION, "format": "YUV420"},
                controls={
                    "FrameDurationLimits": (33333, 1000000),
                    "ExposureTime": 33333,
                    "AnalogueGain": 1.0,
                    "NoiseReductionMode": 0
                }
            )
            
            self.picamera2.configure(config)
            self.picamera2.start()
            
            # Create H264 encoder
            self.encoder = H264Encoder(
                bitrate=CameraConfig.BITRATE,
                repeat=False,
                iperiod=30,
                qp=25
            )
            
            self.logger.info(f"✅ {self.camera_name} camera initialized successfully")
            return True
            
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ {self.camera_name} camera initialization failed: {e}")
            return False
    
    def start_recording(self) -> bool:
        """Start recording in a separate thread"""
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
        
        self.logger.info(f"✅ {self.camera_name} camera recording thread started")
        return True
    
    def _record_loop(self):
        """Main recording loop"""
        try:
            if not self.initialize_camera():
                self.logger.error(f"❌ {self.camera_name} camera initialization failed")
                return
            
            self.logger.info(f"🎥 Starting {self.camera_name} camera recording")
            self.recording = True
            
            # Start recording
            self.picamera2.start_recording(self.encoder, str(self.output_path))
            
            # Keep recording until stopped
            while self.recording:
                time.sleep(1)
                
                # Log progress every 10 seconds
                if self.output_path.exists():
                    size = self.output_path.stat().st_size
                    if size > 0:
                        self.logger.info(f"📹 {self.camera_name} recording: {size} bytes")
            
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ {self.camera_name} camera recording error: {e}")
        finally:
            self.stop_recording_internal()
    
    def stop_recording(self):
        """Stop recording with proper cleanup"""
        self.recording = False
        
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    time.sleep(2)  # Allow time for proper finalization
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
                self.logger.info(f"✅ {self.camera_name} camera hardware released")
        except Exception as e:
            self.logger.error(f"❌ Error stopping {self.camera_name} camera: {e}")
        
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                self.logger.warning(f"⚠️ {self.camera_name} camera thread did not stop gracefully")
            else:
                self.logger.info(f"✅ {self.camera_name} camera thread stopped gracefully")
        
        # Validate recording file
        if self.output_path.exists():
            size = self.output_path.stat().st_size
            self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
            self.success = True
        else:
            self.logger.error(f"❌ {self.camera_name} recording file not found")
    
    def stop_recording_internal(self):
        """Internal method to stop recording"""
        try:
            if self.picamera2:
                if self.recording:
                    self.picamera2.stop_recording()
                    time.sleep(2)
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
                self.logger.info(f"✅ {self.camera_name} camera hardware released")
            
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                self.logger.info(f"✅ {self.camera_name} recording completed: {size} bytes")
                self.success = True
            else:
                self.logger.error(f"❌ {self.camera_name} recording file not found")
                
        except Exception as e:
            self.logger.error(f"❌ Error stopping {self.camera_name} camera: {e}")

class DualCameraRecorder:
    """Manages dual camera recording session"""
    
    def __init__(self, booking_id: str, start_time: datetime, end_time: datetime):
        self.booking_id = booking_id
        self.start_time = start_time
        self.end_time = end_time
        self.active = False
        
        # Create output directory
        date_folder = CameraConfig.OUTPUT_DIR / start_time.strftime("%Y-%m-%d")
        date_folder.mkdir(parents=True, exist_ok=True)
        
        # Generate filenames
        filename_base = f"{start_time.strftime('%H%M%S')}-{end_time.strftime('%H%M%S')}_{booking_id}"
        self.cam0_file = date_folder / f"{filename_base}_cam0.h264"
        self.cam1_file = date_folder / f"{filename_base}_cam1.h264"
        self.merged_file = date_folder / f"{filename_base}_merged.mp4"
        
        # Camera recorders
        self.cam0_recorder = None
        self.cam1_recorder = None
        
        logger.info(f"🎬 Created dual camera recorder for booking {booking_id}")
        logger.info(f"📁 Output files: {self.cam0_file.name}, {self.cam1_file.name}")
    
    def start(self) -> bool:
        """Start dual camera recording"""
        try:
            logger.info(f"🎬 Starting dual camera recording for booking {self.booking_id}")
            
            # Create camera recorders
            self.cam0_recorder = CameraRecorder(0, "Camera0", self.cam0_file)
            self.cam1_recorder = CameraRecorder(1, "Camera1", self.cam1_file)
            
            # Start recording on both cameras
            cam0_started = self.cam0_recorder.start_recording()
            cam1_started = self.cam1_recorder.start_recording()
            
            if not cam0_started and not cam1_started:
                logger.error("❌ Both cameras failed to start recording")
                return False
            
            if not cam0_started:
                logger.warning("⚠️ Camera 0 failed to start, continuing with Camera 1 only")
                self.cam0_recorder = None
            
            if not cam1_started:
                logger.warning("⚠️ Camera 1 failed to start, continuing with Camera 0 only")
                self.cam1_recorder = None
            
            # Wait for threads to start
            time.sleep(2)
            
            # Check thread health
            active_cameras = 0
            if self.cam0_recorder and self.cam0_recorder.thread and self.cam0_recorder.thread.is_alive():
                active_cameras += 1
                logger.info("✅ Camera 0 recording thread is healthy")
            
            if self.cam1_recorder and self.cam1_recorder.thread and self.cam1_recorder.thread.is_alive():
                active_cameras += 1
                logger.info("✅ Camera 1 recording thread is healthy")
            
            if active_cameras == 0:
                logger.error("❌ No camera recording threads are healthy")
                return False
            
            self.active = True
            logger.info(f"✅ Dual camera recording started successfully with {active_cameras} active camera(s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording session: {e}")
            return False
    
    def stop(self):
        """Stop dual camera recording and merge videos"""
        logger.info("🛑 Stopping dual camera recording")
        
        try:
            # Stop camera recordings
            if self.cam0_recorder:
                logger.info("🛑 Stopping camera 0 recording...")
                self.cam0_recorder.stop_recording()
            
            if self.cam1_recorder:
                logger.info("🛑 Stopping camera 1 recording...")
                self.cam1_recorder.stop_recording()
            
            self.active = False
            
            # Wait for files to be finalized
            time.sleep(3)
            
            # Check recording results
            cam0_success = self.cam0_recorder.success if self.cam0_recorder else False
            cam1_success = self.cam1_recorder.success if self.cam1_recorder else False
            
            # Log file status
            if self.cam0_file.exists():
                cam0_size = self.cam0_file.stat().st_size
                logger.info(f"✅ Camera 0 recording: {self.cam0_file.name} ({cam0_size} bytes)")
            else:
                logger.error(f"❌ Camera 0 recording file missing: {self.cam0_file}")
            
            if self.cam1_file.exists():
                cam1_size = self.cam1_file.stat().st_size
                logger.info(f"✅ Camera 1 recording: {self.cam1_file.name} ({cam1_size} bytes)")
            else:
                logger.error(f"❌ Camera 1 recording file missing: {self.cam1_file}")
            
            # Merge videos if both cameras recorded successfully
            if cam0_success and cam1_success:
                logger.info("✅ Both camera recordings completed, merging videos...")
                if self._merge_videos():
                    logger.info(f"✅ Successfully created merged video: {self.merged_file}")
                    # Emit recording_complete event
                    self._emit_recording_complete_event()
                else:
                    logger.error("❌ Failed to merge videos")
            elif cam0_success:
                logger.info("⚠️ Only camera 0 recorded successfully")
                # Use single camera recording as merged file
                self._use_single_camera_recording(self.cam0_file)
            elif cam1_success:
                logger.info("⚠️ Only camera 1 recorded successfully")
                # Use single camera recording as merged file
                self._use_single_camera_recording(self.cam1_file)
            else:
                logger.error("❌ Both camera recordings failed")
            
        except Exception as e:
            logger.error(f"❌ Error stopping dual recording: {e}")
    
    def _merge_videos(self) -> bool:
        """Merge two video files using FFmpeg"""
        try:
            # Convert H.264 to MP4 first
            cam0_mp4 = self.cam0_file.with_suffix('.mp4')
            cam1_mp4 = self.cam1_file.with_suffix('.mp4')
            
            # Convert H.264 to MP4
            subprocess.run([
                'ffmpeg', '-y', '-i', str(self.cam0_file),
                '-c', 'copy', str(cam0_mp4)
            ], check=True, capture_output=True)
            
            subprocess.run([
                'ffmpeg', '-y', '-i', str(self.cam1_file),
                '-c', 'copy', str(cam1_mp4)
            ], check=True, capture_output=True)
            
            # Merge videos side by side
            cmd = [
                'ffmpeg', '-y',
                '-i', str(cam0_mp4),
                '-i', str(cam1_mp4),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-an',  # No audio
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-movflags', '+faststart',
                str(self.merged_file)
            ]
            
            logger.info(f"🎬 Merging videos using FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and self.merged_file.exists():
                file_size = self.merged_file.stat().st_size
                logger.info(f"✅ Successfully merged videos: {self.merged_file} ({file_size:,} bytes)")
                
                # Clean up individual files
                self.cam0_file.unlink(missing_ok=True)
                self.cam1_file.unlink(missing_ok=True)
                cam0_mp4.unlink(missing_ok=True)
                cam1_mp4.unlink(missing_ok=True)
                
                return True
            else:
                logger.error(f"❌ Failed to merge videos (exit code {result.returncode})")
                logger.error(f"🔧 FFmpeg stderr:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg merge timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"❌ Error merging videos: {e}")
            return False
    
    def _use_single_camera_recording(self, single_file: Path):
        """Use single camera recording as merged file"""
        try:
            # Convert H.264 to MP4
            single_mp4 = single_file.with_suffix('.mp4')
            subprocess.run([
                'ffmpeg', '-y', '-i', str(single_file),
                '-c', 'copy', str(single_mp4)
            ], check=True, capture_output=True)
            
            # Copy as merged file
            import shutil
            shutil.copy2(single_mp4, self.merged_file)
            
            if self.merged_file.exists():
                merged_size = self.merged_file.stat().st_size
                logger.info(f"✅ Created single camera merged video: {self.merged_file.name} ({merged_size:,} bytes)")
                
                # Clean up individual files
                single_file.unlink(missing_ok=True)
                single_mp4.unlink(missing_ok=True)
                
                # Emit recording_complete event
                self._emit_recording_complete_event()
            else:
                logger.error("❌ Failed to create single camera merged file")
                
        except Exception as e:
            logger.error(f"❌ Error creating single camera merged file: {e}")
    
    def _emit_recording_complete_event(self):
        """Emit recording_complete event with file paths"""
        try:
            event_data = {
                "booking_id": self.booking_id,
                "cam0_file": str(self.cam0_file),
                "cam1_file": str(self.cam1_file),
                "merged_file": str(self.merged_file),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save event to file for other processes to pick up
            event_file = self.merged_file.with_suffix('.event')
            with open(event_file, 'w') as f:
                json.dump(event_data, f, indent=2)
            
            logger.info(f"📡 Emitted recording_complete event: {event_file}")
            
        except Exception as e:
            logger.error(f"❌ Error emitting recording_complete event: {e}")

def load_bookings() -> list:
    """Load bookings from cache file"""
    if not CameraConfig.BOOKING_CACHE_FILE.exists():
        return []
    try:
        with open(CameraConfig.BOOKING_CACHE_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'bookings' in data:
                return data['bookings']
            else:
                return []
    except Exception as e:
        logger.error(f"❌ Error loading bookings: {e}")
        return []

def get_active_booking(bookings: list) -> Optional[Dict[str, Any]]:
    """Get the currently active booking"""
    now = datetime.now()
    logger.info(f"🔍 Checking {len(bookings)} bookings at {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for booking in bookings:
        try:
            start_time = datetime.fromisoformat(booking["start_time"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(booking["end_time"].replace('Z', '+00:00'))
            
            if start_time <= now <= end_time:
                logger.info(f"✅ Found active booking: {booking.get('id', 'unknown')}")
                return booking
                
        except Exception as e:
            logger.error(f"❌ Error processing booking: {e}")
            continue
    
    logger.info("❌ No active booking found")
    return None

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    
    # Stop active recording session
    if 'current_recorder' in globals() and current_recorder and current_recorder.active:
        logger.info("🛑 Stopping active recording before exit...")
        try:
            current_recorder.stop()
        except Exception as e:
            logger.error(f"❌ Error stopping recording during exit: {e}")
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    """Main application loop"""
    logger.info("🚀 EZREC Dual Camera Recorder started")
    logger.info(f"📁 Output directory: {CameraConfig.OUTPUT_DIR}")
    logger.info(f"📄 Booking cache: {CameraConfig.BOOKING_CACHE_FILE}")
    logger.info(f"📷 Camera IDs: {CameraConfig.CAM_IDS}")
    logger.info(f"🎬 Resolution: {CameraConfig.RESOLUTION}")
    logger.info(f"📹 Framerate: {CameraConfig.FRAMERATE}")
    logger.info(f"💾 Bitrate: {CameraConfig.BITRATE:,} bps")
    
    # Check if Picamera2 is available
    if not PICAMERA2_AVAILABLE:
        logger.error("❌ Picamera2 not available. Cannot start recording.")
        sys.exit(1)
    
    # Verify output directory
    try:
        CameraConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Output directory is accessible: {CameraConfig.OUTPUT_DIR}")
    except Exception as e:
        logger.error(f"❌ Cannot access output directory: {e}")
        sys.exit(1)
    
    current_recorder = None
    
    try:
        while True:
            try:
                bookings = load_bookings()
                active_booking = get_active_booking(bookings)
                
                if current_recorder:
                    # Check if current recording should end
                    if datetime.now() > current_recorder.end_time and current_recorder.active:
                        logger.info(f"🛑 Booking ended, stopping recording")
                        current_recorder.stop()
                        current_recorder = None
                        
                if not current_recorder and active_booking:
                    # Start new recording
                    logger.info(f"🎬 Starting recording for booking: {active_booking['id']}")
                    
                    start_time = datetime.fromisoformat(active_booking["start_time"].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(active_booking["end_time"].replace('Z', '+00:00'))
                    
                    current_recorder = DualCameraRecorder(
                        active_booking['id'],
                        start_time,
                        end_time
                    )
                    
                    if not current_recorder.start():
                        logger.error(f"❌ Failed to start recording session")
                        current_recorder = None
                        
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                import traceback
                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error in main loop: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
    finally:
        # Ensure graceful cleanup
        logger.info("🛑 Performing graceful shutdown...")
        if current_recorder and current_recorder.active:
            logger.info("🛑 Stopping active recording before exit...")
            try:
                current_recorder.stop()
            except Exception as e:
                logger.error(f"❌ Error stopping recording during exit: {e}")
        
        logger.info("✅ Shutdown completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main() 