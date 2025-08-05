#!/usr/bin/env python3
"""
Targeted Camera Streamer Fix
Fixes the read-only filesystem issue and camera configuration
"""

import os
import subprocess
import sys
from pathlib import Path

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

def fix_camera_streamer_logging():
    """Fix the camera streamer logging configuration"""
    print("\n" + "="*50)
    print("🔧 FIXING CAMERA STREAMER LOGGING")
    print("="*50)
    
    # Stop camera streamer
    run_command("sudo systemctl stop camera_streamer.service", "Stop camera streamer")
    
    # Fix camera streamer configuration
    camera_streamer_path = Path("/opt/ezrec-backend/backend/camera_streamer.py")
    if camera_streamer_path.exists():
        print("📝 Fixing camera streamer logging configuration...")
        
        # Read the file
        with open(camera_streamer_path, 'r') as f:
            content = f.read()
        
        # Remove the problematic logs.txt handler
        old_logging = '''logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/opt/ezrec-backend/logs/camera_streamer.log"),
        logging.FileHandler("/opt/ezrec-backend/logs.txt", mode='a'),
        logging.StreamHandler()
    ]
)'''
        
        new_logging = '''logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/opt/ezrec-backend/logs/camera_streamer.log"),
        logging.StreamHandler()
    ]
)'''
        
        if old_logging in content:
            content = content.replace(old_logging, new_logging)
            
            # Write the fixed content
            with open(camera_streamer_path, 'w') as f:
                f.write(content)
            
            print("✅ Fixed camera streamer logging configuration")
        else:
            print("⚠️ Logging configuration not found, checking for other patterns...")
            
            # Try alternative pattern
            alt_old = 'logging.FileHandler("/opt/ezrec-backend/logs.txt", mode=\'a\')'
            if alt_old in content:
                content = content.replace(alt_old, '# ' + alt_old + '  # Disabled due to read-only filesystem')
                with open(camera_streamer_path, 'w') as f:
                    f.write(content)
                print("✅ Commented out problematic logs.txt handler")
            else:
                print("❌ Could not find logging configuration to fix")
    
    # Start camera streamer
    run_command("sudo systemctl start camera_streamer.service", "Start camera streamer")
    import time
    time.sleep(3)
    
    # Check status
    run_command("sudo systemctl status camera_streamer.service --no-pager", "Check camera streamer status")

def fix_camera_hardware():
    """Fix camera hardware configuration"""
    print("\n" + "="*50)
    print("📹 FIXING CAMERA HARDWARE CONFIGURATION")
    print("="*50)
    
    # Check if camera is properly connected
    run_command("v4l2-ctl --list-devices", "List V4L2 devices")
    
    # Check camera formats
    run_command("v4l2-ctl -d /dev/video0 --list-formats-ext", "Check video0 formats")
    
    # Try to set camera format
    run_command("v4l2-ctl -d /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=YUYV", "Set video0 format")
    
    # Check if camera is working with v4l2-ctl
    run_command("v4l2-ctl -d /dev/video0 --stream-mmap --stream-count=1 --stream-to=/tmp/test.raw", "Test video0 capture")
    
    # Check the captured file
    run_command("ls -la /tmp/test.raw", "Check captured test file")

def test_camera_with_different_methods():
    """Test camera with different methods"""
    print("\n" + "="*50)
    print("🎥 TESTING CAMERA WITH DIFFERENT METHODS")
    print("="*50)
    
    # Test with v4l2-ctl
    print("\n📹 Testing with v4l2-ctl...")
    run_command("v4l2-ctl -d /dev/video0 --stream-mmap --stream-count=5 --stream-to=/tmp/v4l2_test.raw", "V4L2 capture test")
    
    # Test with ffmpeg
    print("\n📹 Testing with ffmpeg...")
    run_command("timeout 5 ffmpeg -f v4l2 -i /dev/video0 -t 3 -y /tmp/ffmpeg_test.mp4", "FFmpeg capture test")
    
    # Test with raspivid (if available)
    print("\n📹 Testing with raspivid...")
    run_command("which raspivid", "Check if raspivid is available")
    if run_command("raspivid -t 3000 -o /tmp/raspivid_test.h264", "Raspivid capture test"):
        print("✅ Raspivid test completed")
    else:
        print("❌ Raspivid test failed")

def create_minimal_camera_test():
    """Create a minimal camera test script"""
    print("\n" + "="*50)
    print("🧪 CREATING MINIMAL CAMERA TEST")
    print("="*50)
    
    test_script = '''#!/usr/bin/env python3
import cv2
import time
import sys

def test_camera(device):
    print(f"Testing {device}...")
    
    # Try different backends
    backends = [
        cv2.CAP_V4L2,
        cv2.CAP_ANY,
        cv2.CAP_FFMPEG
    ]
    
    for backend in backends:
        print(f"  Trying backend: {backend}")
        cap = cv2.VideoCapture(device, backend)
        
        if cap.isOpened():
            print(f"    ✅ {device} opened with backend {backend}")
            
            # Set properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Get properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"    📐 Properties: {width}x{height} @ {fps}fps")
            
            # Try to capture frames
            frame_count = 0
            for i in range(5):
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
                    print(f"    ✅ Frame {i+1}: {frame.shape}")
                else:
                    print(f"    ❌ Frame {i+1}: failed")
                time.sleep(0.1)
            
            if frame_count > 0:
                print(f"    ✅ {device} working: {frame_count}/5 frames")
                cap.release()
                return True
            else:
                print(f"    ❌ {device} not capturing frames")
                cap.release()
        else:
            print(f"    ❌ {device} failed to open with backend {backend}")
    
    return False

# Test multiple devices
devices = ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video3"]
working_device = None

for device in devices:
    if test_camera(device):
        working_device = device
        break

if working_device:
    print(f"\\n✅ Found working camera: {working_device}")
    sys.exit(0)
else:
    print("\\n❌ No working camera found")
    sys.exit(1)
'''
    
    # Write test script
    with open("/tmp/minimal_camera_test.py", 'w') as f:
        f.write(test_script)
    
    # Run test
    run_command("python3 /tmp/minimal_camera_test.py", "Run minimal camera test")

def fix_camera_streamer_config():
    """Fix camera streamer configuration for CSI camera"""
    print("\n" + "="*50)
    print("🔧 FIXING CAMERA STREAMER CONFIGURATION")
    print("="*50)
    
    camera_streamer_path = Path("/opt/ezrec-backend/backend/camera_streamer.py")
    if camera_streamer_path.exists():
        print("📝 Updating camera streamer for CSI camera...")
        
        # Read the file
        with open(camera_streamer_path, 'r') as f:
            content = f.read()
        
        # Update camera device selection
        old_camera_init = '''        self.cap = cv2.VideoCapture(0)  # Use default camera'''
        new_camera_init = '''        # Try multiple camera devices for CSI camera
        camera_devices = [0, "/dev/video0", "/dev/video1", "/dev/video2"]
        self.cap = None
        
        for device in camera_devices:
            try:
                self.cap = cv2.VideoCapture(device)
                if self.cap.isOpened():
                    # Test if we can actually read frames
                    ret, frame = self.cap.read()
                    if ret:
                        print(f"✅ Camera opened successfully with device: {device}")
                        break
                    else:
                        self.cap.release()
                        self.cap = None
                else:
                    if self.cap:
                        self.cap.release()
                        self.cap = None
            except Exception as e:
                print(f"Failed to open camera device {device}: {e}")
                if self.cap:
                    self.cap.release()
                    self.cap = None
        
        if not self.cap or not self.cap.isOpened():
            print("❌ Could not open any camera device")
            self.cap = None'''
        
        if old_camera_init in content:
            content = content.replace(old_camera_init, new_camera_init)
            
            # Write the updated content
            with open(camera_streamer_path, 'w') as f:
                f.write(content)
            
            print("✅ Updated camera streamer for CSI camera")
        else:
            print("⚠️ Camera initialization not found in expected format")

def main():
    """Main fix function"""
    print("🚀 Targeted Camera Streamer Fix")
    print("="*50)
    
    # Run fixes
    fix_camera_streamer_logging()
    fix_camera_hardware()
    test_camera_with_different_methods()
    create_minimal_camera_test()
    fix_camera_streamer_config()
    
    print("\n" + "="*50)
    print("✅ CAMERA STREAMER FIXES COMPLETED")
    print("="*50)
    print("1. Fixed logging configuration")
    print("2. Tested camera hardware")
    print("3. Tested different capture methods")
    print("4. Created minimal camera test")
    print("5. Updated camera streamer configuration")
    print("\nNext steps:")
    print("- Check camera streamer: sudo systemctl status camera_streamer.service")
    print("- Test camera: python3 /tmp/minimal_camera_test.py")
    print("- Monitor logs: sudo journalctl -u camera_streamer.service -f")

if __name__ == "__main__":
    main() 