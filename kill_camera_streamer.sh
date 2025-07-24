#!/bin/bash

# Kill Camera Streamer Script
# This script will kill the camera_streamer process that's blocking camera access

set -e

echo "🔧 Killing Camera Streamer Process"
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
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️ $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️ $message${NC}" ;;
    esac
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_status "error" "Please run as root (use sudo)"
    exit 1
fi

echo "Step 1: Finding camera_streamer process..."
echo ""

# Find camera_streamer process
CAMERA_STREAMER_PID=$(pgrep -f "camera_streamer.py" || echo "")

if [ -n "$CAMERA_STREAMER_PID" ]; then
    print_status "warning" "Found camera_streamer process: PID $CAMERA_STREAMER_PID"
    echo ""
    
    echo "Step 2: Killing camera_streamer process..."
    print_status "info" "Killing process $CAMERA_STREAMER_PID..."
    kill -9 $CAMERA_STREAMER_PID
    sleep 2
    
    # Verify it's dead
    if pgrep -f "camera_streamer.py" > /dev/null; then
        print_status "error" "Failed to kill camera_streamer process"
        exit 1
    else
        print_status "success" "Successfully killed camera_streamer process"
    fi
else
    print_status "success" "No camera_streamer process found"
fi

echo ""
echo "Step 3: Removing camera_streamer files..."
echo ""

# Remove camera_streamer files
CAMERA_STREAMER_FILE="/opt/ezrec-backend/backend/camera_streamer.py"
if [ -f "$CAMERA_STREAMER_FILE" ]; then
    print_status "info" "Removing $CAMERA_STREAMER_FILE"
    rm -f "$CAMERA_STREAMER_FILE"
    print_status "success" "Removed camera_streamer.py"
else
    print_status "info" "camera_streamer.py not found (already removed)"
fi

# Remove service file if it exists
SERVICE_FILE="/etc/systemd/system/camera_streamer.service"
if [ -f "$SERVICE_FILE" ]; then
    print_status "info" "Removing $SERVICE_FILE"
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    print_status "success" "Removed camera_streamer.service"
else
    print_status "info" "camera_streamer.service not found"
fi

echo ""
echo "Step 4: Verifying camera is free..."
echo ""

# Check if camera is now free
echo "🔍 Processes using video devices (should be empty):"
lsof /dev/video* 2>/dev/null || echo "✅ No processes using video devices"
echo ""

echo "🔍 Processes using media devices (should be empty):"
lsof /dev/media* 2>/dev/null || echo "✅ No processes using media devices"
echo ""

echo "Step 5: Testing camera access..."
echo ""

# Test camera access
print_status "info" "Testing camera with libcamera-hello..."
if command -v libcamera-hello &> /dev/null; then
    timeout 5s libcamera-hello --list-cameras 2>/dev/null && print_status "success" "Camera test successful" || print_status "error" "Camera test failed"
else
    print_status "warning" "libcamera-hello not available"
fi

echo ""
echo "Step 6: Restarting recorder service..."
echo ""

# Restart recorder service
print_status "info" "Restarting recorder.service..."
systemctl restart recorder.service
sleep 3

# Check recorder status
if systemctl is-active --quiet recorder.service; then
    print_status "success" "recorder.service: ACTIVE"
else
    print_status "error" "recorder.service: INACTIVE"
fi

echo ""
echo "🎉 Camera streamer removal completed!"
echo ""
echo "📋 Next steps:"
echo "1. Test camera: sudo python3 test_camera.py"
echo "2. Monitor recorder: sudo journalctl -u recorder.service -f"
echo "3. Check for any remaining issues"
echo "" 