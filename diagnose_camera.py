#!/usr/bin/env python3
"""
EZREC Camera Diagnostic Script
Run this on the Raspberry Pi to diagnose camera issues
"""

import os
import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and return result"""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception: {e}")
        return False

def check_camera_modules():
    """Check if camera modules are loaded"""
    print("\n" + "="*50)
    print("📹 CAMERA MODULE DIAGNOSTICS")
    print("="*50)
    
    # Check loaded modules
    run_command("lsmod | grep -i camera", "Loaded camera modules")
    run_command("lsmod | grep -i v4l", "V4L2 modules")
    run_command("lsmod | grep -i bcm", "Broadcom camera modules")
    
    # Check if modules can be loaded
    run_command("sudo modprobe bcm2835-v4l2", "Load bcm2835-v4l2 module")
    run_command("sudo modprobe v4l2_common", "Load v4l2_common module")
    
    # Check again after loading
    time.sleep(2)
    run_command("lsmod | grep -i camera", "Camera modules after loading")
    run_command("lsmod | grep -i v4l", "V4L2 modules after loading")

def check_video_devices():
    """Check for video devices"""
    print("\n" + "="*50)
    print("📹 VIDEO DEVICE DIAGNOSTICS")
    print("="*50)
    
    run_command("ls -la /dev/video*", "Video devices")
    run_command("ls -la /dev/media*", "Media devices")
    run_command("v4l2-ctl --list-devices", "V4L2 device list")
    
    # Check specific device if it exists
    if os.path.exists("/dev/video0"):
        run_command("v4l2-ctl -d /dev/video0 --list-formats-ext", "Video0 formats")
        run_command("v4l2-ctl -d /dev/video0 --list-ctrls", "Video0 controls")

def check_camera_permissions():
    """Check camera permissions"""
    print("\n" + "="*50)
    print("🔐 CAMERA PERMISSIONS DIAGNOSTICS")
    print("="*50)
    
    run_command("groups $USER", "Current user groups")
    run_command("ls -la /dev/video*", "Video device permissions")
    run_command("sudo usermod -a -G video $USER", "Add user to video group")
    
    # Check if user is in video group
    result = subprocess.run("groups $USER", shell=True, capture_output=True, text=True)
    if "video" in result.stdout:
        print("✅ User is in video group")
    else:
        print("❌ User is NOT in video group")

def test_opencv_camera():
    """Test OpenCV camera access"""
    print("\n" + "="*50)
    print("🎥 OPENCV CAMERA TEST")
    print("="*50)
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
        
        # Try to open camera
        print("📹 Attempting to open camera with OpenCV...")
        cap = cv2.VideoCapture(0)
        
        if cap.isOpened():
            print("✅ Camera opened successfully")
            
            # Get camera properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"📐 Camera properties: {width}x{height} @ {fps}fps")
            
            # Try to capture a frame
            ret, frame = cap.read()
            if ret:
                print(f"✅ Frame captured successfully: {frame.shape}")
                
                # Save test frame
                cv2.imwrite("/tmp/test_frame.jpg", frame)
                print("💾 Test frame saved to /tmp/test_frame.jpg")
            else:
                print("❌ Failed to capture frame")
            
            cap.release()
            print("🔒 Camera released")
        else:
            print("❌ Failed to open camera")
            
    except ImportError:
        print("❌ OpenCV not available")
    except Exception as e:
        print(f"❌ OpenCV test failed: {e}")

def check_system_info():
    """Check system information"""
    print("\n" + "="*50)
    print("💻 SYSTEM INFORMATION")
    print("="*50)
    
    run_command("uname -a", "System info")
    run_command("cat /proc/cpuinfo | grep Model", "CPU model")
    run_command("vcgencmd get_camera", "Camera info")
    run_command("vcgencmd get_mem gpu", "GPU memory")

def fix_camera_setup():
    """Attempt to fix camera setup"""
    print("\n" + "="*50)
    print("🔧 ATTEMPTING CAMERA FIXES")
    print("="*50)
    
    # Load camera modules
    run_command("sudo modprobe bcm2835-v4l2", "Load bcm2835-v4l2")
    run_command("sudo modprobe v4l2_common", "Load v4l2_common")
    
    # Set permissions
    run_command("sudo chmod 666 /dev/video*", "Set video device permissions")
    run_command("sudo usermod -a -G video $USER", "Add user to video group")
    
    # Enable camera in config
    run_command("sudo raspi-config nonint get_camera", "Check camera enabled")
    
    print("\n⚠️  If camera is not enabled, run: sudo raspi-config")
    print("   Navigate to: Interface Options > Camera > Enable")

def main():
    """Main diagnostic function"""
    print("🚀 EZREC Camera Diagnostic Tool")
    print("="*50)
    
    # Check if running as root
    if os.geteuid() == 0:
        print("⚠️  Running as root - some tests may not work correctly")
    
    # Run diagnostics
    check_system_info()
    check_camera_modules()
    check_video_devices()
    check_camera_permissions()
    test_opencv_camera()
    
    # Attempt fixes
    fix_camera_setup()
    
    print("\n" + "="*50)
    print("📋 SUMMARY")
    print("="*50)
    print("1. Check if camera modules are loaded")
    print("2. Verify video devices exist")
    print("3. Ensure user is in video group")
    print("4. Test OpenCV camera access")
    print("5. If issues persist, run: sudo raspi-config")
    print("   Enable camera in Interface Options")

if __name__ == "__main__":
    main() 