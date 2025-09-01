#!/bin/bash

# EZREC Comprehensive System Check Script
# This script performs a full system check and saves output to logs.txt
# Should be run by the deployment script at the end

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER="michomanoly14892"
DEPLOY_PATH="/opt/ezrec-backend"
LOGS_FILE="logs.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
    echo "[$(date +'%H:%M:%S')] $1" >> "$LOGS_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
    echo "[$(date +'%H:%M:%S')] WARNING: $1" >> "$LOGS_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
    echo "[$(date +'%H:%M:%S')] ERROR: $1" >> "$LOGS_FILE"
}

log_step() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] STEP: $1${NC}"
    echo "[$(date +'%H:%M:%S')] STEP: $1" >> "$LOGS_FILE"
}

# Initialize logs file
init_logs() {
    log_step "Initializing comprehensive system check logs"
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "EZREC COMPREHENSIVE SYSTEM CHECK - $TIMESTAMP" >> "$LOGS_FILE"
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check system services
check_system_services() {
    log_step "Checking EZREC system services"
    
    echo "--- EZREC SERVICES STATUS ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check all EZREC services
    local services=("dual_recorder" "video_worker" "ezrec-api" "system_status")
    
    for service in "${services[@]}"; do
        log_info "Checking $service.service"
        echo "=== $service.service ===" >> "$LOGS_FILE"
        
        # Service status
        sudo systemctl status ${service}.service --no-pager -l >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        # Service logs (last 20 lines)
        echo "--- Recent logs for $service.service ---" >> "$LOGS_FILE"
        sudo journalctl -u ${service}.service -n 20 --no-pager >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        echo "=============================================================================" >> "$LOGS_FILE"
        echo "" >> "$LOGS_FILE"
    done
}

# Check Python environment and dependencies
check_python_environment() {
    log_step "Checking Python environment and dependencies"
    
    echo "--- PYTHON ENVIRONMENT CHECK ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check backend virtual environment
    if [[ -d "$DEPLOY_PATH/backend/venv" ]]; then
        echo "=== Backend Virtual Environment ===" >> "$LOGS_FILE"
        echo "Python version:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/python3" --version >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        echo "Installed packages:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/pip" list >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        # Test critical imports
        echo "Testing critical imports:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/python3" -c "
import sys
sys.path.insert(0, '.')
try:
    from stitch import PanoramicStitcher
    print('✅ Stitch module import successful')
except Exception as e:
    print(f'❌ Stitch module import failed: {e}')

try:
    from enhanced_merge import EnhancedVideoMerger
    print('✅ EnhancedVideoMerger import successful')
except Exception as e:
    print(f'❌ EnhancedVideoMerger import failed: {e}')

try:
    import picamera2
    print('✅ picamera2 import successful')
except Exception as e:
    print(f'❌ picamera2 import failed: {e}')

try:
    import cv2
    print('✅ OpenCV import successful')
except Exception as e:
    print(f'❌ OpenCV import failed: {e}')
" >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
    else
        echo "❌ Backend virtual environment not found" >> "$LOGS_FILE"
    fi
    
    # Check API virtual environment
    if [[ -d "$DEPLOY_PATH/api/venv" ]]; then
        echo "=== API Virtual Environment ===" >> "$LOGS_FILE"
        echo "Python version:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/python3" --version >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        echo "Installed packages:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/pip" list >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        # Test API imports
        echo "Testing API imports:" >> "$LOGS_FILE"
        sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/python3" -c "
try:
    import fastapi
    print('✅ FastAPI import successful')
except Exception as e:
    print(f'❌ FastAPI import failed: {e}')

try:
    import uvicorn
    print('✅ Uvicorn import successful')
except Exception as e:
    print(f'❌ Uvicorn import failed: {e}')
" >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
    else
        echo "❌ API virtual environment not found" >> "$LOGS_FILE"
    fi
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check API server functionality
check_api_server() {
    log_step "Checking API server functionality"
    
    echo "--- API SERVER FUNCTIONALITY CHECK ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check if API server is running
    if sudo systemctl is-active --quiet ezrec-api.service; then
        echo "✅ API service is running" >> "$LOGS_FILE"
        
        # Test API endpoints
        echo "Testing API endpoints:" >> "$LOGS_FILE"
        
        # Test alive endpoint
        if curl -s http://localhost:8000/test-alive > /dev/null 2>&1; then
            echo "✅ /test-alive endpoint responding" >> "$LOGS_FILE"
            echo "Response:" >> "$LOGS_FILE"
            curl -s http://localhost:8000/test-alive >> "$LOGS_FILE" 2>&1 || true
        else
            echo "❌ /test-alive endpoint not responding" >> "$LOGS_FILE"
        fi
        echo "" >> "$LOGS_FILE"
        
        # Test status endpoint
        if curl -s http://localhost:8000/status > /dev/null 2>&1; then
            echo "✅ /status endpoint responding" >> "$LOGS_FILE"
            echo "Response:" >> "$LOGS_FILE"
            curl -s http://localhost:8000/status >> "$LOGS_FILE" 2>&1 || true
        else
            echo "❌ /status endpoint not responding" >> "$LOGS_FILE"
        fi
        echo "" >> "$LOGS_FILE"
        
        # Test docs endpoint
        if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo "✅ /docs endpoint responding" >> "$LOGS_FILE"
        else
            echo "❌ /docs endpoint not responding" >> "$LOGS_FILE"
        fi
        echo "" >> "$LOGS_FILE"
        
    else
        echo "❌ API service is not running" >> "$LOGS_FILE"
    fi
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check Cloudflare tunnel
check_cloudflare_tunnel() {
    log_step "Checking Cloudflare tunnel status"
    
    echo "--- CLOUDFLARE TUNNEL CHECK ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check if cloudflared is running
    if sudo systemctl is-active --quiet cloudflared.service; then
        echo "✅ Cloudflare tunnel service is running" >> "$LOGS_FILE"
        
        # Check tunnel configuration
        if [[ -f "/etc/cloudflared/config.yml" ]]; then
            echo "✅ Tunnel config file exists" >> "$LOGS_FILE"
            echo "Config contents:" >> "$LOGS_FILE"
            cat /etc/cloudflared/config.yml >> "$LOGS_FILE" 2>&1 || true
        else
            echo "❌ Tunnel config file not found" >> "$LOGS_FILE"
        fi
        echo "" >> "$LOGS_FILE"
        
        # Check tunnel status
        echo "Tunnel status:" >> "$LOGS_FILE"
        cloudflared tunnel list >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
    else
        echo "❌ Cloudflare tunnel service is not running" >> "$LOGS_FILE"
    fi
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check file system and permissions
check_file_system() {
    log_step "Checking file system and permissions"
    
    echo "--- FILE SYSTEM CHECK ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check disk usage
    echo "Disk usage:" >> "$LOGS_FILE"
    df -h >> "$LOGS_FILE" 2>&1 || true
    echo "" >> "$LOGS_FILE"
    
    # Check critical directories
    local critical_dirs=("$DEPLOY_PATH" "$DEPLOY_PATH/backend" "$DEPLOY_PATH/api" "$DEPLOY_PATH/logs" "$DEPLOY_PATH/recordings")
    
    for dir in "${critical_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            echo "=== $dir ===" >> "$LOGS_FILE"
            echo "Permissions:" >> "$LOGS_FILE"
            ls -la "$dir" >> "$LOGS_FILE" 2>&1 || true
            echo "" >> "$LOGS_FILE"
        else
            echo "❌ Directory not found: $dir" >> "$LOGS_FILE"
        fi
    done
    
    # Check stitch module
    if [[ -d "$DEPLOY_PATH/backend/stitch" ]]; then
        echo "=== Stitch Module ===" >> "$LOGS_FILE"
        echo "Contents:" >> "$LOGS_FILE"
        ls -la "$DEPLOY_PATH/backend/stitch" >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        echo "Python files:" >> "$LOGS_FILE"
        find "$DEPLOY_PATH/backend/stitch" -name "*.py" -exec ls -la {} \; >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
    else
        echo "❌ Stitch module directory not found" >> "$LOGS_FILE"
    fi
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check network and ports
check_network() {
    log_step "Checking network and ports"
    
    echo "--- NETWORK CHECK ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check listening ports
    echo "Listening ports:" >> "$LOGS_FILE"
    sudo netstat -tlnp >> "$LOGS_FILE" 2>&1 || true
    echo "" >> "$LOGS_FILE"
    
    # Check specific ports
    echo "Port 8000 (API):" >> "$LOGS_FILE"
    sudo lsof -i :8000 >> "$LOGS_FILE" 2>&1 || true
    echo "" >> "$LOGS_FILE"
    
    echo "Port 9000 (Video worker):" >> "$LOGS_FILE"
    sudo lsof -i :9000 >> "$LOGS_FILE" 2>&1 || true
    echo "" >> "$LOGS_FILE"
    
    # Check external connectivity
    echo "External connectivity:" >> "$LOGS_FILE"
    if curl -s --max-time 10 https://api.ezrec.org/status > /dev/null 2>&1; then
        echo "✅ External API accessible via tunnel" >> "$LOGS_FILE"
    else
        echo "❌ External API not accessible" >> "$LOGS_FILE"
    fi
    echo "" >> "$LOGS_FILE"
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Check recent logs
check_recent_logs() {
    log_step "Checking recent system logs"
    
    echo "--- RECENT SYSTEM LOGS ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Check system logs for errors
    echo "Recent system errors:" >> "$LOGS_FILE"
    sudo journalctl -p err --since "1 hour ago" --no-pager >> "$LOGS_FILE" 2>&1 || true
    echo "" >> "$LOGS_FILE"
    
    # Check EZREC specific logs
    if [[ -d "$DEPLOY_PATH/logs" ]]; then
        echo "EZREC log files:" >> "$LOGS_FILE"
        ls -la "$DEPLOY_PATH/logs" >> "$LOGS_FILE" 2>&1 || true
        echo "" >> "$LOGS_FILE"
        
        # Show recent content of key log files
        local log_files=("dual_recorder.log" "video_worker.log" "ezrec-api.log" "system_status.log")
        
        for log_file in "${log_files[@]}"; do
            local full_path="$DEPLOY_PATH/logs/$log_file"
            if [[ -f "$full_path" ]]; then
                echo "=== Recent content of $log_file ===" >> "$LOGS_FILE"
                tail -20 "$full_path" >> "$LOGS_FILE" 2>&1 || true
                echo "" >> "$LOGS_FILE"
            fi
        done
    fi
    
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
}

# Final summary
generate_summary() {
    log_step "Generating system check summary"
    
    echo "--- SYSTEM CHECK SUMMARY ---" >> "$LOGS_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOGS_FILE"
    echo "" >> "$LOGS_FILE"
    
    # Count services
    local services=("dual_recorder" "video_worker" "ezrec-api" "system_status")
    local running_services=0
    
    for service in "${services[@]}"; do
        if sudo systemctl is-active --quiet ${service}.service; then
            ((running_services++))
        fi
    done
    
    echo "Services Status: $running_services/${#services[@]} running" >> "$LOGS_FILE"
    
    # Check API responsiveness
    if curl -s http://localhost:8000/test-alive > /dev/null 2>&1; then
        echo "API Server: ✅ Responding" >> "$LOGS_FILE"
    else
        echo "API Server: ❌ Not responding" >> "$LOGS_FILE"
    fi
    
    # Check Cloudflare tunnel
    if sudo systemctl is-active --quiet cloudflared.service; then
        echo "Cloudflare Tunnel: ✅ Running" >> "$LOGS_FILE"
    else
        echo "Cloudflare Tunnel: ❌ Not running" >> "$LOGS_FILE"
    fi
    
    # Check stitch module
    if [[ -d "$DEPLOY_PATH/backend/stitch" ]]; then
        echo "Stitch Module: ✅ Directory exists" >> "$LOGS_FILE"
    else
        echo "Stitch Module: ❌ Directory missing" >> "$LOGS_FILE"
    fi
    
    echo "" >> "$LOGS_FILE"
    echo "=============================================================================" >> "$LOGS_FILE"
    echo "System check completed at: $TIMESTAMP" >> "$LOGS_FILE"
    echo "=============================================================================" >> "$LOGS_FILE"
}

# Main execution
main() {
    log_step "Starting comprehensive EZREC system check"
    
    # Initialize logs
    init_logs
    
    # Run all checks
    check_system_services
    check_python_environment
    check_api_server
    check_cloudflare_tunnel
    check_file_system
    check_network
    check_recent_logs
    
    # Generate summary
    generate_summary
    
    log_step "System check completed - results saved to $LOGS_FILE"
    
    # Push to GitHub
    push_to_github
}

# Push results to GitHub
push_to_github() {
    log_step "Pushing system check results to GitHub"
    
    # Add logs file
    if git add "$LOGS_FILE" 2>/dev/null; then
        log_info "Added logs.txt to git"
        
        # Commit with timestamp
        if git commit -m "Update system check logs - $TIMESTAMP" 2>/dev/null; then
            log_info "Committed system check logs"
            
            # Push to remote
            if git push origin main 2>/dev/null; then
                log_info "Successfully pushed system check results to GitHub"
            else
                log_warn "Failed to push to GitHub - check git remote configuration"
            fi
        else
            log_warn "Failed to commit logs - no changes or git not configured"
        fi
    else
        log_warn "Failed to add logs to git - git not configured or not a repository"
    fi
}

# Run main function
main "$@" 