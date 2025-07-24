#!/usr/bin/env python3
"""
Test camera functionality and restart services.
"""

import time
import subprocess
import sys
from picamera2 import Picamera2
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def stop_services():
    """Stop all EZREC services."""
    logger.info("Stopping all EZREC services...")
    services = [
        "recorder",
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
    """Kill any processes using the camera."""
    logger.info("Killing any processes using the camera...")
    try:
        subprocess.run(["sudo", "fuser", "-k", "/dev/video0"], check=False)
        time.sleep(2)  # Give processes time to die
    except Exception as e:
        logger.error(f"Error killing camera processes: {e}")

def test_camera():
    """Test the camera by opening it and showing preview."""
    logger.info("Testing camera...")
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration()
        picam2.configure(config)
        picam2.start()
        logger.info("📸 Camera opened successfully! Waiting 5 seconds...")
        time.sleep(5)
        picam2.stop()
        picam2.close()
        logger.info("✅ Camera test successful and camera properly released")
        return True
    except Exception as e:
        logger.error(f"❌ Camera test failed: {e}")
        return False

def restart_services():
    """Restart all EZREC services in correct order."""
    logger.info("Starting services in order...")
    services = [
        "recorder",
        "video_worker",
        "status_updater"
    ]
    for service in services:
        try:
            subprocess.run(["sudo", "systemctl", "restart", service], check=True)
            # Give each service time to initialize
            time.sleep(2)
            # Check service status
            result = subprocess.run(["sudo", "systemctl", "is-active", service], 
                                 capture_output=True, text=True)
            if result.stdout.strip() == "active":
                logger.info(f"✅ Started {service}")
            else:
                logger.error(f"❌ {service} failed to start properly")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to start {service}: {e}")

def main():
    logger.info("Starting camera test sequence...")
    
    # 1. Stop all services
    stop_services()
    
    # 2. Kill any remaining camera processes
    kill_camera_processes()
    
    # 3. Test camera
    if not test_camera():
        logger.error("Camera test failed! Check camera connection and permissions.")
        sys.exit(1)
    
    # 4. Restart services
    restart_services()
    
    logger.info("✨ Camera test sequence completed!")
    logger.info("📝 Check service logs for any issues:")
    logger.info("   sudo journalctl -u recorder.service -f")

if __name__ == "__main__":
    main() 