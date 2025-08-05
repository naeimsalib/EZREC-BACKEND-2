#!/bin/bash
# EZREC Service Restart Script
# This script properly restarts all EZREC services in the correct order

echo "🔄 EZREC Service Restart Script"
echo "================================"

# Function to check if a service is active
check_service() {
    local service=$1
    if systemctl is-active --quiet $service; then
        echo "✅ $service is active"
        return 0
    else
        echo "❌ $service is not active"
        return 1
    fi
}

# Function to restart a service
restart_service() {
    local service=$1
    echo "🔄 Restarting $service..."
    sudo systemctl restart $service
    sleep 3
    if check_service $service; then
        echo "✅ $service restarted successfully"
    else
        echo "❌ Failed to restart $service"
        return 1
    fi
}

# Kill any existing camera processes first
echo "🛑 Killing existing camera processes..."
sudo pkill -f picamera2 || true
sudo pkill -f camera_streamer || true
sudo pkill -f recorder || true
sleep 2

# Stop all services first
echo "🛑 Stopping all EZREC services..."
sudo systemctl stop camera_streamer.service || true
sudo systemctl stop recorder.service || true
sudo systemctl stop video_worker.service || true
sudo systemctl stop status_updater.service || true
sudo systemctl stop health_api.service || true
sleep 3

# Start services in the correct order
echo "🚀 Starting EZREC services..."

# 1. Start camera_streamer first (it owns the camera)
restart_service "camera_streamer.service"

# 2. Start status_updater
restart_service "status_updater.service"

# 3. Start recorder
restart_service "recorder.service"

# 4. Start video_worker
restart_service "video_worker.service"

# 5. Start health_api
restart_service "health_api.service"

# Check all services
echo ""
echo "📊 Service Status Summary:"
echo "=========================="
services=("camera_streamer" "status_updater" "recorder" "video_worker" "health_api")

all_ok=true
for service in "${services[@]}"; do
    if check_service "$service.service"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        all_ok=false
    fi
done

echo ""
if $all_ok; then
    echo "🎉 All services are running successfully!"
else
    echo "⚠️ Some services failed to start. Check logs with:"
    echo "   sudo journalctl -u camera_streamer.service -n 50"
    echo "   sudo journalctl -u recorder.service -n 50"
fi

# Test camera stream
echo ""
echo "🔍 Testing camera stream..."
sleep 5
if curl -s --max-time 10 http://127.0.0.1:9000 > /dev/null; then
    echo "✅ Camera stream is accessible"
else
    echo "❌ Camera stream is not accessible"
    echo "   Check camera_streamer logs: sudo journalctl -u camera_streamer.service -f"
fi

echo ""
echo "�� Restart complete!" 