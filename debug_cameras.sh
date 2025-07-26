#!/bin/bash

echo "🔍 EZREC Camera Debugging Script"
echo "================================="
echo ""

# Check if running on Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  This script should be run on a Raspberry Pi"
    exit 1
fi

echo "📋 System Information:"
echo "======================"
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

echo "📷 Camera Hardware Detection:"
echo "============================="

# Check for v4l2-ctl
if command -v v4l2-ctl >/dev/null 2>&1; then
    echo "✅ v4l2-ctl found"
    echo ""
    echo "📹 Video devices:"
    v4l2-ctl --list-devices
    echo ""
else
    echo "⚠️  v4l2-ctl not found. Installing..."
    sudo apt update && sudo apt install -y v4l-utils
    if command -v v4l2-ctl >/dev/null 2>&1; then
        echo "✅ v4l2-ctl installed successfully"
        echo ""
        echo "📹 Video devices:"
        v4l2-ctl --list-devices
        echo ""
    else
        echo "❌ Failed to install v4l2-ctl"
    fi
fi

echo "🔍 Camera Device Files:"
echo "======================="
ls -la /dev/video* 2>/dev/null || echo "No /dev/video* devices found"
echo ""

echo "📡 I2C Camera Detection:"
echo "======================="
if command -v i2cdetect >/dev/null 2>&1; then
    echo "✅ i2cdetect found"
    echo ""
    echo "🔍 Scanning I2C bus 1:"
    sudo i2cdetect -y 1
    echo ""
    echo "🔍 Scanning I2C bus 0:"
    sudo i2cdetect -y 0
    echo ""
else
    echo "⚠️  i2cdetect not found. Installing..."
    sudo apt update && sudo apt install -y i2c-tools
    if command -v i2cdetect >/dev/null 2>&1; then
        echo "✅ i2cdetect installed successfully"
        echo ""
        echo "🔍 Scanning I2C bus 1:"
        sudo i2cdetect -y 1
        echo ""
        echo "🔍 Scanning I2C bus 0:"
        sudo i2cdetect -y 0
        echo ""
    else
        echo "❌ Failed to install i2c-tools"
    fi
fi

echo "🐍 Python Camera Testing:"
echo "========================"

# Test Picamera2 availability
python3 -c "
try:
    from picamera2 import Picamera2
    print('✅ Picamera2 is available')
    
    # Test camera initialization
    try:
        camera = Picamera2()
        print('✅ Picamera2 camera object created')
        
        # Get camera properties
        props = camera.camera_properties
        print(f'📷 Camera properties: {props}')
        
        # Check for serial number
        if 'SerialNumber' in props:
            print(f'🔢 Camera serial: {props[\"SerialNumber\"]}')
        else:
            print('⚠️  No serial number found in camera properties')
            
        camera.close()
        print('✅ Camera closed successfully')
        
    except Exception as e:
        print(f'❌ Camera initialization failed: {e}')
        
except ImportError as e:
    print(f'❌ Picamera2 not available: {e}')
"

echo ""
echo "🔧 Environment Variables:"
echo "========================"
if [ -f "/opt/ezrec-backend/.env" ]; then
    echo "✅ .env file found"
    echo ""
    echo "📷 Camera configuration:"
    grep -E "CAMERA_[0-9]_SERIAL|CAMERA_[0-9]_NAME|DUAL_CAMERA" /opt/ezrec-backend/.env || echo "No camera config found in .env"
else
    echo "❌ .env file not found at /opt/ezrec-backend/.env"
fi
echo ""

echo "📁 Directory Permissions:"
echo "========================"
echo "Recordings directory:"
ls -la /opt/ezrec-backend/recordings/ 2>/dev/null || echo "Recordings directory not found"
echo ""

echo "Temporary directory:"
ls -la /tmp/ | grep -E "(camera|left|right)" || echo "No camera temp files found"
echo ""

echo "🔍 Recent Camera Debug Logs:"
echo "============================"
if [ -f "/tmp/left_camera_debug.log" ]; then
    echo "📝 Left camera debug log (last 20 lines):"
    tail -20 /tmp/left_camera_debug.log
    echo ""
else
    echo "❌ Left camera debug log not found"
fi

if [ -f "/tmp/right_camera_debug.log" ]; then
    echo "📝 Right camera debug log (last 20 lines):"
    tail -20 /tmp/right_camera_debug.log
    echo ""
else
    echo "❌ Right camera debug log not found"
fi

echo "🔄 Service Status:"
echo "=================="
echo "Dual recorder service:"
sudo systemctl status dual_recorder.service --no-pager -l
echo ""

echo "📊 Recent Service Logs:"
echo "======================"
echo "Last 20 lines of dual_recorder service:"
sudo journalctl -u dual_recorder.service -n 20 --no-pager
echo ""

echo "🎯 Manual Camera Test:"
echo "====================="
echo "To manually test camera scripts, run:"
echo "  python3 /tmp/camera_left_recorder.py"
echo "  python3 /tmp/camera_right_recorder.py"
echo ""
echo "Then check the debug logs:"
echo "  cat /tmp/left_camera_debug.log"
echo "  cat /tmp/right_camera_debug.log"
echo ""

echo "🔧 Next Steps:"
echo "=============="
echo "1. If cameras are detected but not working, try rebooting the Pi"
echo "2. Check if camera modules are loaded: lsmod | grep camera"
echo "3. Verify camera connections and power"
echo "4. Test with libcamera-hello if available"
echo "5. Check dmesg for camera-related errors: dmesg | grep -i camera"
echo "" 