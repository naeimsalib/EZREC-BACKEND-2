#!/usr/bin/env python3
"""
EZREC Camera Diagnostics Script
- Checks camera hardware and software status
- Identifies common issues and provides solutions
- Tests camera functionality
"""
import os
import sys
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("camera_diagnostics")

def run_command(cmd, capture_output=True):
    """Run a command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_system_info():
    """Check basic system information"""
    logger.info("=== System Information ===")
    
    # Check OS
    success, output, error = run_command("cat /etc/os-release | grep PRETTY_NAME")
    if success:
        logger.info(f"OS: {output.strip()}")
    
    # Check kernel
    success, output, error = run_command("uname -r")
    if success:
        logger.info(f"Kernel: {output.strip()}")
    
    # Check CPU
    success, output, error = run_command("cat /proc/cpuinfo | grep Model")
    if success:
        logger.info(f"CPU: {output.strip()}")

def check_camera_hardware():
    """Check camera hardware status"""
    logger.info("\n=== Camera Hardware Check ===")
    
    # Check if camera device exists
    if os.path.exists('/dev/video0'):
        logger.info("✅ Camera device /dev/video0 found")
    else:
        logger.error("❌ Camera device /dev/video0 not found")
        return False
    
    # Check camera permissions
    success, output, error = run_command("ls -la /dev/video*")
    if success:
        logger.info("Camera device permissions:")
        logger.info(output)
    
    # Check if user is in video group
    success, output, error = run_command("groups")
    if success and "video" in output:
        logger.info("✅ User is in video group")
    else:
        logger.warning("⚠️ User is not in video group")
        logger.info("Run: sudo usermod -a -G video $USER")
    
    return True

def check_camera_processes():
    """Check for camera-related processes"""
    logger.info("\n=== Camera Process Check ===")
    
    # Check for picamera2 processes
    success, output, error = run_command("ps aux | grep -i picamera")
    if success and output.strip():
        logger.warning("⚠️ Found picamera2 processes:")
        logger.info(output)
    else:
        logger.info("✅ No picamera2 processes found")
    
    # Check for camera_streamer processes
    success, output, error = run_command("ps aux | grep -i camera_streamer")
    if success and output.strip():
        logger.warning("⚠️ Found camera_streamer processes:")
        logger.info(output)
    else:
        logger.info("✅ No camera_streamer processes found")
    
    # Check what's using /dev/video0
    success, output, error = run_command("lsof /dev/video0")
    if success and output.strip():
        logger.warning("⚠️ Processes using /dev/video0:")
        logger.info(output)
    else:
        logger.info("✅ No processes using /dev/video0")

def check_camera_libraries():
    """Check camera library installation"""
    logger.info("\n=== Camera Library Check ===")
    
    # Check picamera2 installation
    try:
        import picamera2
        logger.info("✅ picamera2 library is installed")
    except ImportError:
        logger.error("❌ picamera2 library not found")
        logger.info("Install with: sudo apt install python3-picamera2")
        return False
    
    # Check OpenCV
    try:
        import cv2
        logger.info("✅ OpenCV library is installed")
    except ImportError:
        logger.error("❌ OpenCV library not found")
        logger.info("Install with: pip install opencv-python")
        return False
    
    # Check PIL
    try:
        from PIL import Image
        logger.info("✅ PIL/Pillow library is installed")
    except ImportError:
        logger.error("❌ PIL/Pillow library not found")
        logger.info("Install with: pip install Pillow")
        return False
    
    return True

def test_camera_functionality():
    """Test basic camera functionality"""
    logger.info("\n=== Camera Functionality Test ===")
    
    try:
        from picamera2 import Picamera2
        import numpy as np
        
        logger.info("Initializing camera...")
        picam2 = Picamera2()
        
        # Create configuration
        config = picam2.create_video_configuration(
            main={"size": (1280, 720), "format": "RGB888"},
            controls={"FrameRate": 30}
        )
        picam2.configure(config)
        
        logger.info("Starting camera...")
        picam2.start()
        
        # Wait a moment for camera to stabilize
        time.sleep(2)
        
        # Capture a test frame
        logger.info("Capturing test frame...")
        frame = picam2.capture_array()
        
        if frame is not None and frame.size > 0:
            # Check if frame is not completely black
            mean_value = np.mean(frame)
            logger.info(f"Frame captured successfully. Mean pixel value: {mean_value:.2f}")
            
            if mean_value > 1.0:
                logger.info("✅ Camera is working correctly")
                result = True
            else:
                logger.warning("⚠️ Camera captured black frame - possible hardware issue")
                result = False
        else:
            logger.error("❌ Failed to capture frame")
            result = False
        
        # Stop camera
        picam2.stop()
        return result
        
    except Exception as e:
        logger.error(f"❌ Camera test failed: {e}")
        return False

def check_systemd_services():
    """Check systemd service status"""
    logger.info("\n=== Systemd Service Check ===")
    
    services = ['camera_streamer', 'recorder', 'video_worker', 'status_updater']
    
    for service in services:
        success, output, error = run_command(f"systemctl is-active {service}.service")
        if success:
            status = output.strip()
            if status == "active":
                logger.info(f"✅ {service}.service is active")
            else:
                logger.warning(f"⚠️ {service}.service is {status}")
        else:
            logger.error(f"❌ Could not check {service}.service status")

def kill_camera_processes():
    """Kill any camera-related processes"""
    logger.info("\n=== Killing Camera Processes ===")
    
    commands = [
        "pkill -f picamera2",
        "pkill -f camera_streamer",
        "pkill -f recorder",
        "sudo systemctl stop camera_streamer.service"
    ]
    
    for cmd in commands:
        success, output, error = run_command(cmd)
        if success:
            logger.info(f"✅ Executed: {cmd}")
        else:
            logger.info(f"ℹ️ Command completed: {cmd}")

def provide_solutions():
    """Provide common solutions"""
    logger.info("\n=== Common Solutions ===")
    
    logger.info("1. If camera device not found:")
    logger.info("   - Check camera cable connection")
    logger.info("   - Enable camera in raspi-config")
    logger.info("   - Reboot: sudo reboot")
    
    logger.info("\n2. If camera shows black frames:")
    logger.info("   - Check camera lens cover")
    logger.info("   - Ensure adequate lighting")
    logger.info("   - Check camera focus")
    
    logger.info("\n3. If camera is locked by another process:")
    logger.info("   - Run: sudo pkill -f picamera2")
    logger.info("   - Run: sudo systemctl restart camera_streamer.service")
    
    logger.info("\n4. If user not in video group:")
    logger.info("   - Run: sudo usermod -a -G video $USER")
    logger.info("   - Logout and login again")
    
    logger.info("\n5. If libraries missing:")
    logger.info("   - Run: sudo apt update && sudo apt install python3-picamera2")
    logger.info("   - Run: pip install opencv-python Pillow")

def main():
    """Main diagnostic function"""
    logger.info("EZREC Camera Diagnostics")
    logger.info("=" * 50)
    
    # Check system info
    check_system_info()
    
    # Check hardware
    hardware_ok = check_camera_hardware()
    
    # Check processes
    check_camera_processes()
    
    # Check libraries
    libraries_ok = check_camera_libraries()
    
    # Check services
    check_systemd_services()
    
    # Test camera if everything else is OK
    if hardware_ok and libraries_ok:
        logger.info("\n" + "=" * 50)
        logger.info("Testing camera functionality...")
        camera_ok = test_camera_functionality()
        
        if not camera_ok:
            logger.info("\n" + "=" * 50)
            logger.info("Camera test failed. Would you like to:")
            logger.info("1. Kill all camera processes and retry")
            logger.info("2. View solutions")
            logger.info("3. Exit")
            
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == "1":
                kill_camera_processes()
                time.sleep(3)
                logger.info("Retesting camera...")
                test_camera_functionality()
            elif choice == "2":
                provide_solutions()
    else:
        logger.info("\n" + "=" * 50)
        logger.info("Hardware or library issues detected. Viewing solutions...")
        provide_solutions()
    
    logger.info("\n" + "=" * 50)
    logger.info("Diagnostics complete!")

if __name__ == "__main__":
    main() 