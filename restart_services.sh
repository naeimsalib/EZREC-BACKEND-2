#!/bin/bash

# EZREC Service Restart and Status Check Script
# Run this on your Raspberry Pi to restart all services and check their status

set -e

echo "🔄 EZREC Service Restart Script"
echo "================================"
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

# Stop all services first
echo "🛑 Stopping all EZREC services..."
services=("recorder" "video_worker" "system_status" "log_collector" "health_api")
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        systemctl stop "$service.service"
        print_status "success" "Stopped $service.service"
    else
        print_status "warning" "$service.service was not running"
    fi
done

# Kill any camera processes
echo ""
echo "🔫 Killing any camera processes..."
if command -v fuser &> /dev/null; then
    fuser -k /dev/video0 2>/dev/null || true
    sleep 2
    print_status "info" "Camera processes cleared"
else
    print_status "warning" "fuser not available, skipping camera process kill"
fi

# Reload systemd
echo ""
echo "🔄 Reloading systemd..."
systemctl daemon-reload
print_status "success" "Systemd reloaded"

# Start services in order
echo ""
echo "🚀 Starting services in order..."
for service in "${services[@]}"; do
    echo "Starting $service.service..."
    systemctl start "$service.service"
    sleep 3
    
    if systemctl is-active --quiet "$service.service"; then
        print_status "success" "$service.service is running"
    else
        print_status "error" "$service.service failed to start"
    fi
done

# Enable services
echo ""
echo "🔧 Enabling services for auto-start..."
for service in "${services[@]}"; do
    systemctl enable "$service.service"
    print_status "success" "Enabled $service.service"
done

# Check final status
echo ""
echo "📊 Final Service Status:"
echo "========================"
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service.service"; then
        print_status "success" "$service.service: ACTIVE"
    else
        print_status "error" "$service.service: INACTIVE"
    fi
done

# Show recent logs
echo ""
echo "📋 Recent Logs (last 10 lines each):"
echo "===================================="

for service in "${services[@]}"; do
    echo ""
    echo "--- $service.service logs ---"
    journalctl -u "$service.service" -n 10 --no-pager || print_status "warning" "No logs for $service.service"
done

# Check for errors in logs
echo ""
echo "🔍 Checking for errors in recent logs..."
echo "========================================"

for service in "${services[@]}"; do
    echo ""
    echo "--- Errors in $service.service ---"
    journalctl -u "$service.service" --since "5 minutes ago" | grep -i "error\|fail\|exception" | tail -5 || print_status "info" "No recent errors in $service.service"
done

# Check system resources
echo ""
echo "💻 System Resources:"
echo "==================="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk Usage: $(df / | tail -1 | awk '{print $5}')"
echo "Temperature: $(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2 || echo 'N/A')"

# Check camera
echo ""
echo "📷 Camera Status:"
echo "================"
if [ -e /dev/video0 ]; then
    print_status "success" "Camera device found: /dev/video0"
    ls -la /dev/video*
else
    print_status "error" "Camera device not found: /dev/video0"
fi

# Check recording status
echo ""
echo "🎥 Recording Status:"
echo "==================="
if [ -f "/opt/ezrec-backend/status.json" ]; then
    if command -v jq &> /dev/null; then
        is_recording=$(jq -r '.is_recording // false' /opt/ezrec-backend/status.json)
        if [ "$is_recording" = "true" ]; then
            print_status "success" "Recording is ACTIVE"
        else
            print_status "info" "Recording is INACTIVE"
        fi
    else
        print_status "warning" "jq not available, cannot parse status.json"
    fi
else
    print_status "warning" "Status file not found: /opt/ezrec-backend/status.json"
fi

# Check bookings cache
echo ""
echo "📅 Bookings Cache:"
echo "=================="
if [ -f "/opt/ezrec-backend/api/local_data/bookings.json" ]; then
    booking_count=$(jq '. | length' /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || echo "0")
    print_status "info" "Found $booking_count bookings in cache"
else
    print_status "warning" "Bookings cache not found"
fi

echo ""
echo "🎉 Service restart completed!"
echo ""
echo "📝 Useful commands for monitoring:"
echo "  View all service logs: sudo journalctl -f"
echo "  View specific service: sudo journalctl -u recorder.service -f"
echo "  Check service status: sudo systemctl status recorder.service"
echo "  View application logs: tail -f /opt/ezrec-backend/logs/ezrec.log"
echo ""
echo "🔧 If services are not working:"
echo "  1. Check .env file configuration"
echo "  2. Verify camera connection"
echo "  3. Check disk space: df -h"
echo "  4. Check network: ping 8.8.8.8" 