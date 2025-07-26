#!/bin/bash

echo "🔍 EZREC System Health Check"
echo "============================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "1. Checking Service Status..."
echo "----------------------------"

# Check if all services are running
services=("dual_recorder.service" "video_worker.service" "ezrec-api.service")
all_services_running=true

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        print_status 0 "$service is running"
    else
        print_status 1 "$service is not running"
        all_services_running=false
    fi
done

echo ""
echo "2. Checking Service Logs (Last 10 lines each)..."
echo "------------------------------------------------"

for service in "${services[@]}"; do
    echo ""
    print_info "=== $service logs ==="
    sudo journalctl -u "$service" -n 10 --no-pager
done

echo ""
echo "3. Checking System Resources..."
echo "-------------------------------"

# CPU and Memory
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

print_info "CPU Usage: ${cpu_usage}%"
print_info "Memory Usage: ${memory_usage}%"
print_info "Disk Usage: ${disk_usage}%"

# Check if resources are within acceptable limits
if (( $(echo "$cpu_usage < 80" | bc -l) )); then
    print_status 0 "CPU usage is acceptable"
else
    print_status 1 "CPU usage is high"
fi

if (( $(echo "$memory_usage < 80" | bc -l) )); then
    print_status 0 "Memory usage is acceptable"
else
    print_status 1 "Memory usage is high"
fi

if (( $(echo "$disk_usage < 90" | bc -l) )); then
    print_status 0 "Disk usage is acceptable"
else
    print_status 1 "Disk usage is high"
fi

echo ""
echo "4. Checking Camera Hardware..."
echo "------------------------------"

# Check if cameras are detected
camera_devices=$(ls /dev/video* 2>/dev/null | wc -l)
print_info "Video devices found: $camera_devices"

if [ $camera_devices -ge 2 ]; then
    print_status 0 "Sufficient video devices detected"
else
    print_status 1 "Insufficient video devices (need at least 2)"
fi

# Check v4l2 devices
print_info "V4L2 devices:"
v4l2-ctl --list-devices 2>/dev/null | head -20

echo ""
echo "5. Checking Required Tools..."
echo "-----------------------------"

tools=("ffmpeg" "ffprobe" "v4l2-ctl")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        print_status 0 "$tool is available"
    else
        print_status 1 "$tool is missing"
    fi
done

echo ""
echo "6. Checking Python Environment..."
echo "--------------------------------"

# Check if virtual environment exists and has required packages
if [ -f "/opt/ezrec-backend/api/venv/bin/python3" ]; then
    print_status 0 "Python virtual environment exists"
    
    # Check key packages
    packages=("fastapi" "supabase" "picamera2" "psutil" "boto3")
    for package in "${packages[@]}"; do
        if /opt/ezrec-backend/api/venv/bin/python3 -c "import $package" 2>/dev/null; then
            print_status 0 "$package is installed"
        else
            print_status 1 "$package is missing"
        fi
    done
else
    print_status 1 "Python virtual environment not found"
fi

echo ""
echo "7. Checking File Permissions..."
echo "-------------------------------"

# Check key directories and files
directories=("/opt/ezrec-backend" "/opt/ezrec-backend/recordings" "/opt/ezrec-backend/logs")
for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        if [ -w "$dir" ]; then
            print_status 0 "$dir is writable"
        else
            print_status 1 "$dir is not writable"
        fi
    else
        print_status 1 "$dir does not exist"
    fi
done

echo ""
echo "8. Checking API Endpoints..."
echo "----------------------------"

# Check if API is responding
if curl -s http://localhost:8000/health > /dev/null; then
    print_status 0 "API health endpoint is responding"
    
    # Get health response
    health_response=$(curl -s http://localhost:8000/health)
    print_info "Health response: $health_response"
else
    print_status 1 "API health endpoint is not responding"
fi

echo ""
echo "9. Checking Recent Log Files..."
echo "-------------------------------"

# Check recent log files
log_files=("/opt/ezrec-backend/logs/dual_recorder.log" "/opt/ezrec-backend/logs/video_worker.log")
for log_file in "${log_files[@]}"; do
    if [ -f "$log_file" ]; then
        print_info "=== Recent entries in $(basename "$log_file") ==="
        tail -5 "$log_file" 2>/dev/null || echo "Could not read log file"
    else
        print_warning "$(basename "$log_file") does not exist"
    fi
    echo ""
done

echo ""
echo "10. Checking Booking Cache..."
echo "-----------------------------"

booking_cache="/opt/ezrec-backend/api/local_data/bookings.json"
if [ -f "$booking_cache" ]; then
    print_status 0 "Booking cache file exists"
    cache_size=$(stat -c%s "$booking_cache")
    print_info "Cache file size: $cache_size bytes"
    
    # Check if it's valid JSON
    if python3 -m json.tool "$booking_cache" > /dev/null 2>&1; then
        print_status 0 "Booking cache is valid JSON"
    else
        print_status 1 "Booking cache is not valid JSON"
    fi
else
    print_warning "Booking cache file does not exist (this is normal if no bookings)"
fi

echo ""
echo "11. Checking Environment Configuration..."
echo "----------------------------------------"

env_file="/opt/ezrec-backend/.env"
if [ -f "$env_file" ]; then
    print_status 0 ".env file exists"
    
    # Check for required variables (without showing values)
    required_vars=("SUPABASE_URL" "SUPABASE_KEY" "USER_ID" "CAMERA_ID")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" "$env_file"; then
            print_status 0 "$var is configured"
        else
            print_status 1 "$var is missing"
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_warning "Missing environment variables: ${missing_vars[*]}"
    fi
else
    print_status 1 ".env file does not exist"
fi

echo ""
echo "12. Final Status Summary..."
echo "---------------------------"

if [ "$all_services_running" = true ]; then
    print_status 0 "All services are running"
else
    print_status 1 "Some services are not running"
fi

# Overall assessment
echo ""
echo "🎯 RECOMMENDATIONS:"
echo "=================="

if [ "$all_services_running" = true ]; then
    echo -e "${GREEN}✅ System appears ready for frontend testing${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create a test booking from the frontend"
    echo "2. Monitor the logs during recording:"
    echo "   sudo journalctl -u dual_recorder.service -f"
    echo "3. Check for merged video files in /opt/ezrec-backend/recordings/"
else
    echo -e "${RED}❌ System needs attention before testing${NC}"
    echo ""
    echo "Issues to resolve:"
    echo "1. Fix any service failures"
    echo "2. Check logs for specific errors"
    echo "3. Verify environment configuration"
fi

echo ""
echo "📋 Useful Commands for Monitoring:"
echo "=================================="
echo "• View all service logs: sudo journalctl -u dual_recorder.service -f"
echo "• Check disk space: df -h"
echo "• Monitor system resources: htop"
echo "• Check camera devices: v4l2-ctl --list-devices"
echo "• Test API: curl http://localhost:8000/health"
echo "• View recent recordings: ls -la /opt/ezrec-backend/recordings/" 