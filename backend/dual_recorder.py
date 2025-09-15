#!/usr/bin/env python3
"""
EZREC Dual Camera Recorder Service - SIMPLIFIED VERSION
Direct implementation without complex service architecture
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import pytz

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dual_recorder")

class SimpleDualRecorder:
    """Simplified dual recorder service"""
    
    def __init__(self):
        self.recordings_path = Path("/opt/ezrec-backend/recordings")
        self.bookings_path = Path("/opt/ezrec-backend/api/local_data/bookings.json")
        self.current_booking = None
        self.recording_processes = []
        
        # Ensure directories exist
        self.recordings_path.mkdir(parents=True, exist_ok=True)
        self.bookings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clean up any zombie processes on startup
        self.cleanup_zombie_processes()
        
        logger.info("🎥 Simple Dual Recorder Service initialized")
    
    def cleanup_zombie_processes(self):
        """Clean up any zombie rpicam-vid processes on startup"""
        try:
            logger.info("🧹 Cleaning up zombie rpicam-vid processes...")
            result = subprocess.run(['pkill', '-f', 'rpicam-vid'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Zombie processes cleaned up")
            else:
                logger.info("ℹ️ No zombie processes found")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup zombie processes: {e}")
    
    def load_bookings(self):
        """Load bookings from file"""
        try:
            if self.bookings_path.exists():
                with open(self.bookings_path, 'r') as f:
                    bookings = json.load(f)
                logger.info(f"📋 Loaded {len(bookings)} bookings from cache")
                return bookings
            else:
                logger.info("📋 No bookings file found")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to load bookings: {e}")
            return []
    
    def find_active_booking(self):
        """Find an active booking that should be recording now"""
        bookings = self.load_bookings()
        if not bookings:
            return None
        
        # Get current local time (system timezone)
        now_local = datetime.now()
        logger.info(f"🔍 Checking {len(bookings)} bookings at {now_local} (local time)")
        
        for booking in bookings:
            try:
                # Parse booking times - handle both UTC and local time formats
                start_time_str = booking['start_time']
                end_time_str = booking['end_time']
                
                # If times end with 'Z', treat as UTC and convert to local
                if start_time_str.endswith('Z'):
                    start_time_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    end_time_utc = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    
                    # Convert UTC to local time
                    start_time = start_time_utc.replace(tzinfo=None) + (now_local - datetime.utcnow())
                    end_time = end_time_utc.replace(tzinfo=None) + (now_local - datetime.utcnow())
                else:
                    # Assume local time format
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', ''))
                
                logger.info(f"🔍 Booking {booking['id']}: {start_time} - {end_time}")
                logger.info(f"   Now: {now_local}")
                
                # Compare in local time
                if start_time <= now_local <= end_time:
                    logger.info(f"🎯 Active booking found: {booking['id']}")
                    return booking
            except Exception as e:
                logger.error(f"❌ Error parsing booking {booking.get('id', 'unknown')}: {e}")
                continue
        
        logger.info("❌ No active booking found")
        return None
    
    def detect_cameras(self):
        """Detect available cameras and return camera count"""
        try:
            result = subprocess.run(['rpicam-vid', '--list-cameras'], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                # Parse the output to count cameras
                output = result.stdout
                camera_count = 0
                
                # Look for camera entries in the output - improved parsing
                lines = output.split('\n')
                for line in lines:
                    # Look for lines that start with a number followed by a colon (camera index)
                    if line.strip() and ':' in line and line.strip()[0].isdigit():
                        camera_count += 1
                
                logger.info(f"✅ Detected {camera_count} camera(s)")
                logger.info(f"📋 Camera detection output: {output.strip()}")
                return camera_count
            else:
                logger.warning("⚠️ No cameras detected")
                return 0
        except Exception as e:
            logger.error(f"❌ Camera detection failed: {e}")
            return 0
    
    def start_recording(self, booking):
        """Start recording for a booking with smart camera handling"""
        try:
            logger.info(f"🎬 Starting recording for booking: {booking['id']}")
            
            # Create recording directory
            today = datetime.now().strftime("%Y-%m-%d")
            session_dir = self.recordings_path / today / f"session_{booking['id']}"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean up any existing processes first
            self.cleanup_zombie_processes()
            time.sleep(2)  # Wait for cleanup to complete
            
            # Detect available cameras
            camera_count = self.detect_cameras()
            
            if camera_count == 0:
                logger.error("❌ No cameras detected - cannot start recording")
                return False
            elif camera_count == 1:
                logger.info("📷 Single camera detected - starting single camera recording")
                return self._start_single_camera_recording(booking, session_dir)
            else:
                logger.info(f"📷 {camera_count} cameras detected - starting dual camera recording")
                return self._start_dual_camera_recording(booking, session_dir)
                
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            return False
    
    def _start_single_camera_recording(self, booking, session_dir):
        """Start recording with a single camera"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create a single recording file
            output_file = session_dir / f"camera_0_{timestamp}.mp4"
            
            cmd = [
                'rpicam-vid',
                '--camera', '0',  # Explicitly specify camera 0
                '--width', '1280',
                '--height', '720',
                '--framerate', '25',
                '--output', str(output_file),
                '--timeout', '300000',  # 5 minutes
                '--codec', 'h264',
                '--bitrate', '5000000'  # 5 Mbps
            ]
            
            logger.info("🎥 Starting single camera recording...")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(3)  # Wait for camera to initialize
            
            # Check if recording started successfully
            if process.poll() is not None:
                logger.error(f"❌ Camera failed to start (exit code: {process.returncode})")
                stderr_output = process.stderr.read().decode() if process.stderr else 'No error output'
                logger.error(f"❌ Camera error: {stderr_output}")
                return False
            
            # Store successful process
            self.recording_processes = [process]
            self.current_booking = booking
            
            logger.info(f"🎉 SINGLE CAMERA RECORDING STARTED SUCCESSFULLY!")
            logger.info(f"📁 Recording to: {output_file.name}")
            logger.info(f"⏱️ Recording duration: 5 minutes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start single camera recording: {e}")
            return False
    
    def _start_dual_camera_recording(self, booking, session_dir):
        """Start recording with dual cameras simultaneously"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Camera 0 - Primary camera
            output_file_0 = session_dir / f"camera_0_{timestamp}.mp4"
            cmd_0 = [
                'rpicam-vid',
                '--camera', '0',  # Explicitly specify camera 0
                '--width', '1280',
                '--height', '720',
                '--framerate', '25',
                '--output', str(output_file_0),
                '--timeout', '300000',  # 5 minutes
                '--codec', 'h264',
                '--bitrate', '5000000'  # 5 Mbps
            ]
            
            # Camera 1 - Secondary camera
            output_file_1 = session_dir / f"camera_1_{timestamp}.mp4"
            cmd_1 = [
                'rpicam-vid',
                '--camera', '1',  # Explicitly specify camera 1
                '--width', '1280',
                '--height', '720',
                '--framerate', '25',
                '--output', str(output_file_1),
                '--timeout', '300000',  # 5 minutes
                '--codec', 'h264',
                '--bitrate', '5000000'  # 5 Mbps
            ]
            
            logger.info("🎥 Starting BOTH cameras simultaneously...")
            
            # Start both cameras at the same time
            process_0 = subprocess.Popen(cmd_0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process_1 = subprocess.Popen(cmd_1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for both cameras to initialize
            time.sleep(5)  # Give both cameras time to start
            
            # Check if both cameras started successfully
            camera_0_success = process_0.poll() is None
            camera_1_success = process_1.poll() is None
            
            if not camera_0_success:
                logger.error(f"❌ Camera 0 failed to start (exit code: {process_0.returncode})")
                stderr_output = process_0.stderr.read().decode() if process_0.stderr else 'No error output'
                logger.error(f"❌ Camera 0 error: {stderr_output}")
                # Clean up failed process
                if camera_1_success:
                    process_1.terminate()
                return False
            
            if not camera_1_success:
                logger.error(f"❌ Camera 1 failed to start (exit code: {process_1.returncode})")
                stderr_output = process_1.stderr.read().decode() if process_1.stderr else 'No error output'
                logger.error(f"❌ Camera 1 error: {stderr_output}")
                # Clean up failed process
                process_0.terminate()
                return False
            
            # Both cameras started successfully
            self.recording_processes = [process_0, process_1]
            self.current_booking = booking
            
            logger.info(f"🎉 DUAL CAMERA RECORDING STARTED SUCCESSFULLY!")
            logger.info(f"📁 Camera 0: {output_file_0.name}")
            logger.info(f"📁 Camera 1: {output_file_1.name}")
            logger.info(f"⏱️ Recording duration: 5 minutes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start dual camera recording: {e}")
            return False
    
    def stop_recording(self):
        """Stop current recording"""
        if not self.recording_processes:
            return
        
        logger.info("🛑 Stopping recording")
        
        for process in self.recording_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        self.recording_processes = []
        self.current_booking = None
        logger.info("✅ Recording stopped")
    
    def is_recording(self):
        """Check if currently recording with detailed status"""
        if not self.recording_processes:
            return False
        
        # Check each process individually
        active_processes = []
        for i, process in enumerate(self.recording_processes):
            if process.poll() is not None:
                # Process has ended
                exit_code = process.returncode
                logger.info(f"🔄 Camera {i} process ended (exit code: {exit_code})")
                if exit_code != 0:
                    logger.warning(f"⚠️ Camera {i} exited with error code: {exit_code}")
            else:
                active_processes.append(process)
                logger.debug(f"✅ Camera {i} still recording")
        
        # Update the recording processes list
        self.recording_processes = active_processes
        
        # If no active processes, clear current booking
        if not self.recording_processes:
            logger.info("🛑 All recording processes ended - clearing current booking")
            self.current_booking = None
            return False
        
        # Log current status
        active_count = len(self.recording_processes)
        expected_count = 2 if len(self.recording_processes) > 1 else 1
        logger.info(f"📊 Recording status: {active_count}/{expected_count} cameras active")
        
        return True
    
    def check_and_handle_bookings(self):
        """Check for active bookings and handle recording"""
        try:
            active_booking = self.find_active_booking()
            currently_recording = self.is_recording()
            
            logger.info(f"📊 Status: Active booking: {active_booking is not None}, Recording: {currently_recording}")
            
            if active_booking and not currently_recording:
                # Start recording for active booking
                logger.info("🚀 Starting new recording session")
                self.start_recording(active_booking)
            elif not active_booking and currently_recording:
                # Stop recording if no active booking
                logger.info("🛑 Stopping recording - no active booking")
                self.stop_recording()
            elif active_booking and currently_recording:
                logger.info("✅ Recording in progress for active booking")
            else:
                logger.info("⏸️ No active booking, no recording")
                
        except Exception as e:
            logger.error(f"❌ Error in check_and_handle_bookings: {e}")

def main():
    """Main service function - runs continuously"""
    logger.info("🎥 EZREC Simple Dual Recorder Service Starting")
    
    # Create service
    recorder = SimpleDualRecorder()
    
    # Test camera detection
    camera_count = recorder.detect_cameras()
    if camera_count == 0:
        logger.warning("⚠️ No cameras detected, but continuing...")
    else:
        logger.info(f"✅ {camera_count} camera(s) detected and ready")
    
    try:
        while True:
            # Check and handle bookings
            recorder.check_and_handle_bookings()
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
        recorder.stop_recording()
    except Exception as e:
        logger.error(f"❌ Service error: {e}")
        recorder.stop_recording()

if __name__ == "__main__":
    main()
