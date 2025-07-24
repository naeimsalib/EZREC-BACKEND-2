#!/bin/bash

# EZREC Log Analysis Script
# Run this on your Raspberry Pi to analyze all logs and identify issues

set -e

echo "📊 EZREC Log Analysis"
echo "====================="
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

# Create output directory
OUTPUT_DIR="/tmp/ezrec_log_analysis_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "📁 Analysis output will be saved to: $OUTPUT_DIR"
echo ""

# 1. System Service Status
echo "🔍 1. System Service Status"
echo "==========================="
{
    echo "=== EZREC Service Status ==="
    echo "Timestamp: $(date)"
    echo ""
    
    services=("recorder" "video_worker" "system_status" "log_collector" "health_api")
    for service in "${services[@]}"; do
        echo "--- $service.service ---"
        systemctl status "$service.service" --no-pager || echo "Service not found or not running"
        echo ""
    done
} > "$OUTPUT_DIR/01_service_status.txt"

print_status "success" "Service status saved"

# 2. Recent Logs (last 50 lines each)
echo ""
echo "📋 2. Recent Service Logs"
echo "========================"
{
    echo "=== Recent Service Logs ==="
    echo "Timestamp: $(date)"
    echo ""
    
    for service in "${services[@]}"; do
        echo "--- $service.service (last 50 lines) ---"
        journalctl -u "$service.service" -n 50 --no-pager || echo "No logs found"
        echo ""
        echo "=========================================="
        echo ""
    done
} > "$OUTPUT_DIR/02_recent_logs.txt"

print_status "success" "Recent logs saved"

# 3. Error Analysis
echo ""
echo "🚨 3. Error Analysis"
echo "==================="
{
    echo "=== Error Analysis ==="
    echo "Timestamp: $(date)"
    echo ""
    
    for service in "${services[@]}"; do
        echo "--- Errors in $service.service (last 24 hours) ---"
        journalctl -u "$service.service" --since "24 hours ago" | grep -i "error\|fail\|exception\|critical" || echo "No errors found"
        echo ""
    done
    
    echo "--- All System Errors (last 24 hours) ---"
    journalctl --since "24 hours ago" | grep -i "error\|fail\|exception\|critical" | tail -20 || echo "No system errors found"
    echo ""
} > "$OUTPUT_DIR/03_error_analysis.txt"

print_status "success" "Error analysis saved"

# 4. Application Logs
echo ""
echo "📝 4. Application Logs"
echo "====================="
{
    echo "=== Application Logs ==="
    echo "Timestamp: $(date)"
    echo ""
    
    LOG_FILES=(
        "/opt/ezrec-backend/logs/ezrec.log"
        "/opt/ezrec-backend/logs/recorder.log"
        "/opt/ezrec-backend/logs/video_worker.log"
        "/opt/ezrec-backend/logs/system_status.log"
        "/opt/ezrec-backend/logs/log_collector.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            echo "--- $log_file (last 50 lines) ---"
            tail -50 "$log_file" || echo "Could not read log file"
            echo ""
        else
            echo "--- $log_file ---"
            echo "File not found"
            echo ""
        fi
    done
} > "$OUTPUT_DIR/04_application_logs.txt"

print_status "success" "Application logs saved"

# 5. System Resources
echo ""
echo "💻 5. System Resources"
echo "====================="
{
    echo "=== System Resources ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "--- CPU Info ---"
    cat /proc/cpuinfo | grep "Model name" | head -1 || echo "CPU info not available"
    echo ""
    
    echo "--- Memory Usage ---"
    free -h
    echo ""
    
    echo "--- Disk Usage ---"
    df -h
    echo ""
    
    echo "--- Temperature ---"
    vcgencmd measure_temp 2>/dev/null || echo "Temperature not available"
    echo ""
    
    echo "--- Load Average ---"
    uptime
    echo ""
    
    echo "--- Network Interfaces ---"
    ip addr show | grep -E "inet.*global" || echo "No network interfaces found"
    echo ""
} > "$OUTPUT_DIR/05_system_resources.txt"

print_status "success" "System resources saved"

# 6. Camera Status
echo ""
echo "📷 6. Camera Status"
echo "=================="
{
    echo "=== Camera Status ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "--- Camera Devices ---"
    ls -la /dev/video* 2>/dev/null || echo "No camera devices found"
    echo ""
    
    echo "--- Camera Groups ---"
    groups pi 2>/dev/null || echo "User groups not available"
    echo ""
    
    echo "--- Camera Permissions ---"
    ls -la /dev/video0 2>/dev/null || echo "Camera device not found"
    echo ""
    
    echo "--- Camera Processes ---"
    ps aux | grep -i camera || echo "No camera processes found"
    echo ""
} > "$OUTPUT_DIR/06_camera_status.txt"

print_status "success" "Camera status saved"

# 7. Configuration Check
echo ""
echo "⚙️ 7. Configuration Check"
echo "========================"
{
    echo "=== Configuration Check ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "--- Environment File ---"
    if [ -f "/opt/ezrec-backend/.env" ]; then
        echo "Environment file exists"
        echo "File size: $(stat -c%s /opt/ezrec-backend/.env) bytes"
        echo "Last modified: $(stat -c%y /opt/ezrec-backend/.env)"
        echo ""
        echo "Required variables check:"
        grep -E "^(SUPABASE_URL|SUPABASE_KEY|USER_ID|CAMERA_ID)=" /opt/ezrec-backend/.env || echo "Missing required variables"
    else
        echo "Environment file not found"
    fi
    echo ""
    
    echo "--- Status File ---"
    if [ -f "/opt/ezrec-backend/status.json" ]; then
        echo "Status file exists"
        cat /opt/ezrec-backend/status.json | head -20 || echo "Could not read status file"
    else
        echo "Status file not found"
    fi
    echo ""
    
    echo "--- Bookings Cache ---"
    if [ -f "/opt/ezrec-backend/api/local_data/bookings.json" ]; then
        echo "Bookings cache exists"
        if command -v jq &> /dev/null; then
            echo "Booking count: $(jq '. | length' /opt/ezrec-backend/api/local_data/bookings.json)"
        else
            echo "jq not available for JSON parsing"
        fi
    else
        echo "Bookings cache not found"
    fi
    echo ""
} > "$OUTPUT_DIR/07_configuration_check.txt"

print_status "success" "Configuration check saved"

# 8. Network Connectivity
echo ""
echo "🌐 8. Network Connectivity"
echo "========================="
{
    echo "=== Network Connectivity ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "--- Internet Connectivity ---"
    ping -c 3 8.8.8.8 2>/dev/null && echo "Internet connection: OK" || echo "Internet connection: FAILED"
    echo ""
    
    echo "--- DNS Resolution ---"
    nslookup google.com 2>/dev/null && echo "DNS resolution: OK" || echo "DNS resolution: FAILED"
    echo ""
    
    echo "--- Supabase Connectivity ---"
    if [ -f "/opt/ezrec-backend/.env" ]; then
        SUPABASE_URL=$(grep "^SUPABASE_URL=" /opt/ezrec-backend/.env | cut -d'=' -f2)
        if [ -n "$SUPABASE_URL" ]; then
            HOST=$(echo "$SUPABASE_URL" | sed 's|https://||' | sed 's|http://||' | cut -d'/' -f1)
            ping -c 3 "$HOST" 2>/dev/null && echo "Supabase connectivity: OK" || echo "Supabase connectivity: FAILED"
        else
            echo "SUPABASE_URL not found in .env"
        fi
    else
        echo "Environment file not found"
    fi
    echo ""
} > "$OUTPUT_DIR/08_network_connectivity.txt"

print_status "success" "Network connectivity saved"

# 9. Process Analysis
echo ""
echo "🔍 9. Process Analysis"
echo "====================="
{
    echo "=== Process Analysis ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "--- EZREC Related Processes ---"
    ps aux | grep -E "(recorder|video_worker|system_status|log_collector|health_api)" | grep -v grep || echo "No EZREC processes found"
    echo ""
    
    echo "--- Python Processes ---"
    ps aux | grep python | grep -v grep || echo "No Python processes found"
    echo ""
    
    echo "--- Camera Related Processes ---"
    ps aux | grep -i camera | grep -v grep || echo "No camera processes found"
    echo ""
    
    echo "--- System Load ---"
    top -bn1 | head -20
    echo ""
} > "$OUTPUT_DIR/09_process_analysis.txt"

print_status "success" "Process analysis saved"

# 10. Summary Report
echo ""
echo "📊 10. Summary Report"
echo "===================="
{
    echo "=== EZREC Log Analysis Summary ==="
    echo "Timestamp: $(date)"
    echo "Analysis saved to: $OUTPUT_DIR"
    echo ""
    
    echo "--- Service Status Summary ---"
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service.service"; then
            echo "✅ $service.service: ACTIVE"
        else
            echo "❌ $service.service: INACTIVE"
        fi
    done
    echo ""
    
    echo "--- Critical Issues Found ---"
    # Check for critical errors
    CRITICAL_ERRORS=$(journalctl --since "1 hour ago" | grep -i "error\|fail\|exception\|critical" | wc -l)
    echo "Critical errors in last hour: $CRITICAL_ERRORS"
    
    if [ "$CRITICAL_ERRORS" -gt 0 ]; then
        echo "Recent critical errors:"
        journalctl --since "1 hour ago" | grep -i "error\|fail\|exception\|critical" | tail -5
    fi
    echo ""
    
    echo "--- Recommendations ---"
    echo "1. Check all log files in $OUTPUT_DIR"
    echo "2. Review service status and fix any inactive services"
    echo "3. Check camera connection and permissions"
    echo "4. Verify .env file configuration"
    echo "5. Ensure network connectivity to Supabase"
    echo "6. Monitor system resources (CPU, memory, disk)"
    echo ""
} > "$OUTPUT_DIR/10_summary_report.txt"

print_status "success" "Summary report saved"

# Create a single comprehensive report
echo ""
echo "📄 Creating comprehensive report..."
{
    echo "EZREC COMPREHENSIVE LOG ANALYSIS"
    echo "================================="
    echo "Generated: $(date)"
    echo "Analysis directory: $OUTPUT_DIR"
    echo ""
    
    for i in {01..10}; do
        if [ -f "$OUTPUT_DIR/${i}_*.txt" ]; then
            cat "$OUTPUT_DIR"/${i}_*.txt
            echo ""
            echo "=========================================="
            echo ""
        fi
    done
} > "$OUTPUT_DIR/COMPREHENSIVE_REPORT.txt"

print_status "success" "Comprehensive report created"

echo ""
echo "🎉 Log analysis completed!"
echo ""
echo "📁 All analysis files saved to: $OUTPUT_DIR"
echo ""
echo "📋 Key files:"
echo "  - COMPREHENSIVE_REPORT.txt (complete analysis)"
echo "  - 01_service_status.txt (service status)"
echo "  - 03_error_analysis.txt (error analysis)"
echo "  - 10_summary_report.txt (summary and recommendations)"
echo ""
echo "📤 To share logs with support:"
echo "  tar -czf ezrec_logs_$(date +%Y%m%d_%H%M%S).tar.gz $OUTPUT_DIR"
echo ""
echo "🔧 Next steps:"
echo "  1. Review the comprehensive report"
echo "  2. Check for any inactive services"
echo "  3. Look for error patterns"
echo "  4. Verify camera and network connectivity" 