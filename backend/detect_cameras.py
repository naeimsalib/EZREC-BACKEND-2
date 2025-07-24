#!/usr/bin/env python3
"""
Camera Detection Script
- Detects all cameras on the Raspberry Pi
- Shows serial numbers, capabilities, and device paths
- Helps configure dual camera setups
"""

import subprocess
import json
import sys
from pathlib import Path

def run_command(cmd, timeout=10):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def detect_cameras():
    """Detect all cameras using libcamera-hello"""
    print("🔍 Detecting cameras using libcamera-hello...")
    success, output, error = run_command(['libcamera-hello', '--list-cameras'])
    
    if not success:
        print(f"❌ Failed to detect cameras: {error}")
        return []
    
    cameras = []
    lines = output.split('\n')
    current_camera = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_camera:
                cameras.append(current_camera)
                current_camera = {}
            continue
            
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key.lower() in ['model', 'serial', 'bus info']:
                current_camera[key.lower()] = value
        elif line.startswith('Camera'):
            if current_camera:
                cameras.append(current_camera)
            current_camera = {'name': line}
    
    if current_camera:
        cameras.append(current_camera)
    
    return cameras

def check_video_devices():
    """Check available video devices"""
    print("\n📹 Checking video devices...")
    video_devices = []
    
    for i in range(10):  # Check /dev/video0 through /dev/video9
        device = f"/dev/video{i}"
        if Path(device).exists():
            # Get device info
            success, output, error = run_command(['v4l2-ctl', '--device', device, '--all'])
            if success:
                video_devices.append({
                    'device': device,
                    'info': output
                })
    
    return video_devices

def check_i2c_devices():
    """Check I2C devices"""
    print("\n🔌 Checking I2C devices...")
    i2c_devices = []
    
    # Check I2C bus 1 (most common for cameras)
    success, output, error = run_command(['i2cdetect', '-y', '1'])
    if success:
        i2c_devices.append({
            'bus': 1,
            'output': output
        })
    
    # Check I2C bus 0
    success, output, error = run_command(['i2cdetect', '-y', '0'])
    if success:
        i2c_devices.append({
            'bus': 0,
            'output': output
        })
    
    return i2c_devices

def check_camera_config():
    """Check camera configuration"""
    print("\n⚙️ Checking camera configuration...")
    
    # Check /boot/config.txt
    config_path = Path('/boot/config.txt')
    if config_path.exists():
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        camera_lines = [line.strip() for line in config_content.split('\n') 
                       if 'camera' in line.lower() or 'i2c' in line.lower()]
        
        return camera_lines
    
    return []

def main():
    print("🎥 EZREC Camera Detection Tool")
    print("=" * 50)
    
    # Detect cameras
    cameras = detect_cameras()
    
    if cameras:
        print(f"\n✅ Found {len(cameras)} camera(s):")
        for i, camera in enumerate(cameras, 1):
            print(f"\n📷 Camera {i}:")
            for key, value in camera.items():
                print(f"  {key}: {value}")
    else:
        print("\n❌ No cameras detected")
    
    # Check video devices
    video_devices = check_video_devices()
    if video_devices:
        print(f"\n✅ Found {len(video_devices)} video device(s):")
        for device in video_devices:
            print(f"\n📹 {device['device']}:")
            # Extract key info
            info_lines = device['info'].split('\n')
            for line in info_lines[:10]:  # Show first 10 lines
                if any(keyword in line.lower() for keyword in ['driver', 'card', 'bus', 'version']):
                    print(f"  {line.strip()}")
    else:
        print("\n❌ No video devices found")
    
    # Check I2C devices
    i2c_devices = check_i2c_devices()
    if i2c_devices:
        print(f"\n✅ Found {len(i2c_devices)} I2C bus(es):")
        for i2c in i2c_devices:
            print(f"\n🔌 I2C Bus {i2c['bus']}:")
            print(i2c['output'])
    else:
        print("\n❌ No I2C devices found")
    
    # Check camera config
    config_lines = check_camera_config()
    if config_lines:
        print(f"\n⚙️ Camera configuration in /boot/config.txt:")
        for line in config_lines:
            print(f"  {line}")
    else:
        print("\n❌ No camera configuration found in /boot/config.txt")
    
    # Recommendations
    print("\n" + "=" * 50)
    print("💡 RECOMMENDATIONS:")
    
    if len(cameras) > 1:
        print("⚠️  DUAL CAMERA DETECTED:")
        print("   - Configure each camera with a unique serial number")
        print("   - Add CAMERA_SERIAL to your .env file")
        print("   - Consider reducing bitrate and resolution for stability")
        print("   - Monitor system resources (CPU, memory, temperature)")
        
        print("\n🔧 For dual camera setup, add to your .env file:")
        print("   CAMERA_SERIAL=<serial_number_of_primary_camera>")
        
        if cameras:
            print("\n📋 Available camera serials:")
            for i, camera in enumerate(cameras, 1):
                serial = camera.get('serial', 'Unknown')
                model = camera.get('model', 'Unknown')
                print(f"   Camera {i}: {model} (Serial: {serial})")
    
    elif len(cameras) == 1:
        print("✅ Single camera detected - should work normally")
    else:
        print("❌ No cameras detected - check connections and drivers")
    
    print("\n🔧 To fix dual camera issues:")
    print("   1. Add unique serial numbers to each camera")
    print("   2. Configure one camera at a time")
    print("   3. Reduce bitrate and resolution")
    print("   4. Add cooling if temperature is high")
    print("   5. Consider using separate Pis for multiple cameras")

if __name__ == "__main__":
    main() 