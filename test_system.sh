#!/bin/bash

# EZREC Backend Comprehensive Test Script
# This script tests all components and provides detailed logs for debugging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Test configuration
API_BASE_URL="http://localhost:9000"
TEST_DURATION=30  # seconds to run recording test
LOG_DIR="/opt/ezrec-backend/logs"

echo "🚀 Starting EZREC Backend Comprehensive Test"
echo "=============================================="
echo "Timestamp: $(date)"
echo "Test Duration: ${TEST_DURATION} seconds"
echo ""

# Function to check if a service is running
check_service() {
    local service_name=$1
    if systemctl is-active --quiet ${service_name}.service; then
        log_success "$service_name is running"
        return 0
    else
        log_error "$service_name is not running"
        return 1
    fi
}

# Function to get service status
get_service_status() {
    local service_name=$1
    echo "--- $service_name Status ---"
    systemctl status ${service_name}.service --no-pager -l || true
    echo ""
}

# Function to get recent logs
get_recent_logs() {
    local service_name=$1
    local log_file=$2
    echo "--- Recent $service_name Logs ---"
    if [ -f "$log_file" ]; then
        tail -20 "$log_file" || echo "No log file found"
    else
        journalctl -u ${service_name}.service -n 20 --no-pager || echo "No journal logs found"
    fi
    echo ""
}

# Function to test API endpoint
test_api_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local response=$(curl -s -w "%{http_code}" -o /tmp/api_response.json "$API_BASE_URL$endpoint")
    local status_code=${response: -3}
    
    if [ "$status_code" = "$expected_status" ]; then
        log_success "API $endpoint returned $status_code"
        if [ -f /tmp/api_response.json ]; then
            echo "Response: $(cat /tmp/api_response.json)"
        fi
    else
        log_error "API $endpoint returned $status_code (expected $expected_status)"
        if [ -f /tmp/api_response.json ]; then
            echo "Response: $(cat /tmp/api_response.json)"
        fi
    fi
    echo ""
}

# Function to create a test booking
create_test_booking() {
    log_step "Creating Test Booking"
    
    # Create a booking for 30 seconds from now
    local start_time=$(date -d "+30 seconds" -Iseconds)
    local end_time=$(date -d "+90 seconds" -Iseconds)
    
    local booking_data=$(cat <<EOF
{
    "id": "test-booking-$(date +%s)",
    "user_id": "test-user-$(date +%s)",
    "start_time": "$start_time",
    "end_time": "$end_time",
    "status": "confirmed"
}
EOF
)
    
    echo "Creating booking with data:"
    echo "$booking_data"
    echo ""
    
    local response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$booking_data" \
        -o /tmp/booking_response.json \
        "$API_BASE_URL/bookings")
    
    local status_code=${response: -3}
    
    if [ "$status_code" = "200" ]; then
        log_success "Test booking created successfully"
        echo "Response: $(cat /tmp/booking_response.json)"
    else
        log_error "Failed to create test booking (status: $status_code)"
        if [ -f /tmp/booking_response.json ]; then
            echo "Response: $(cat /tmp/booking_response.json)"
        fi
    fi
    echo ""
}

# Function to monitor recording status
monitor_recording() {
    log_step "Monitoring Recording Status"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + TEST_DURATION))
    
    echo "Monitoring for $TEST_DURATION seconds..."
    echo "Start time: $(date)"
    echo "End time: $(date -d "@$end_time")"
    echo ""
    
    while [ $(date +%s) -lt $end_time ]; do
        local current_time=$(date '+%H:%M:%S')
        local is_recording=$(curl -s "$API_BASE_URL/status/is_recording" | jq -r '.is_recording // false' 2>/dev/null || echo "false")
        local next_booking=$(curl -s "$API_BASE_URL/status/next_booking" | jq -r '.start_time // "none"' 2>/dev/null || echo "none")
        
        echo "[$current_time] Recording: $is_recording | Next Booking: $next_booking"
        
        # Check if recording started
        if [ "$is_recording" = "true" ]; then
            log_success "Recording started at $current_time"
        fi
        
        sleep 5
    done
    
    echo ""
    log_info "Recording monitoring completed"
}

# Function to check disk space and files
check_system_resources() {
    log_step "Checking System Resources"
    
    echo "--- Disk Usage ---"
    df -h /opt/ezrec-backend 2>/dev/null || df -h /
    echo ""
    
    echo "--- Memory Usage ---"
    free -h
    echo ""
    
    echo "--- CPU Usage ---"
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
    echo ""
    
    echo "--- Temperature ---"
    if command -v vcgencmd >/dev/null 2>&1; then
        vcgencmd measure_temp
    else
        echo "Temperature monitoring not available"
    fi
    echo ""
}

# Function to check recording files
check_recordings() {
    log_step "Checking Recording Files"
    
    local recordings_dir="/opt/ezrec-backend/recordings"
    local raw_dir="/opt/ezrec-backend/raw_recordings"
    local processed_dir="/opt/ezrec-backend/processed_recordings"
    
    echo "--- Recordings Directory ---"
    if [ -d "$recordings_dir" ]; then
        find "$recordings_dir" -name "*.mp4" -o -name "*.json" | head -10
    else
        echo "Recordings directory not found"
    fi
    echo ""
    
    echo "--- Raw Recordings Directory ---"
    if [ -d "$raw_dir" ]; then
        find "$raw_dir" -name "*.mp4" | head -10
    else
        echo "Raw recordings directory not found"
    fi
    echo ""
    
    echo "--- Processed Recordings Directory ---"
    if [ -d "$processed_dir" ]; then
        find "$processed_dir" -name "*.mp4" | head -10
    else
        echo "Processed recordings directory not found"
    fi
    echo ""
}

# Function to check network connectivity
check_network() {
    log_step "Checking Network Connectivity"
    
    echo "--- Internet Connectivity ---"
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "Internet connectivity OK"
    else
        log_error "No internet connectivity"
    fi
    echo ""
    
    echo "--- Local Network ---"
    if ping -c 1 localhost >/dev/null 2>&1; then
        log_success "Local network OK"
    else
        log_error "Local network issues"
    fi
    echo ""
    
    echo "--- Port Status ---"
    echo "Port 9000 (API): $(netstat -tlnp 2>/dev/null | grep :9000 || echo 'Not listening')"
    echo "Port 8000 (Alternative): $(netstat -tlnp 2>/dev/null | grep :8000 || echo 'Not listening')"
    echo ""
}

# Main test execution
main() {
    log_step "1. Checking Service Status"
    echo ""
    
    # Check all services
    local services=("dual_recorder" "video_worker" "ezrec-api" "system_status")
    local all_services_ok=true
    
    for service in "${services[@]}"; do
        if ! check_service "$service"; then
            all_services_ok=false
        fi
    done
    
    if [ "$all_services_ok" = true ]; then
        log_success "All services are running"
    else
        log_error "Some services are not running"
    fi
    echo ""
    
    log_step "2. Testing API Endpoints"
    echo ""
    
    # Test basic API endpoints
    test_api_endpoint "/test-alive"
    test_api_endpoint "/status"
    test_api_endpoint "/health"
    test_api_endpoint "/bookings"
    test_api_endpoint "/status/is_recording"
    test_api_endpoint "/status/next_booking"
    
    log_step "3. Creating Test Booking"
    echo ""
    create_test_booking
    
    log_step "4. Monitoring Recording Process"
    echo ""
    monitor_recording
    
    log_step "5. Checking System Resources"
    echo ""
    check_system_resources
    
    log_step "6. Checking Recording Files"
    echo ""
    check_recordings
    
    log_step "7. Checking Network"
    echo ""
    check_network
    
    log_step "8. Detailed Service Logs"
    echo ""
    
    # Get detailed logs for each service
    for service in "${services[@]}"; do
        get_service_status "$service"
        get_recent_logs "$service" "$LOG_DIR/${service}.log"
    done
    
    log_step "9. Final Status Check"
    echo ""
    
    # Final status check
    for service in "${services[@]}"; do
        check_service "$service"
    done
    
    echo ""
    log_step "Test Summary"
    echo "=============="
    echo "Test completed at: $(date)"
    echo "All logs have been captured above"
    echo ""
    echo "If you see any errors or warnings above, please share this complete output"
    echo "for debugging assistance."
    echo ""
}

# Run the test
main "$@" 