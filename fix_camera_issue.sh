#!/bin/bash

# EZREC Camera Fix Script
# This script will find and kill all processes using the camera

set -e

echo "🔧 EZREC Camera Fix Script"
echo "=========================="
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

echo "Step 1: Finding all processes using camera devices..."
echo ""

# Find all processes using video devices
echo "📷 Processes using video devices:"
lsof /dev/video* 2>/dev/null || echo "No processes found using video devices"
echo ""

# Find all processes using media devices
echo "📹 Processes using media devices:"
lsof /dev/media* 2>/dev/null || echo "No processes found using media devices"
echo ""

# Find Python processes that might be using camera
echo "🐍 Python processes:"
ps aux | grep python | grep -v grep || echo "No Python processes found"
echo ""

echo "Step 2: Stopping all EZREC services..."
echo ""

# Stop all EZREC services
services=("recorder" "video_worker" "system_status" "log_collector" "health_api")
for service in "${services[@]}"; do
    print_status "info" "Stopping $service.service..."
    systemctl stop "$service.service" 2>/dev/null || print_status "warning" "$service.service not running"
done

echo ""
echo "Step 3: Killing all camera-related processes..."
echo ""

# Kill all processes using video devices
print_status "info" "Killing processes using video devices..."
for dev in /dev/video*; do
    if [ -e "$dev" ]; then
        fuser -k "$dev" 2>/dev/null || true
    fi
done

# Kill all processes using media devices
print_status "info" "Killing processes using media devices..."
for dev in /dev/media*; do
    if [ -e "$dev" ]; then
        fuser -k "$dev" 2>/dev/null || true
    fi
done

# Kill any remaining Python processes that might be using camera
print_status "info" "Killing Python processes..."
pkill -f "recorder.py" 2>/dev/null || true
pkill -f "video_worker.py" 2>/dev/null || true
pkill -f "test_camera.py" 2>/dev/null || true

echo ""
echo "Step 4: Waiting for processes to terminate..."
sleep 3

echo ""
echo "Step 5: Verifying camera is free..."
echo ""

# Check if camera is now free
echo "📷 Video devices status:"
ls -la /dev/video* 2>/dev/null || echo "No video devices found"
echo ""

echo "📹 Media devices status:"
ls -la /dev/media* 2>/dev/null || echo "No media devices found"
echo ""

echo "🔍 Processes using video devices (should be empty):"
lsof /dev/video* 2>/dev/null || echo "✅ No processes using video devices"
echo ""

echo "🔍 Processes using media devices (should be empty):"
lsof /dev/media* 2>/dev/null || echo "✅ No processes using media devices"
echo ""

echo "Step 6: Testing camera access..."
echo ""

# Test camera access
print_status "info" "Testing camera with libcamera-hello..."
if command -v libcamera-hello &> /dev/null; then
    timeout 5s libcamera-hello --list-cameras 2>/dev/null && print_status "success" "Camera test successful" || print_status "error" "Camera test failed"
else
    print_status "warning" "libcamera-hello not available"
fi

echo ""
echo "Step 7: Restarting EZREC services..."
echo ""

# Restart services in order
for service in "${services[@]}"; do
    print_status "info" "Starting $service.service..."
    systemctl start "$service.service"
    sleep 2
done

echo ""
echo "Step 8: Checking service status..."
echo ""

# Check service status
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        print_status "success" "$service.service: ACTIVE"
    else
        print_status "error" "$service.service: INACTIVE"
    fi
done

echo ""
echo "🎉 Camera fix completed!"
echo ""
echo "📋 Next steps:"
echo "1. Check if camera is working: sudo python3 test_camera.py"
echo "2. Monitor logs: sudo journalctl -u recorder.service -f"
echo "3. Check for any remaining issues"
echo "" 