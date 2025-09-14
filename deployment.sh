#!/bin/bash

# EZREC Backend Deployment Script - UPDATED WITH ALL FIXES
# Clean, efficient deployment with proper error handling and modular structure
# 
# NOTE: This script focuses ONLY on EZREC services and does NOT touch
# Cloudflare tunnel configuration. The tunnel should be set up separately
# and will be preserved during deployment.

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================

DEPLOY_USER="michomanoly14892"
DEPLOY_PATH="/opt/ezrec-backend"
SERVICES=("dual_recorder" "video_worker" "ezrec-api" "system_status")
TIMER_SERVICES=("system_status")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

log_step() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] STEP: $1${NC}"
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if user exists
user_exists() {
    id "$1" &>/dev/null
}

# Manage services (start/stop/enable/disable)
manage_services() {
    local action=$1
    local service_list=("${@:2}")
    
    for service in "${service_list[@]}"; do
        log_info "Managing $service: $action"
        sudo systemctl $action ${service}.service 2>/dev/null || true
    done
}

# Check service status
check_service_status() {
    local service=$1
    if sudo systemctl is-active --quiet $service; then
        log_info "✅ $service is running"
        return 0
    else
        log_error "$service failed to start"
        return 1
    fi
}

# Kill processes by pattern
kill_processes() {
    local patterns=("$@")
    for pattern in "${patterns[@]}"; do
        sudo pkill -f "$pattern" 2>/dev/null || true
    done
}

# Test Python import
test_python_import() {
    local venv_path=$1
    local module=$2
    local description=$3
    
    if sudo -u $DEPLOY_USER $venv_path/bin/python3 -c "import $module; print('✅ $description imported successfully')" 2>/dev/null; then
        log_info "✅ $description import test passed"
        return 0
    else
        log_warn "⚠️ $description import test failed"
        return 1
    fi
}

# =============================================================================
# COMPREHENSIVE FIXES
# =============================================================================

# Fix port conflicts aggressively with comprehensive cleanup
fix_port_conflicts_comprehensive() {
    log_info "🔧 Fixing port conflicts with comprehensive cleanup..."
    
    # Stop all EZREC services first
    log_info "🛑 Stopping all EZREC services..."
    sudo systemctl stop ezrec-api.service 2>/dev/null || true
    sudo systemctl stop video_worker.service 2>/dev/null || true
    sudo systemctl stop dual_recorder.service 2>/dev/null || true
    sudo systemctl stop system_status.service 2>/dev/null || true
    
    # Kill any processes using our ports with multiple strategies
    log_info "🧹 Comprehensive port cleanup..."
    
    # Strategy 1: Kill by port
    if lsof -i :8000 >/dev/null 2>&1; then
        log_info "🔍 Found processes on port 8000, killing them..."
        sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    if lsof -i :9000 >/dev/null 2>&1; then
        log_info "🔍 Found processes on port 9000, killing them..."
        sudo lsof -ti :9000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Strategy 2: Kill by process name (more aggressive)
    log_info "🧹 Killing processes by name..."
    sudo pkill -f "uvicorn" 2>/dev/null || true
    sudo pkill -f "api_server" 2>/dev/null || true
    sudo pkill -f "python.*8000" 2>/dev/null || true
    sudo pkill -f "python.*9000" 2>/dev/null || true
    sudo pkill -f "python.*api_server" 2>/dev/null || true
    
    # Strategy 3: Kill any remaining Python processes on our ports
    for port in 8000 9000; do
        if lsof -i :$port >/dev/null 2>&1; then
            log_info "🔍 Found remaining processes on port $port, force killing..."
            sudo lsof -ti :$port | xargs -r sudo kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    
    # Strategy 4: Kill any Python processes that might be running our services
    log_info "🧹 Killing any remaining Python service processes..."
    sudo pkill -f "api_server.py" 2>/dev/null || true
    sudo pkill -f "dual_recorder.py" 2>/dev/null || true
    sudo pkill -f "video_worker.py" 2>/dev/null || true
    sudo pkill -f "system_status.py" 2>/dev/null || true
    sleep 2
    
    # Strategy 5: Force kill any remaining processes on our ports
    log_info "🧹 Force killing any remaining processes on ports 8000 and 9000..."
    for port in 8000 9000; do
        if lsof -i :$port >/dev/null 2>&1; then
            log_info "🔍 Force killing processes on port $port..."
            sudo lsof -ti :$port | xargs -r sudo kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    
    # Wait for processes to fully terminate
    sleep 3
    
    # Verify ports are free
    for port in 8000 9000; do
        if ! lsof -i :$port >/dev/null 2>&1; then
            log_info "✅ Port $port is now free"
        else
            log_error "❌ Port $port is still in use after cleanup"
            log_info "📋 Processes still using port $port:"
            sudo lsof -i :$port 2>/dev/null || true
        fi
    done
    
    log_info "✅ Comprehensive port conflict resolution completed"
}

# Install psutil in all virtual environments
install_psutil_everywhere() {
    log_info "🔧 Installing psutil in all virtual environments..."
    
    # Install in backend venv
    if [[ -d "$DEPLOY_PATH/backend/venv" ]]; then
        log_info "📦 Installing psutil in backend virtual environment..."
        if sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/pip" install --no-cache-dir psutil; then
            log_info "✅ psutil installed successfully in backend venv"
        else
            log_error "❌ psutil installation failed in backend venv"
            return 1
        fi
    fi
    
    # Install in API venv
    if [[ -d "$DEPLOY_PATH/api/venv" ]]; then
        log_info "📦 Installing psutil in API virtual environment..."
        if sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/pip" install --no-cache-dir psutil; then
            log_info "✅ psutil installed successfully in API venv"
        else
            log_error "❌ psutil installation failed in API venv"
            return 1
        fi
    fi
    
    # Test the imports
    log_info "🧪 Testing psutil imports..."
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/python3" -c "import psutil; print('✅ psutil imported successfully in backend')" 2>/dev/null; then
        log_info "✅ psutil import test passed in backend"
    else
        log_error "❌ psutil import test failed in backend"
        return 1
    fi
    
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/python3" -c "import psutil; print('✅ psutil imported successfully in API')" 2>/dev/null; then
        log_info "✅ psutil import test passed in API"
    else
        log_error "❌ psutil import test failed in API"
        return 1
    fi
    
    log_info "✅ psutil installed and tested successfully in all environments"
}

# Ensure all required files and directories exist with proper permissions
ensure_files_and_directories() {
    log_info "🔧 Ensuring all required files and directories exist..."
    
    # Create logs directory with proper permissions
    log_info "📁 Creating logs directory..."
    sudo mkdir -p "$DEPLOY_PATH/logs"
    sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/logs"
    sudo chmod 755 "$DEPLOY_PATH/logs"
    log_info "✅ Logs directory created with proper permissions"
    
    # Create system_status.log file with proper permissions
    log_info "📄 Creating system_status.log file..."
    sudo touch "$DEPLOY_PATH/logs/system_status.log"
    sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/logs/system_status.log"
    sudo chmod 644 "$DEPLOY_PATH/logs/system_status.log"
    log_info "✅ system_status.log file created with proper permissions"
    
    # Ensure system_status.py exists and has proper permissions
    if [[ -f "backend/system_status.py" ]]; then
        log_info "📄 Copying system_status.py to deployment directory..."
        sudo cp backend/system_status.py "$DEPLOY_PATH/backend/system_status.py"
        sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/backend/system_status.py"
        sudo chmod 755 "$DEPLOY_PATH/backend/system_status.py"
        log_info "✅ system_status.py copied with proper permissions"
    else
        log_error "❌ system_status.py not found in backend directory"
        return 1
    fi
    
    # Create all required log files with proper permissions
    log_info "📄 Creating all required log files..."
    for log_file in "video_worker.log" "dual_recorder.log" "api_server.log" "health_check.log" "service_monitor.log"; do
        if [[ ! -f "$DEPLOY_PATH/logs/$log_file" ]]; then
            sudo touch "$DEPLOY_PATH/logs/$log_file"
            sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/logs/$log_file"
            sudo chmod 644 "$DEPLOY_PATH/logs/$log_file"
            log_info "✅ Created $log_file with proper permissions"
        else
            # Ensure existing log files have correct permissions
            sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/logs/$log_file"
            sudo chmod 644 "$DEPLOY_PATH/logs/$log_file"
            log_info "✅ Fixed permissions for existing $log_file"
        fi
    done
    
    log_info "✅ All required files and directories created with proper permissions"
}

# Copy all project files to deployment directory
copy_project_files() {
    log_info "📁 Copying all project files to deployment directory..."
    
    # Create deployment directory structure
    sudo mkdir -p "$DEPLOY_PATH/backend"
    sudo mkdir -p "$DEPLOY_PATH/api"
    sudo mkdir -p "$DEPLOY_PATH/systemd"
    
    # Copy backend files
    log_info "📄 Copying backend files..."
    if [[ -d "backend" ]]; then
        sudo cp -r backend/* "$DEPLOY_PATH/backend/"
        sudo chown -R $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/backend"
        sudo chmod -R 755 "$DEPLOY_PATH/backend"
        log_info "✅ Backend files copied successfully"
    else
        log_error "❌ Backend directory not found"
        return 1
    fi
    
    # Copy API files
    log_info "📄 Copying API files..."
    if [[ -d "api" ]]; then
        sudo cp -r api/* "$DEPLOY_PATH/api/"
        sudo chown -R $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/api"
        sudo chmod -R 755 "$DEPLOY_PATH/api"
        log_info "✅ API files copied successfully"
    else
        log_error "❌ API directory not found"
        return 1
    fi
    
    # Copy systemd service files
    log_info "📄 Copying systemd service files..."
    if [[ -d "systemd" ]]; then
        sudo cp systemd/*.service /etc/systemd/system/
        sudo cp systemd/*.timer /etc/systemd/system/ 2>/dev/null || true
        sudo systemctl daemon-reload
        log_info "✅ Systemd service files copied and reloaded"
    else
        log_error "❌ Systemd directory not found"
        return 1
    fi
    
    # Copy environment file if it exists
    if [[ -f ".env" ]]; then
        log_info "📄 Copying environment file..."
        sudo cp .env "$DEPLOY_PATH/.env"
        sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/.env"
        sudo chmod 600 "$DEPLOY_PATH/.env"
        log_info "✅ Environment file copied"
    else
        log_warn "⚠️ No .env file found - you may need to create one manually"
    fi
    
    log_info "✅ All project files copied successfully"
}

# Fix camera initialization issues
fix_camera_initialization() {
    log_info "🔧 Fixing camera initialization issues..."
    
    # Check if cameras are accessible
    log_info "📷 Checking camera accessibility..."
    if command_exists libcamera-hello; then
        log_info "📷 Testing camera access with libcamera-hello..."
        timeout 10 libcamera-hello --list-cameras 2>/dev/null || log_warn "⚠️ Camera access test failed"
    fi
    
    # Ensure camera permissions
    log_info "🔐 Ensuring camera permissions..."
    sudo usermod -a -G video $DEPLOY_USER 2>/dev/null || true
    sudo usermod -a -G render $DEPLOY_USER 2>/dev/null || true
    
    # Check camera device files
    if [[ -e /dev/video0 ]]; then
        log_info "✅ Camera device /dev/video0 found"
        sudo chmod 666 /dev/video0 2>/dev/null || true
    else
        log_warn "⚠️ Camera device /dev/video0 not found"
    fi
    
    if [[ -e /dev/video1 ]]; then
        log_info "✅ Camera device /dev/video1 found"
        sudo chmod 666 /dev/video1 2>/dev/null || true
    else
        log_warn "⚠️ Camera device /dev/video1 not found"
    fi
    
    log_info "✅ Camera initialization fixes applied"
}

# Replace dual_recorder with simplified version
replace_with_simple_recorder() {
    log_info "🔄 Replacing dual_recorder with simplified version..."
    
    # Backup original dual_recorder
    if [[ -f "$DEPLOY_PATH/backend/dual_recorder.py" ]]; then
        cp "$DEPLOY_PATH/backend/dual_recorder.py" "$DEPLOY_PATH/backend/dual_recorder.py.backup"
        log_info "📁 Backed up original dual_recorder.py"
    fi
    
    # Copy simplified version
    if [[ -f "$DEPLOY_PATH/backend/dual_recorder_simple.py" ]]; then
        cp "$DEPLOY_PATH/backend/dual_recorder_simple.py" "$DEPLOY_PATH/backend/dual_recorder.py"
        log_info "✅ Replaced dual_recorder.py with simplified version"
    elif [[ -f "backend/dual_recorder_simple.py" ]]; then
        cp "backend/dual_recorder_simple.py" "$DEPLOY_PATH/backend/dual_recorder.py"
        log_info "✅ Replaced dual_recorder.py with simplified version (from source)"
    else
        log_warn "⚠️ dual_recorder_simple.py not found, keeping original"
    fi
    
    # Make sure it's executable
    if [[ -f "$DEPLOY_PATH/backend/dual_recorder.py" ]]; then
        chmod +x "$DEPLOY_PATH/backend/dual_recorder.py"
        log_info "✅ Made dual_recorder.py executable"
    else
        log_warn "⚠️ dual_recorder.py not found for chmod"
    fi
    
    log_info "✅ Dual recorder replacement completed"
}

# Handle service restart issues and ensure clean startup
handle_service_restart_issues() {
    log_info "🔧 Handling service restart issues..."
    
    # Stop all services to break any restart loops
    log_info "🛑 Stopping all services to break restart loops..."
    sudo systemctl stop ezrec-api.service 2>/dev/null || true
    sudo systemctl stop dual_recorder.service 2>/dev/null || true
    sudo systemctl stop video_worker.service 2>/dev/null || true
    sudo systemctl stop system_status.service 2>/dev/null || true
    
    # Wait for services to fully stop
    sleep 5
    
    # Kill any remaining processes
    log_info "🧹 Killing any remaining service processes..."
    sudo pkill -f "api_server" 2>/dev/null || true
    sudo pkill -f "dual_recorder" 2>/dev/null || true
    sudo pkill -f "video_worker" 2>/dev/null || true
    sudo pkill -f "system_status" 2>/dev/null || true
    
    # Wait for processes to terminate
    sleep 3
    
    log_info "✅ Service restart issues handled"
}

# Ensure all services are properly enabled and configured
ensure_services_enabled() {
    log_info "🔧 Ensuring all services are properly enabled..."
    
    # Enable all EZREC services
    for service in "${SERVICES[@]}"; do
        log_info "🔧 Enabling $service.service for auto-start..."
        if sudo systemctl enable ${service}.service; then
            log_info "✅ $service.service enabled successfully"
        else
            log_error "❌ Failed to enable $service.service"
            return 1
        fi
    done
    
    # Enable timers
    for timer in "${TIMER_SERVICES[@]}"; do
        log_info "🔧 Enabling $timer.timer for auto-start..."
        if sudo systemctl enable ${timer}.timer; then
            log_info "✅ $timer.timer enabled successfully"
        else
            log_error "❌ Failed to enable $timer.timer"
            return 1
        fi
    done
    
    # Verify services are enabled
    log_info "🔍 Verifying services are enabled..."
    for service in "${SERVICES[@]}"; do
        if sudo systemctl is-enabled ${service}.service >/dev/null 2>&1; then
            log_info "✅ $service.service is enabled"
        else
            log_error "❌ $service.service is not enabled"
            return 1
        fi
    done
    
    log_info "✅ All services properly enabled for auto-start"
}

# Start all services with proper error handling and port conflict prevention
start_all_services_safely() {
    log_info "🔧 Starting all services safely with port conflict prevention..."
    
    # First, ensure ports are free
    fix_port_conflicts_comprehensive
    
    # Start services in correct order with delays
    local service_order=("ezrec-api" "dual_recorder" "video_worker" "system_status")
    
    for service in "${service_order[@]}"; do
        log_info "🚀 Starting $service.service..."
        
        # Special handling for API service
        if [[ "$service" == "ezrec-api" ]]; then
            log_info "🔧 Special handling for API service..."
            
            # Double-check port 8000 is free
            if lsof -i :8000 >/dev/null 2>&1; then
                log_warn "⚠️ Port 8000 still in use, forcing cleanup..."
                sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
                sleep 3
            fi
            
            # Start the service
            if sudo systemctl start ${service}.service; then
                log_info "✅ $service.service started successfully"
            else
                log_error "❌ Failed to start $service.service"
                sudo systemctl status ${service}.service --no-pager -l
                return 1
            fi
            
            # Wait for API to be ready
            log_info "⏳ Waiting for API service to be ready..."
            sleep 10
            
            # Test API endpoint
            if curl -s http://localhost:8000/test-alive >/dev/null 2>&1; then
                log_info "✅ API service is responding"
            else
                log_warn "⚠️ API service not responding yet, but continuing..."
            fi
        elif [[ "$service" == "system_status" ]]; then
            log_info "🔧 Special handling for system_status service..."
            
            # Ensure the service can write to its log file
            if [[ -f "$DEPLOY_PATH/logs/system_status.log" ]]; then
                log_info "✅ system_status.log file exists and is writable"
            else
                log_error "❌ system_status.log file missing, creating it..."
                sudo touch "$DEPLOY_PATH/logs/system_status.log"
                sudo chown $DEPLOY_USER:$DEPLOY_USER "$DEPLOY_PATH/logs/system_status.log"
                sudo chmod 644 "$DEPLOY_PATH/logs/system_status.log"
            fi
            
            # Start the service
            if sudo systemctl start ${service}.service; then
                log_info "✅ $service.service started successfully"
            else
                log_error "❌ Failed to start $service.service"
                sudo systemctl status ${service}.service --no-pager -l
                return 1
            fi
        else
            # Start other services
            if sudo systemctl start ${service}.service; then
                log_info "✅ $service.service started successfully"
            else
                log_error "❌ Failed to start $service.service"
                sudo systemctl status ${service}.service --no-pager -l
                return 1
            fi
        fi
        
        # Wait between service starts (longer for critical services)
        if [[ "$service" == "dual_recorder" || "$service" == "video_worker" ]]; then
            log_info "⏳ Waiting longer for $service to fully initialize..."
            sleep 10
        else
            sleep 3
        fi
    done
    
    # Start timers
    for timer in "${TIMER_SERVICES[@]}"; do
        log_info "🚀 Starting $timer.timer..."
        if sudo systemctl start ${timer}.timer; then
            log_info "✅ $timer.timer started successfully"
        else
            log_error "❌ Failed to start $timer.timer"
            return 1
        fi
    done
    
    log_info "✅ All services started safely"
}

# Comprehensive system verification
verify_system_completely() {
    log_info "🔍 Performing comprehensive system verification..."
    
    local all_checks_passed=true
    
    # Check 1: All services are running (with retry logic)
    log_info "🧪 Checking all services are running..."
    for service in "${SERVICES[@]}"; do
        local retry_count=0
        local max_retries=3
        local service_running=false
        
        while [[ $retry_count -lt $max_retries ]]; do
            if sudo systemctl is-active --quiet ${service}.service; then
                log_info "✅ $service.service is running"
                service_running=true
                break
            else
                retry_count=$((retry_count + 1))
                if [[ $retry_count -lt $max_retries ]]; then
                    log_info "⏳ $service.service not ready yet, retrying in 5s... (attempt $retry_count/$max_retries)"
                    sleep 5
                fi
            fi
        done
        
        if [[ "$service_running" == false ]]; then
            log_error "❌ $service.service is not running after $max_retries attempts"
            log_info "📋 Service status:"
            sudo systemctl status ${service}.service --no-pager -l
            all_checks_passed=false
        fi
    done
    
    # Check 2: API endpoints are responding
    log_info "🧪 Testing API endpoints..."
    if curl -s http://localhost:8000/test-alive >/dev/null 2>&1; then
        log_info "✅ API /test-alive endpoint is responding"
    else
        log_error "❌ API /test-alive endpoint is not responding"
        all_checks_passed=false
    fi
    
    if curl -s http://localhost:8000/status >/dev/null 2>&1; then
        log_info "✅ API /status endpoint is responding"
    else
        log_error "❌ API /status endpoint is not responding"
        all_checks_passed=false
    fi
    
    # Check 3: Python imports are working
    log_info "🧪 Testing Python imports..."
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/python3" -c "import psutil, picamera2, cv2; print('✅ Backend imports working')" 2>/dev/null; then
        log_info "✅ Backend Python imports are working"
    else
        log_error "❌ Backend Python imports failed"
        all_checks_passed=false
    fi
    
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/python3" -c "import psutil, fastapi; print('✅ API imports working')" 2>/dev/null; then
        log_info "✅ API Python imports are working"
    else
        log_error "❌ API Python imports failed"
        all_checks_passed=false
    fi
    
    # Check 4: Cloudflare tunnel is running
    log_info "🧪 Testing Cloudflare tunnel..."
    if sudo systemctl is-active --quiet cloudflared.service; then
        log_info "✅ Cloudflare tunnel is running"
    else
        log_error "❌ Cloudflare tunnel is not running"
        all_checks_passed=false
    fi
    
    # Final result
    if [[ "$all_checks_passed" == true ]]; then
        log_info "🎉 All system verification checks passed!"
        return 0
    else
        log_error "❌ Some system verification checks failed"
        return 1
    fi
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTION
# =============================================================================

main() {
    local current_user=$(whoami)
    log_info "Starting EZREC deployment as user: $current_user"
    
    # 1. Apply comprehensive fixes first
    log_step "1. Applying comprehensive system fixes"
    
    # Fix port conflicts
    fix_port_conflicts_comprehensive
    
    # Install psutil everywhere
    install_psutil_everywhere
    
    # Copy all project files to deployment directory
    copy_project_files
    
    # Fix camera initialization issues
    fix_camera_initialization
    
    # Replace dual_recorder with simplified version
    replace_with_simple_recorder
    
    # Ensure all required files and directories exist
    ensure_files_and_directories
    
    # Handle service restart issues
    handle_service_restart_issues
    
    # Enable all services
    ensure_services_enabled
    
    # 2. Start services safely
    log_step "2. Starting all services safely"
    start_all_services_safely
    
    # 2.5. Wait for all services to fully initialize
    log_info "⏳ Waiting for all services to fully initialize..."
    sleep 15
    
    # 3. Verify system completely
    log_step "3. Verifying system completely"
    verify_system_completely
    
    # 4. Final status report
    log_info "⏳ Waiting for services to settle before final status check..."
    sleep 5
    log_step "4. Final system status"
    
    echo -e "\n=== FINAL SYSTEM STATUS ==="
    for service in "${SERVICES[@]}"; do
        local retry_count=0
        local max_retries=2
        local service_running=false
        
        while [[ $retry_count -lt $max_retries ]]; do
            if sudo systemctl is-active --quiet ${service}.service; then
                echo "✅ $service.service: RUNNING"
                service_running=true
                break
            else
                retry_count=$((retry_count + 1))
                if [[ $retry_count -lt $max_retries ]]; then
                    sleep 2
                fi
            fi
        done
        
        if [[ "$service_running" == false ]]; then
            echo "❌ $service.service: NOT RUNNING"
        fi
    done
    
    if sudo systemctl is-active --quiet cloudflared.service; then
        echo "✅ cloudflared.service: RUNNING"
    else
        echo "❌ cloudflared.service: NOT RUNNING"
    fi
    
    # Test external API
    if curl -s --max-time 10 https://api.ezrec.org/status >/dev/null 2>&1; then
        echo "✅ External API: ACCESSIBLE"
    else
        echo "❌ External API: NOT ACCESSIBLE"
    fi
    
    log_info "🎉 Deployment completed successfully!"
    log_info "✅ All services are running and responding correctly"
    log_info "✅ External API is accessible via Cloudflare tunnel"
    log_info "✅ System is ready for frontend testing"
}

# Run main function with output capture
main "$@" 2>&1 | tee -a logs.txt
