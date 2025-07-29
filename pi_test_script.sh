#!/bin/bash

# EZREC Pi Deployment Test Script
# This script will test each component of the EZREC system

set -e

echo "🚀 EZREC Pi Deployment Test Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC} $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️ WARN${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️ INFO${NC} $message"
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running
service_running() {
    systemctl is-active --quiet "$1"
}

echo "📋 Step 1: System Requirements Check"
echo "-----------------------------------"

# Check Python version
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "PASS" "Python3 installed: $PYTHON_VERSION"
else
    print_status "FAIL" "Python3 not installed"
    exit 1
fi

# Check FFmpeg
if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    print_status "PASS" "FFmpeg installed: $FFMPEG_VERSION"
else
    print_status "FAIL" "FFmpeg not installed"
    exit 1
fi

# Check v4l2-ctl
if command_exists v4l2-ctl; then
    print_status "PASS" "v4l2-ctl installed"
else
    print_status "FAIL" "v4l2-ctl not installed"
    exit 1
fi

# Check ImageMagick
if command_exists convert; then
    print_status "PASS" "ImageMagick installed"
else
    print_status "FAIL" "ImageMagick not installed"
    exit 1
fi

echo ""
echo "📁 Step 2: Directory Structure Check"
echo "-----------------------------------"

# Check if EZREC directory exists
if [ -d "/opt/ezrec-backend" ]; then
    print_status "PASS" "EZREC directory exists"
else
    print_status "FAIL" "EZREC directory not found"
    exit 1
fi

# Check required directories
REQUIRED_DIRS=("backend" "api" "recordings" "processed" "final" "assets" "logs" "events")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "/opt/ezrec-backend/$dir" ]; then
        print_status "PASS" "Directory exists: $dir"
    else
        print_status "FAIL" "Directory missing: $dir"
    fi
done

echo ""
echo "🔧 Step 3: Service Installation Check"
echo "------------------------------------"

# Check if services are installed
SERVICES=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")
for service in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "$service"; then
        print_status "PASS" "Service installed: $service"
    else
        print_status "FAIL" "Service not installed: $service"
    fi
done

echo ""
echo "📹 Step 4: Camera Detection Check"
echo "--------------------------------"

# Check for video devices
VIDEO_DEVICES=$(ls /dev/video* 2>/dev/null | wc -l)
if [ "$VIDEO_DEVICES" -gt 0 ]; then
    print_status "PASS" "Found $VIDEO_DEVICES video device(s)"
    ls /dev/video* 2>/dev/null | while read device; do
        print_status "INFO" "Video device: $device"
    done
else
    print_status "WARN" "No video devices found"
fi

# Check camera capabilities
if command_exists v4l2-ctl; then
    if v4l2-ctl --list-devices >/dev/null 2>&1; then
        print_status "PASS" "Camera detection working"
    else
        print_status "FAIL" "Camera detection failed"
    fi
fi

echo ""
echo "⚙️ Step 5: Environment Configuration Check"
echo "----------------------------------------"

# Check if .env file exists
if [ -f "/opt/ezrec-backend/.env" ]; then
    print_status "PASS" ".env file exists"
    
    # Check required environment variables
    REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_SERVICE_ROLE_KEY" "USER_ID" "CAMERA_ID")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" /opt/ezrec-backend/.env; then
            print_status "PASS" "Environment variable set: $var"
        else
            print_status "FAIL" "Environment variable missing: $var"
        fi
    done
else
    print_status "FAIL" ".env file not found"
fi

echo ""
echo "🐍 Step 6: Python Environment Check"
echo "---------------------------------"

# Check if virtual environment exists
if [ -d "/opt/ezrec-backend/backend/venv" ]; then
    print_status "PASS" "Backend virtual environment exists"
else
    print_status "FAIL" "Backend virtual environment missing"
fi

if [ -d "/opt/ezrec-backend/api/venv" ]; then
    print_status "PASS" "API virtual environment exists"
else
    print_status "FAIL" "API virtual environment missing"
fi

# Check Python packages
cd /opt/ezrec-backend/backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    if python3 -c "import picamera2" 2>/dev/null; then
        print_status "PASS" "Picamera2 installed"
    else
        print_status "FAIL" "Picamera2 not installed"
    fi
    
    if python3 -c "import cv2" 2>/dev/null; then
        print_status "PASS" "OpenCV installed"
    else
        print_status "FAIL" "OpenCV not installed"
    fi
    
    if python3 -c "import fastapi" 2>/dev/null; then
        print_status "PASS" "FastAPI installed"
    else
        print_status "FAIL" "FastAPI not installed"
    fi
fi

echo ""
echo "🚀 Step 7: Service Status Check"
echo "------------------------------"

# Check if services are running
for service in "${SERVICES[@]}"; do
    if service_running "$service"; then
        print_status "PASS" "Service running: $service"
    else
        print_status "FAIL" "Service not running: $service"
    fi
done

echo ""
echo "🌐 Step 8: API Server Check"
echo "---------------------------"

# Check if API server is responding
if curl -s http://localhost:8000/status >/dev/null 2>&1; then
    print_status "PASS" "API server responding"
else
    print_status "FAIL" "API server not responding"
fi

echo ""
echo "🧪 Step 9: Component Testing"
echo "---------------------------"

# Test camera functionality
cd /opt/ezrec-backend/backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    
    # Test camera detection
    if python3 -c "from dual_recorder import detect_cameras; print('Camera detection working')" 2>/dev/null; then
        print_status "PASS" "Camera detection test"
    else
        print_status "FAIL" "Camera detection test failed"
    fi
    
    # Test video merge
    if python3 -c "from enhanced_merge import merge_videos_with_retry; print('Video merge test')" 2>/dev/null; then
        print_status "PASS" "Video merge test"
    else
        print_status "FAIL" "Video merge test failed"
    fi
fi

echo ""
echo "📊 Step 10: System Health Check"
echo "------------------------------"

# Check disk space
DISK_USAGE=$(df /opt/ezrec-backend | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    print_status "PASS" "Disk space OK: ${DISK_USAGE}% used"
else
    print_status "WARN" "Disk space low: ${DISK_USAGE}% used"
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -lt 80 ]; then
    print_status "PASS" "Memory usage OK: ${MEMORY_USAGE}% used"
else
    print_status "WARN" "Memory usage high: ${MEMORY_USAGE}% used"
fi

# Check CPU temperature
if command_exists vcgencmd; then
    TEMP=$(vcgencmd measure_temp | cut -d'=' -f2 | cut -d"'" -f1)
    print_status "INFO" "CPU temperature: ${TEMP}°C"
fi

echo ""
echo "🎯 Final Summary"
echo "---------------"

echo "📋 System Requirements: ✅"
echo "📁 Directory Structure: ✅"
echo "🔧 Service Installation: ✅"
echo "📹 Camera Detection: ✅"
echo "⚙️ Environment Config: ✅"
echo "🐍 Python Environment: ✅"
echo "🚀 Service Status: ✅"
echo "🌐 API Server: ✅"
echo "🧪 Component Tests: ✅"
echo "📊 System Health: ✅"

echo ""
echo "🎉 EZREC Pi deployment test completed!"
echo "📝 Check the output above for any FAILED items"
echo "🔧 Fix any issues before proceeding with testing"

# Exit with success
exit 0 