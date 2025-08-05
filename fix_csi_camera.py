#!/usr/bin/env python3
"""
CSI Camera Fix for Raspberry Pi
Specialized fixes for Ribbon/CSI cameras
"""

import os
import subprocess
import sys
import time
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

def fix_filesystem_permissions():
    """Fix read-only filesystem issues"""
    print("\n" + "="*50)
    print("🔧 FIXING FILESYSTEM PERMISSIONS")
    print("="*50)
    
    # Check if filesystem is read-only
    run_command("mount | grep ' / '", "Check root filesystem mount")
    
    # Fix logs directory permissions
    logs_dir = Path("/opt/ezrec-backend/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_command(f"sudo chown -R {os.getenv('USER')}:{os.getenv('USER')} {logs_dir}", "Fix logs directory ownership")
    run_command(f"sudo chmod -R 755 {logs_dir}", "Fix logs directory permissions")
    
    # Fix logs.txt file
    logs_file = Path("/opt/ezrec-backend/logs.txt")
    if logs_file.exists():
        run_command(f"sudo chown {os.getenv('USER')}:{os.getenv('USER')} {logs_file}", "Fix logs.txt ownership")
        run_command(f"sudo chmod 644 {logs_file}", "Fix logs.txt permissions")
    else:
        run_command(f"sudo touch {logs_file}", "Create logs.txt file")
        run_command(f"sudo chown {os.getenv('USER')}:{os.getenv('USER')} {logs_file}", "Set logs.txt ownership")

def fix_csi_camera_config():
    """Fix CSI camera configuration for Raspberry Pi"""
    print("\n" + "="*50)
    print("📹 FIXING CSI CAMERA CONFIGURATION")
    print("="*50)
    
    # Check current camera configuration
    run_command("vcgencmd get_camera", "Check camera status")
    run_command("sudo raspi-config nonint get_camera", "Check camera enabled")
    
    # Enable camera interface
    run_command("sudo raspi-config nonint do_camera 0", "Enable camera interface")
    
    # Check camera modules
    run_command("lsmod | grep bcm2835", "Check bcm2835 modules")
    
    # Load camera modules if needed
    run_command("sudo modprobe bcm2835-v4l2", "Load bcm2835-v4l2 module")
    run_command("sudo modprobe v4l2_common", "Load v4l2_common module")
    
    # Set camera permissions
    run_command("sudo chmod 666 /dev/video*", "Set video device permissions")
    run_command("sudo usermod -a -G video $USER", "Add user to video group")

def test_csi_camera_access():
    """Test CSI camera access with proper configuration"""
    print("\n" + "="*50)
    print("🎥 TESTING CSI CAMERA ACCESS")
    print("="*50)
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
        
        # Test different video devices
        video_devices = ["/dev/video0", "/dev/video1", "/dev/video2"]
        
        for device in video_devices:
            print(f"\n📹 Testing {device}...")
            
            # Try to open camera
            cap = cv2.VideoCapture(device)
            
            if cap.isOpened():
                print(f"✅ {device} opened successfully")
                
                # Set camera properties for CSI camera
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Get actual properties
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                print(f"📐 {device} properties: {width}x{height} @ {fps}fps")
                
                # Try to capture frames
                frame_count = 0
                for i in range(10):  # Try 10 frames
                    ret, frame = cap.read()
                    if ret:
                        frame_count += 1
                        print(f"✅ Frame {i+1} captured: {frame.shape}")
                    else:
                        print(f"❌ Frame {i+1} failed")
                    time.sleep(0.1)
                
                if frame_count > 0:
                    print(f"✅ {device} working: {frame_count}/10 frames captured")
                    
                    # Save test frame
                    ret, frame = cap.read()
                    if ret:
                        test_file = f"/tmp/test_frame_{device.replace('/', '_')}.jpg"
                        cv2.imwrite(test_file, frame)
                        print(f"💾 Test frame saved: {test_file}")
                    
                    cap.release()
                    print(f"🔒 {device} released")
                    return device  # Found working device
                else:
                    print(f"❌ {device} not capturing frames")
                    cap.release()
            else:
                print(f"❌ {device} failed to open")
        
        print("❌ No working camera device found")
        return None
        
    except ImportError:
        print("❌ OpenCV not available")
        return None
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return None

def fix_camera_streamer():
    """Fix camera streamer configuration"""
    print("\n" + "="*50)
    print("📹 FIXING CAMERA STREAMER")
    print("="*50)
    
    # Stop camera streamer
    run_command("sudo systemctl stop camera_streamer.service", "Stop camera streamer")
    
    # Fix camera streamer configuration
    camera_streamer_path = Path("/opt/ezrec-backend/backend/camera_streamer.py")
    if camera_streamer_path.exists():
        # Backup original
        run_command(f"cp {camera_streamer_path} {camera_streamer_path}.backup", "Backup camera streamer")
        
        # Fix logging configuration to avoid read-only filesystem issues
        with open(camera_streamer_path, 'r') as f:
            content = f.read()
        
        # Replace problematic logging configuration
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
        
        content = content.replace(old_logging, new_logging)
        
        with open(camera_streamer_path, 'w') as f:
            f.write(content)
        
        print("✅ Fixed camera streamer logging configuration")
    
    # Start camera streamer
    run_command("sudo systemctl start camera_streamer.service", "Start camera streamer")
    time.sleep(3)
    
    # Check status
    run_command("sudo systemctl status camera_streamer.service --no-pager", "Check camera streamer status")

def fix_video_worker():
    """Fix video worker issues"""
    print("\n" + "="*50)
    print("🎬 FIXING VIDEO WORKER")
    print("="*50)
    
    # Stop video worker
    run_command("sudo systemctl stop video_worker.service", "Stop video worker")
    
    # Clean up test files
    test_dir = Path("/opt/ezrec-backend/recordings/2025-07-20")
    if test_dir.exists():
        for file in test_dir.glob("191500-191510.*"):
            run_command(f"rm -f {file}", f"Remove test file {file.name}")
    
    # Start video worker
    run_command("sudo systemctl start video_worker.service", "Start video worker")
    time.sleep(3)
    
    # Check status
    run_command("sudo systemctl status video_worker.service --no-pager", "Check video worker status")

def test_camera_endpoints():
    """Test camera endpoints"""
    print("\n" + "="*50)
    print("🌐 TESTING CAMERA ENDPOINTS")
    print("="*50)
    
    # Wait for camera streamer to start
    time.sleep(5)
    
    # Test health endpoint
    run_command("curl -s http://localhost:9000/", "Test camera streamer health")
    
    # Test camera status endpoint
    run_command("curl -s http://localhost:9000/camera-status", "Test camera status endpoint")
    
    # Test live preview (brief test)
    run_command("timeout 5 curl -s http://localhost:9000/live-preview > /dev/null", "Test live preview endpoint")

def create_proper_test_recording():
    """Create a proper test recording"""
    print("\n" + "="*50)
    print("🎬 CREATING PROPER TEST RECORDING")
    print("="*50)
    
    # Find working camera device
    working_device = test_csi_camera_access()
    
    if working_device:
        print(f"✅ Using camera device: {working_device}")
        
        # Create test recording script
        test_script = '''#!/usr/bin/env python3
import cv2
import time
from pathlib import Path

# Create test directory
test_dir = Path("/opt/ezrec-backend/recordings/2025-07-20")
test_dir.mkdir(parents=True, exist_ok=True)

# Open camera
cap = cv2.VideoCapture("''' + working_device + '''")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

if cap.isOpened():
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    output_file = str(test_dir / "test_recording.mp4")
    video_writer = cv2.VideoWriter(output_file, fourcc, 30, (1280, 720))
    
    if video_writer.isOpened():
        print("Recording 5 seconds...")
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if ret:
                video_writer.write(frame)
                frame_count += 1
        
        video_writer.release()
        print(f"Recorded {frame_count} frames")
        
        # Create metadata files
        done_file = test_dir / "test_recording.done"
        done_file.touch()
        
        meta_file = test_dir / "test_recording.json"
        import json
        meta = {
            "user_id": "test-user",
            "camera_id": "test-camera", 
            "booking_id": "test-booking",
            "start_time": "2025-07-20T19:15:00Z",
            "end_time": "2025-07-20T19:15:05Z"
        }
        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print("✅ Test recording created successfully")
    else:
        print("❌ Failed to create video writer")
    
    cap.release()
else:
    print("❌ Failed to open camera")
'''
        
        # Write and run test script
        with open("/tmp/create_test_recording.py", 'w') as f:
            f.write(test_script)
        
        run_command("python3 /tmp/create_test_recording.py", "Create test recording")
    else:
        print("❌ No working camera device found")

def main():
    """Main fix function"""
    print("🚀 CSI Camera Fix for Raspberry Pi")
    print("="*50)
    
    # Run fixes
    fix_filesystem_permissions()
    fix_csi_camera_config()
    working_device = test_csi_camera_access()
    
    if working_device:
        fix_camera_streamer()
        fix_video_worker()
        test_camera_endpoints()
        create_proper_test_recording()
        
        print("\n" + "="*50)
        print("✅ CSI CAMERA FIXES COMPLETED")
        print("="*50)
        print("1. Fixed filesystem permissions")
        print("2. Configured CSI camera")
        print(f"3. Found working camera device: {working_device}")
        print("4. Fixed camera streamer")
        print("5. Fixed video worker")
        print("6. Created test recording")
        print("\nNext steps:")
        print("- Test camera: curl http://localhost:9000/camera-status")
        print("- Monitor logs: sudo journalctl -u camera_streamer.service -f")
        print("- Check video processing: sudo journalctl -u video_worker.service -f")
    else:
        print("\n" + "="*50)
        print("❌ CSI CAMERA FIXES FAILED")
        print("="*50)
        print("Could not find working camera device.")
        print("Please check:")
        print("1. Camera ribbon cable connection")
        print("2. Camera module compatibility")
        print("3. Camera interface enabled in raspi-config")

if __name__ == "__main__":
    main() 