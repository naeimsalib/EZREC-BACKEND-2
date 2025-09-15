#!/usr/bin/env python3
"""
EZREC Camera Service
Handles all camera operations and recording functionality
"""

import os
import sys
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pytz

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings, get_logger

logger = get_logger(__name__)

class CameraService:
    """Service for camera operations and recording"""
    
    def __init__(self):
        self.recording = False
        self.recording_processes: Dict[int, subprocess.Popen] = {}
        self.recording_threads: Dict[int, threading.Thread] = {}
        self.logger = get_logger(__name__)
    
    def detect_cameras(self) -> List[int]:
        """Detect available cameras using rpicam-vid"""
        available_cameras = []
        
        for index in range(2):
            try:
                # Test camera with rpicam-vid
                result = subprocess.run([
                    'rpicam-vid', '--camera', str(index), '--timeout', '1000', '--output', '/dev/null'
                ], capture_output=True, text=True, timeout=5)
                
                # Check if camera info is in stderr (camera is available)
                if "Available cameras" in result.stderr or "imx477" in result.stderr:
                    available_cameras.append(index)
                    self.logger.info(f"✅ Camera {index} detected")
                else:
                    self.logger.warning(f"⚠️ Camera {index} not available")
            except Exception as e:
                self.logger.warning(f"⚠️ Camera {index} not available: {e}")
        
        self.logger.info(f"📷 Available cameras: {available_cameras}")
        return available_cameras
    
    def record_camera(self, camera_index: int, output_file: Path, booking_id: str) -> bool:
        """Record from a single camera using rpicam-vid"""
        try:
            self.logger.info(f"🔧 Starting recording for camera {camera_index}")
            
            # Use rpicam-vid directly
            cmd = [
                'rpicam-vid',
                '--camera', str(camera_index),
                '--width', str(settings.camera.recording_width),
                '--height', str(settings.camera.recording_height),
                '--framerate', str(settings.camera.recording_framerate),
                '--output', str(output_file),
                '--timeout', str(settings.camera.recording_timeout)
            ]
            
            self.logger.info(f"🎬 Running command: {' '.join(cmd)}")
            
            # Start recording process
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.recording_processes[camera_index] = process
            
            self.logger.info(f"✅ Camera {camera_index} started recording to {output_file}")
            
            # Wait for process to complete or be stopped
            while self.recording and process.poll() is None:
                time.sleep(1)
            
            # Stop the process if still running
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            
            self.logger.info(f"✅ Camera {camera_index} finished recording")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Camera {camera_index} recording failed: {e}")
            return False
    
    def start_recording_session(self, booking_id: str) -> bool:
        """Start recording session for all available cameras"""
        self.logger.info(f"🎬 Starting recording session for booking: {booking_id}")
        
        # Detect cameras
        self.logger.info("🔍 Detecting cameras...")
        available_cameras = self.detect_cameras()
        
        if not available_cameras:
            self.logger.error("❌ No cameras available")
            return False
        
        # Create recordings directory
        today = datetime.now().strftime("%Y-%m-%d")
        session_dir = settings.paths.recordings_path / today / f"session_{booking_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Start recording using threads
        self.recording = True
        
        for camera_index in available_cameras:
            output_file = session_dir / f"camera_{camera_index}.mp4"
            
            # Start recording in a separate thread
            thread = threading.Thread(
                target=self.record_camera,
                args=(camera_index, output_file, booking_id)
            )
            thread.daemon = True
            thread.start()
            
            self.recording_threads[camera_index] = thread
        
        self.logger.info("✅ Recording started successfully")
        return True
    
    def stop_recording_session(self):
        """Stop recording session"""
        if not self.recording:
            return
        
        self.logger.info("🛑 Stopping recording session")
        self.recording = False
        
        # Stop all recording processes
        for camera_index, process in self.recording_processes.items():
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                self.logger.info(f"✅ Camera {camera_index} process stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping camera {camera_index} process: {e}")
        
        # Wait for threads to finish
        for camera_index, thread in self.recording_threads.items():
            try:
                thread.join(timeout=5)
                self.logger.info(f"✅ Camera {camera_index} thread finished")
            except Exception as e:
                self.logger.error(f"❌ Error stopping camera {camera_index} thread: {e}")
        
        self.recording_processes.clear()
        self.recording_threads.clear()
        self.logger.info("✅ Recording stopped")
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.recording
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status"""
        return {
            "recording": self.recording,
            "active_cameras": list(self.recording_processes.keys()),
            "process_count": len(self.recording_processes),
            "thread_count": len(self.recording_threads)
        }
