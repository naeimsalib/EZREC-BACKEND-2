#!/bin/bash

# EZREC Backend Deployment Script
# Clean, efficient deployment with proper error handling and modular structure

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

# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

# Setup users and groups
setup_users() {
    log_step "Setting up users and groups"
    
    # Create ezrec user if it doesn't exist
    if ! user_exists "ezrec"; then
        sudo useradd -r -s /bin/false -d $DEPLOY_PATH ezrec
        log_info "Created ezrec user"
    fi
    
    # Ensure deploy user exists
    if ! user_exists "$DEPLOY_USER"; then
        sudo useradd -m -s /bin/bash $DEPLOY_USER
        log_info "Created $DEPLOY_USER user"
    fi
    
    # Add users to video group
    sudo usermod -a -G video $DEPLOY_USER
    sudo usermod -a -G video ezrec
    log_info "Added users to video group"
}

# Install system dependencies
install_dependencies() {
    log_step "Installing system dependencies"
    
    sudo apt update
    sudo apt install -y \
        build-essential libjpeg-dev \
        ffmpeg \
        v4l-utils \
        imagemagick \
        python3-libcamera \
        python3-picamera2 \
        python3-pip \
        python3-venv \
        python3-dev \
        libavcodec-extra \
        libavdevice-dev \
        libavfilter-dev \
        libavformat-dev \
        libavutil-dev \
        libswscale-dev \
        libswresample-dev \
        v4l2loopback-dkms \
        git curl wget vim htop
    
    log_info "System dependencies installed"
}

# Setup directory structure
setup_directories() {
    log_step "Setting up directory structure"
    
    sudo mkdir -p $DEPLOY_PATH/{recordings,processed,final,assets,logs,events,api/local_data,media_cache}
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    sudo chmod -R 755 $DEPLOY_PATH
    
    # Ensure logs directory has proper permissions
    sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/logs
    sudo chmod 755 $DEPLOY_PATH/logs
    
    log_info "Directory structure created"
}

# Setup virtual environment
setup_venv() {
    local path=$1
    local name=$2
    
    log_info "Setting up $name virtual environment"
    
    cd "$path"
    sudo rm -rf venv 2>/dev/null || true
    sudo -u $DEPLOY_USER python3 -m venv --system-site-packages venv
    
    # Install dependencies
    sudo -u $DEPLOY_USER venv/bin/pip install --upgrade pip
    sudo -u $DEPLOY_USER venv/bin/pip install -r ../requirements.txt
    sudo -u $DEPLOY_USER venv/bin/pip install --upgrade "typing-extensions>=4.12.0"
    sudo -u $DEPLOY_USER venv/bin/pip install --force-reinstall --no-binary simplejpeg simplejpeg
    
    log_info "$name virtual environment ready"
}

# Create kms.py placeholder for picamera2 compatibility
create_kms_placeholder() {
    log_info "Creating kms.py placeholder for picamera2 compatibility"
    
    cd $DEPLOY_PATH/backend
    SITE_PACKAGES=$(sudo -u $DEPLOY_USER venv/bin/python3 -c "import distutils.sysconfig as s; print(s.get_python_lib())")
    
    sudo -u $DEPLOY_USER tee "$SITE_PACKAGES/kms.py" > /dev/null << 'EOF'
"""
Placeholder kms module for picamera2 compatibility
"""
import sys
import warnings

warnings.warn("Using placeholder kms module – picamera2 may not work correctly")

class PixelFormat:
    XRGB8888 = "XRGB8888"
    RGB888 = "RGB888"
    BGR888 = "BGR888"
    YUV420 = "YUV420"
    NV12 = "NV12"
    NV21 = "NV21"

class KMS:
    def __init__(self):
        pass
    
    def close(self):
        pass

def create_kms():
    return KMS()

__all__ = ['KMS', 'create_kms', 'PixelFormat']
EOF
    
    sudo -u $DEPLOY_USER ln -sf "$SITE_PACKAGES/kms.py" "$SITE_PACKAGES/pykms.py"
    log_info "kms.py placeholder created"
}

# Setup files and permissions
setup_files() {
    log_step "Setting up files and permissions"
    
    # Create log files
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/dual_recorder.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/video_worker.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/ezrec-api.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/system_status.log
    sudo chmod 644 $DEPLOY_PATH/logs/*.log
    
    # Create bookings.json
    sudo -u $DEPLOY_USER tee $DEPLOY_PATH/api/local_data/bookings.json > /dev/null << 'EOF'
[]
EOF
    
    # Create status file
    sudo -u $DEPLOY_USER tee $DEPLOY_PATH/status.json > /dev/null << EOF
{
  "is_recording": false,
  "last_update": "$(date -Iseconds)",
  "system_status": "deployed"
}
EOF
    sudo chmod 664 $DEPLOY_PATH/status.json
    
    # Set final permissions
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    sudo chmod -R 755 $DEPLOY_PATH
    sudo chmod 644 $DEPLOY_PATH/.env 2>/dev/null || true
    
    log_info "Files and permissions set up"
}

# Install systemd services
install_services() {
    log_step "Installing systemd services"
    
    sudo cp $DEPLOY_PATH/systemd/*.service /etc/systemd/system/
    sudo cp $DEPLOY_PATH/systemd/*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    
    # Enable services
    for service in "${SERVICES[@]}"; do
        sudo systemctl enable ${service}.service
    done
    
    # Enable timers
    for timer in "${TIMER_SERVICES[@]}"; do
        sudo systemctl enable ${timer}.timer
    done
    
    log_info "Systemd services installed and enabled"
}

# Setup cron jobs
setup_cron() {
    log_step "Setting up cron jobs"
    
    # Add cleanup job to root crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * $DEPLOY_PATH/backend/cleanup_old_data.py > $DEPLOY_PATH/logs/cleanup.log 2>&1") | crontab -
    
    log_info "Cron jobs configured"
}

# Start services
start_services() {
    log_step "Starting services"
    
    # Start main services
    for service in "${SERVICES[@]}"; do
        sudo systemctl start ${service}.service
    done
    
    # Start timers
    for timer in "${TIMER_SERVICES[@]}"; do
        sudo systemctl start ${timer}.timer
    done
    
    # Wait for services to start
    sleep 5
    
    # Reset any failed services
    for service in "${SERVICES[@]}"; do
        sudo systemctl reset-failed ${service}.service 2>/dev/null || true
    done
    
    # Restart services to ensure they use new virtual environments
    for service in "${SERVICES[@]}"; do
        sudo systemctl restart ${service}.service
    done
    
    # Wait for final startup
    sleep 10
    
    log_info "Services started"
}

# Validate deployment
validate_deployment() {
    log_step "Validating deployment"
    
    # Check service status
    local failed_services=()
    for service in "${SERVICES[@]}"; do
        if ! check_service_status ${service}.service; then
            failed_services+=($service)
        fi
    done
    
    # Check critical files
    local missing_files=()
    local critical_files=(
        "$DEPLOY_PATH/.env"
        "$DEPLOY_PATH/backend/venv/bin/python3"
        "$DEPLOY_PATH/api/venv/bin/python3"
        "$DEPLOY_PATH/status.json"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=($file)
        fi
    done
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 && ${#missing_files[@]} -eq 0 ]]; then
        log_info "✅ Deployment validation passed"
        return 0
    else
        log_error "❌ Deployment validation failed"
        [[ ${#failed_services[@]} -gt 0 ]] && log_error "Failed services: ${failed_services[*]}"
        [[ ${#missing_files[@]} -gt 0 ]] && log_error "Missing files: ${missing_files[*]}"
        return 1
    fi
}

# Test picamera2 import
test_picamera2() {
    log_info "Testing picamera2 import"
    
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "import picamera2; print('✅ picamera2 imported successfully')" 2>/dev/null; then
        log_info "✅ picamera2 import test passed"
    else
        log_warn "⚠️ picamera2 import test failed - check system packages"
    fi
}

# =============================================================================
# MAIN DEPLOYMENT PROCESS
# =============================================================================

main() {
    local current_user=$(whoami)
    log_info "Starting EZREC deployment as user: $current_user"
    
    # 1. Stop and kill old services
    log_step "1. Stopping old services"
    manage_services "stop" "${SERVICES[@]}"
    manage_services "disable" "${SERVICES[@]}"
    kill_processes "dual_recorder.py" "video_worker.py" "api_server.py" "system_status.py"
    
    # 2. Backup and cleanup old installation
    log_step "2. Cleaning up old installation"
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        log_info "Backing up existing .env file"
        sudo cp $DEPLOY_PATH/.env /tmp/ezrec_env_backup
    fi
    
    sudo rm -rf $DEPLOY_PATH
    sudo mkdir -p $DEPLOY_PATH
    
    # 3. Copy project files
    log_step "3. Copying project files"
    sudo cp -r . $DEPLOY_PATH/
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    
    # Restore .env if it existed
    if [[ -f "/tmp/ezrec_env_backup" ]]; then
        log_info "Restoring .env file"
        sudo cp /tmp/ezrec_env_backup $DEPLOY_PATH/.env
        sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/.env
        sudo chmod 644 $DEPLOY_PATH/.env
    fi
    
    # 4. Install dependencies
    install_dependencies
    
    # 5. Setup users and directories
    setup_users
    setup_directories
    
    # 6. Setup virtual environments
    log_step "6. Setting up virtual environments"
    setup_venv "$DEPLOY_PATH/backend" "backend"
    setup_venv "$DEPLOY_PATH/api" "API"
    
    # 7. Apply fixes
    log_step "7. Applying fixes"
    create_kms_placeholder
    
    # Create assets
    log_info "Creating placeholder assets"
    cd $DEPLOY_PATH
    sudo -u $DEPLOY_USER python3 backend/create_assets.py
    
    # 8. Setup files and services
    setup_files
    install_services
    setup_cron
    
    # 9. Start services
    start_services
    
    # 10. Validate deployment
    validate_deployment
    test_picamera2
    
    # 11. Final checks
    log_step "11. Final checks"
    
    # Check .env file
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        log_info "✅ .env file exists"
    else
        log_warn "⚠️ .env file not found - create it manually:"
        log_info "sudo cp $DEPLOY_PATH/env.example $DEPLOY_PATH/.env"
        log_info "sudo nano $DEPLOY_PATH/.env"
    fi
    
    # Show directory structure
    log_info "Directory structure:"
    ls -la $DEPLOY_PATH/
    
    # Show virtual environments
    log_info "Virtual environments:"
    ls -la $DEPLOY_PATH/backend/venv/bin/python3
    ls -la $DEPLOY_PATH/api/venv/bin/python3
    
    # Show assets
    log_info "Assets:"
    ls -la $DEPLOY_PATH/assets/
    
    log_info "🎉 EZREC deployment completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Configure your .env file with your actual credentials"
    log_info "2. Check service logs: sudo journalctl -u dual_recorder.service -f"
    log_info ""
    log_info "Services are now running and will start automatically on boot."
}

# Run main function
main "$@"
