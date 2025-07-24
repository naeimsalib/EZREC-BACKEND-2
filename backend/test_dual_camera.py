#!/usr/bin/env python3
"""
Test dual camera functionality
"""

import time
import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Camera configuration
CAMERA_0_SERIAL = os.getenv('CAMERA_0_SERIAL', '88000')
CAMERA_1_SERIAL = os.getenv('CAMERA_1_SERIAL', '80000')
CAMERA_0_NAME = os.getenv('CAMERA_0_NAME', 'left')
CAMERA_1_NAME = os.getenv('CAMERA_1_NAME', 'right')

def stop_services():
    """Stop all EZREC services."""
    logger.info("Stopping all EZREC services...")
    services = [
        "recorder",
        "dual_recorder",
        "video_worker",
        "status_updater"
    ]
    for service in services:
        try:
            subprocess.run(["sudo", "systemctl", "stop", service], check=True)
            logger.info(f"✅ Stopped {service}")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to stop {service}: {e}")

def kill_camera_processes():
    """Kill any processes using the cameras."""
    logger.info("Killing any processes using the cameras...")
    try:
        # Kill processes using any video device
        for i in range(20):  # Check video0 through video19
            subprocess.run(["sudo", "fuser", "-k", f"/dev/video{i}"], check=False)
        time.sleep(3)  # Give processes time to die
    except Exception as e:
        logger.error(f"Error killing camera processes: {e}")

def test_dual_camera():
    """Test both cameras by opening them simultaneously."""
    logger.info("Testing dual camera setup...")
    
    try:
        from picamera2 import Picamera2
        
        # Test camera 0
        logger.info(f"📷 Testing {CAMERA_0_NAME} camera (Serial: {CAMERA_0_SERIAL})...")
        camera0 = Picamera2()
        config0 = camera0.create_preview_configuration()
        camera0.configure(config0)
        camera0.start()
        logger.info(f"✅ {CAMERA_0_NAME} camera opened successfully")
        
        # Test camera 1
        logger.info(f"📷 Testing {CAMERA_1_NAME} camera (Serial: {CAMERA_1_SERIAL})...")
        camera1 = Picamera2()
        config1 = camera1.create_preview_configuration()
        camera1.configure(config1)
        camera1.start()
        logger.info(f"✅ {CAMERA_1_NAME} camera opened successfully")
        
        # Both cameras are now active
        logger.info("🎬 Both cameras are active! Waiting 5 seconds...")
        time.sleep(5)
        
        # Close cameras
        camera0.stop()
        camera0.close()
        camera1.stop()
        camera1.close()
        
        logger.info("✅ Dual camera test successful and cameras properly released")
        return True
        
    except Exception as e:
        logger.error(f"❌ Dual camera test failed: {e}")
        return False

def test_merge_functionality():
    """Test video merging functionality."""
    logger.info("Testing video merge functionality...")
    
    # Create test video files (if they don't exist)
    test_dir = Path("/tmp/dual_camera_test")
    test_dir.mkdir(exist_ok=True)
    
    video1 = test_dir / "test_video1.mp4"
    video2 = test_dir / "test_video2.mp4"
    merged = test_dir / "test_merged.mp4"
    
    # Create simple test videos using FFmpeg
    try:
        # Create a 5-second test video for camera 1
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=640x480:rate=30',
            '-c:v', 'libx264', '-preset', 'ultrafast', str(video1)
        ], capture_output=True, check=True)
        
        # Create a 5-second test video for camera 2
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc2=duration=5:size=640x480:rate=30',
            '-c:v', 'libx264', '-preset', 'ultrafast', str(video2)
        ], capture_output=True, check=True)
        
        logger.info("✅ Created test video files")
        
        # Test side-by-side merge
        logger.info("Testing side-by-side merge...")
        result = subprocess.run([
            'ffmpeg', '-y',
            '-i', str(video1),
            '-i', str(video2),
            '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
            '-map', '[v]',
            '-map', '0:a',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            str(merged)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and merged.exists():
            logger.info("✅ Side-by-side merge test successful")
            # Clean up test files
            video1.unlink(missing_ok=True)
            video2.unlink(missing_ok=True)
            merged.unlink(missing_ok=True)
            test_dir.rmdir()
            return True
        else:
            logger.error(f"❌ Merge test failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing merge functionality: {e}")
        return False

def restart_services():
    """Restart EZREC services."""
    logger.info("Starting EZREC services...")
    services = [
        "dual_recorder",
        "video_worker",
        "status_updater"
    ]
    for service in services:
        try:
            subprocess.run(["sudo", "systemctl", "restart", service], check=True)
            time.sleep(2)
            result = subprocess.run(["sudo", "systemctl", "is-active", service], 
                                 capture_output=True, text=True)
            if result.stdout.strip() == "active":
                logger.info(f"✅ Started {service}")
            else:
                logger.error(f"❌ {service} failed to start properly")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start {service}: {e}")

def main():
    logger.info("🎬 Starting dual camera test sequence...")
    logger.info(f"📷 Camera 0: {CAMERA_0_NAME} (Serial: {CAMERA_0_SERIAL})")
    logger.info(f"📷 Camera 1: {CAMERA_1_NAME} (Serial: {CAMERA_1_SERIAL})")
    
    # 1. Stop all services
    stop_services()
    
    # 2. Kill any remaining camera processes
    kill_camera_processes()
    
    # 3. Test dual camera functionality
    if not test_dual_camera():
        logger.error("❌ Dual camera test failed! Check camera connections and permissions.")
        sys.exit(1)
    
    # 4. Test merge functionality
    if not test_merge_functionality():
        logger.error("❌ Merge functionality test failed! Check FFmpeg installation.")
        sys.exit(1)
    
    # 5. Restart services
    restart_services()
    
    logger.info("✨ Dual camera test sequence completed!")
    logger.info("📝 Check service logs for any issues:")
    logger.info("   sudo journalctl -u dual_recorder.service -f")
    logger.info("")
    logger.info("🎬 Your dual camera setup is ready!")
    logger.info("📹 Both cameras will record simultaneously and merge into one video.")

if __name__ == "__main__":
    main() 