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
        """Detect available cameras"""
        try:
            result = subprocess.run(['rpicam-vid', '--output', '/dev/null'], 
                                  capture_output=True, text=True, timeout=10)
            
            # Check stderr for camera information
            if 'Available cameras' in result.stderr or 'imx477' in result.stderr:
                logger.info("✅ Cameras detected successfully")
                return True
            else:
                logger.warning("⚠️ No cameras detected")
                return False
        except Exception as e:
            logger.error(f"❌ Camera detection failed: {e}")
            return False
    
    def start_recording(self, booking):
        """Start recording for a booking"""
        try:
            logger.info(f"🎬 Starting recording for booking: {booking['id']}")
            
            # Create recording directory
            today = datetime.now().strftime("%Y-%m-%d")
            session_dir = self.recordings_path / today / f"session_{booking['id']}"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Start recording for both cameras
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Camera 0 - Use simpler parameters for better compatibility
            output_file_0 = session_dir / f"camera_0_{timestamp}.mp4"
            cmd_0 = [
                'rpicam-vid',
                '--width', '1280',
                '--height', '720',
                '--framerate', '25',
                '--output', str(output_file_0),
                '--timeout', '300000'  # 5 minutes
            ]
            
            # Camera 1 - Use simpler parameters for better compatibility
            output_file_1 = session_dir / f"camera_1_{timestamp}.mp4"
            cmd_1 = [
                'rpicam-vid',
                '--width', '1280',
                '--height', '720',
                '--framerate', '25',
                '--output', str(output_file_1),
                '--timeout', '300000'  # 5 minutes
            ]
            
            # Test camera availability first
            logger.info("🔍 Testing camera availability...")
            test_result = subprocess.run(['rpicam-vid', '--list-cameras'], 
                                       capture_output=True, text=True, timeout=10)
            if test_result.returncode != 0:
                logger.error(f"❌ Camera test failed: {test_result.stderr}")
                return False
            
            logger.info("✅ Cameras available, starting recording...")
            
            # Start recording processes with staggered timing to avoid conflicts
            process_0 = subprocess.Popen(cmd_0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(1)  # Wait 1 second between camera starts
            process_1 = subprocess.Popen(cmd_1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment and check if processes started successfully
            time.sleep(3)
            
            if process_0.poll() is not None:
                logger.error(f"❌ Camera 0 process failed immediately (exit code: {process_0.returncode})")
                logger.error(f"❌ Camera 0 stderr: {process_0.stderr.read().decode() if process_0.stderr else 'No error output'}")
                return False
                
            if process_1.poll() is not None:
                logger.error(f"❌ Camera 1 process failed immediately (exit code: {process_1.returncode})")
                logger.error(f"❌ Camera 1 stderr: {process_1.stderr.read().decode() if process_1.stderr else 'No error output'}")
                return False
            
            self.recording_processes = [process_0, process_1]
            self.current_booking = booking
            
            logger.info(f"✅ Recording started successfully for both cameras")
            logger.info(f"📁 Output files: {output_file_0.name}, {output_file_1.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
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
        """Check if currently recording"""
        if not self.recording_processes:
            return False
        
        # Check if all processes are still running
        active_processes = []
        for process in self.recording_processes:
            if process.poll() is not None:
                # Process has ended, clean up
                logger.info(f"🔄 Recording process ended (exit code: {process.returncode})")
            else:
                active_processes.append(process)
        
        # Update the recording processes list
        self.recording_processes = active_processes
        
        # If no active processes, clear current booking
        if not self.recording_processes:
            self.current_booking = None
            return False
        
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
    if not recorder.detect_cameras():
        logger.warning("⚠️ Camera detection failed, but continuing...")
    
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
