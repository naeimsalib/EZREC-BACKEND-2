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
    
    # Install dependencies with better error handling
    sudo -u $DEPLOY_USER venv/bin/pip install --upgrade pip
    sudo -u $DEPLOY_USER venv/bin/pip install -r ../requirements.txt
    
    # Fix typing-extensions conflict
    sudo -u $DEPLOY_USER venv/bin/pip install --upgrade "typing-extensions>=4.12.0"
    
    # Install simplejpeg with proper error handling
    if ! sudo -u $DEPLOY_USER venv/bin/pip install --force-reinstall --no-binary simplejpeg simplejpeg; then
        log_warn "Failed to install simplejpeg, trying alternative method"
        sudo -u $DEPLOY_USER venv/bin/pip install simplejpeg
    fi
    
    # Ensure PyAV is upgraded to compatible version for picamera2
    log_info "Upgrading PyAV to ensure picamera2 compatibility"
    sudo -u $DEPLOY_USER venv/bin/pip install --upgrade "av>=15.0.0"
    
    # Verify picamera2 compatibility
    log_info "Verifying picamera2 and PyAV compatibility"
    if sudo -u $DEPLOY_USER venv/bin/python3 -c "import picamera2; import av; print('✅ picamera2 and PyAV compatibility verified')" 2>/dev/null; then
        log_info "✅ picamera2 and PyAV compatibility verified"
    else
        log_warn "⚠️ picamera2 and PyAV compatibility check failed"
    fi
    
    log_info "$name virtual environment ready"
}

# Create improved kms.py placeholder for picamera2 compatibility
create_kms_placeholder() {
    log_info "Creating improved kms.py placeholder for picamera2 compatibility"
    
    cd $DEPLOY_PATH/backend
    SITE_PACKAGES=$(sudo -u $DEPLOY_USER venv/bin/python3 -c "import distutils.sysconfig as s; print(s.get_python_lib())")
    
    sudo -u $DEPLOY_USER tee "$SITE_PACKAGES/kms.py" > /dev/null << 'EOF'
"""
Improved placeholder kms module for picamera2 compatibility
"""
import sys
import warnings

warnings.warn("Using placeholder kms module – picamera2 may not work correctly")

class PixelFormat:
    # Standard formats
    XRGB8888 = "XRGB8888"
    XBGR8888 = "XBGR8888"
    RGB888 = "RGB888"
    BGR888 = "BGR888"
    
    # YUV formats
    YUV420 = "YUV420"
    YUV422 = "YUV422"
    YUV444 = "YUV444"
    YVU420 = "YVU420"  # Added missing attribute
    YVU422 = "YVU422"  # Added missing attribute
    YVU444 = "YVU444"  # Added missing attribute
    
    # NV formats
    NV12 = "NV12"
    NV21 = "NV21"
    
    # RGB565 formats (little endian)
    RGB565 = "RGB565"
    BGR565 = "BGR565"
    RGB565_LE = "RGB565_LE"  # Added missing attribute
    BGR565_LE = "BGR565_LE"  # Added missing attribute
    
    # YUV packed formats
    YUYV = "YUYV"
    UYVY = "UYVY"
    
    # Additional formats that might be needed
    RGB24 = "RGB24"
    BGR24 = "BGR24"
    ARGB8888 = "ARGB8888"
    ABGR8888 = "ABGR8888"
    RGBA8888 = "RGBA8888"
    BGRA8888 = "BGRA8888"

class KMS:
    def __init__(self):
        pass
    
    def close(self):
        pass
    
    def create_framebuffer(self, width, height, pixel_format):
        return None
    
    def create_connector(self):
        return None

def create_kms():
    return KMS()

# Add more functions that picamera2 might need
def get_connector_info(connector):
    return None

def get_crtc_info(crtc):
    return None

__all__ = ['KMS', 'create_kms', 'PixelFormat', 'get_connector_info', 'get_crtc_info']
EOF
    
    sudo -u $DEPLOY_USER ln -sf "$SITE_PACKAGES/kms.py" "$SITE_PACKAGES/pykms.py"
    log_info "Improved kms.py placeholder created"
}

# Download user assets and company logo
download_user_assets() {
    log_info "Downloading user assets and company logo"
    
    cd $DEPLOY_PATH
    
    # Get user_id from .env file
    USER_ID=$(grep "^USER_ID=" .env | cut -d'=' -f2)
    if [[ -z "$USER_ID" ]]; then
        log_warn "USER_ID not found in .env file, skipping user asset download"
        return
    fi
    
    # Create single assets directory for all assets
    ASSETS_DIR="$DEPLOY_PATH/assets"
    sudo -u $DEPLOY_USER mkdir -p "$ASSETS_DIR"
    
    # Download main company logo (always required) - from root of bucket
    log_info "Downloading main company logo..."
    COMPANY_LOGO_PATH="$ASSETS_DIR/ezrec_logo.png"
    
    # Capture the actual download result
    COMPANY_LOGO_RESULT=$(sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "
import boto3
import os
import sys
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv('/opt/ezrec-backend/.env')

# Get AWS credentials
bucket = os.getenv('AWS_USER_MEDIA_BUCKET') or os.getenv('AWS_S3_BUCKET')
region = os.getenv('AWS_REGION')
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

if not all([bucket, region, access_key, secret_key]):
    print('❌ Missing AWS credentials for asset download')
    sys.exit(1)

try:
    s3 = boto3.client('s3', region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    
    # Download company logo from root of bucket
    try:
        s3.download_file(bucket, 'main_ezrec_logo.png', '$COMPANY_LOGO_PATH')
        print('✅ Downloaded company logo: main_ezrec_logo.png')
        sys.exit(0)
    except Exception as e:
        print(f'❌ Company logo not found: {e}')
        sys.exit(1)
        
except Exception as e:
    print(f'⚠️ Error downloading company logo: {e}')
    sys.exit(1)
" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        log_info "✅ Company logo downloaded successfully"
    else
        log_warn "⚠️ Company logo download failed: $COMPANY_LOGO_RESULT"
    fi
    
    # Download user assets from user-specific folders
    log_info "Checking for user assets in user folder..."
    USER_ASSETS_RESULT=$(sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "
import boto3
import os
import sys
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv('/opt/ezrec-backend/.env')

# Get AWS credentials
bucket = os.getenv('AWS_USER_MEDIA_BUCKET') or os.getenv('AWS_S3_BUCKET')
region = os.getenv('AWS_REGION')
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

if not all([bucket, region, access_key, secret_key]):
    print('❌ Missing AWS credentials for asset download')
    sys.exit(1)

try:
    s3 = boto3.client('s3', region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    
    # Define user assets with correct paths based on S3 structure
    user_assets = [
        # User logo from logo folder
        ('$USER_ID/logo/logo.png', '$ASSETS_DIR/user_logo.png'),
        # Intro video from intro-video folder
        ('$USER_ID/intro-video/intro.mp4', '$ASSETS_DIR/intro.mp4'),
        # Sponsor logos from sponsor-logo folders
        ('$USER_ID/sponsor-logo1/logo1.png', '$ASSETS_DIR/sponsor_logo1.png'),
        ('$USER_ID/sponsor-logo2/logo2.png', '$ASSETS_DIR/sponsor_logo2.png'),
        ('$USER_ID/sponsor-logo3/logo3.png', '$ASSETS_DIR/sponsor_logo3.png'),
    ]
    
    downloaded_count = 0
    
    for s3_key, local_path in user_assets:
        try:
            s3.download_file(bucket, s3_key, local_path)
            print(f'✅ Downloaded: {s3_key} -> {local_path}')
            downloaded_count += 1
        except Exception as e:
            print(f'⚠️ Not found: {s3_key}')
    
    print(f'📊 Downloaded {downloaded_count} user assets')
    
    # List all objects in bucket for debugging
    try:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
        if 'Contents' in response:
            print('📋 Available objects in bucket:')
            for obj in response['Contents']:
                print(f'  - {obj[\"Key\"]}')
        else:
            print('📋 Bucket appears to be empty')
    except Exception as e:
        print(f'⚠️ Could not list bucket contents: {e}')
    
    # Exit with success if at least one asset was downloaded
    if downloaded_count > 0:
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f'⚠️ Error checking user assets: {e}')
    sys.exit(1)
" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        log_info "✅ User asset download completed successfully"
    else
        log_warn "⚠️ User asset download failed or no assets found: $USER_ASSETS_RESULT"
    fi
    
    # Set proper permissions
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER "$ASSETS_DIR"
    sudo chmod -R 755 "$ASSETS_DIR"
    
    log_info "Asset download process completed"
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

# Start services with improved error handling
start_services() {
    log_step "Starting services"
    
    # Start main services
    for service in "${SERVICES[@]}"; do
        log_info "Starting $service.service"
        if ! sudo systemctl start ${service}.service; then
            log_error "Failed to start $service.service"
            # Try to get more details about the failure
            sudo systemctl status ${service}.service --no-pager -l
        fi
    done
    
    # Start timers
    for timer in "${TIMER_SERVICES[@]}"; do
        log_info "Starting $timer.timer"
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
        log_info "Restarting $service.service"
        sudo systemctl restart ${service}.service
    done
    
    # Wait for final startup
sleep 10

    log_info "Services started"
}

# Enhanced validation with detailed checks
validate_deployment() {
    log_step "Validating deployment"
    
    # Check service status with detailed reporting
    local failed_services=()
    local successful_services=()
    
    for service in "${SERVICES[@]}"; do
        if check_service_status ${service}.service; then
            successful_services+=($service)
        else
            failed_services+=($service)
            # Show detailed status for failed services
            log_error "Detailed status for $service:"
            sudo systemctl status ${service}.service --no-pager -l
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
    
    # Test Python imports
    log_info "Testing Python imports..."
    test_python_import "$DEPLOY_PATH/backend/venv" "picamera2" "picamera2"
    test_python_import "$DEPLOY_PATH/api/venv" "fastapi" "FastAPI"
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 && ${#missing_files[@]} -eq 0 ]]; then
        log_info "✅ Deployment validation passed"
        log_info "✅ Successful services: ${successful_services[*]}"
        return 0
    else
        log_error "❌ Deployment validation failed"
        [[ ${#failed_services[@]} -gt 0 ]] && log_error "Failed services: ${failed_services[*]}"
        [[ ${#missing_files[@]} -gt 0 ]] && log_error "Missing files: ${missing_files[*]}"
        return 1
    fi
}

# Test picamera2 import with detailed error reporting
test_picamera2() {
    log_info "Testing picamera2 import with detailed error reporting"
    
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "import picamera2; print('✅ picamera2 imported successfully')" 2>/dev/null; then
        log_info "✅ picamera2 import test passed"
    else
        log_warn "⚠️ picamera2 import test failed - showing detailed error:"
        sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "import picamera2" 2>&1 || true
    fi
}

# Test system_status service manually
test_system_status() {
    log_info "Testing system_status service manually"
    
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 $DEPLOY_PATH/backend/system_status.py 2>/dev/null; then
        log_info "✅ system_status service test passed"
        return 0
    else
        log_warn "⚠️ system_status service test failed - showing detailed error:"
        sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 $DEPLOY_PATH/backend/system_status.py 2>&1 || true
        return 1
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
    
    # Ensure working video_worker is deployed
    log_info "Deploying working video_worker with all fixes..."
    if [[ -f "$DEPLOY_PATH/backend/video_worker.py" ]]; then
        log_info "✅ video_worker.py exists and will be used"
    else
        log_warn "⚠️ video_worker.py not found in deployment"
    fi
    
    # Create assets
    log_info "Creating placeholder assets"
    cd $DEPLOY_PATH
    sudo -u $DEPLOY_USER python3 backend/create_assets.py
    
    # Download user assets and company logo
    download_user_assets
    
    # 8. Setup files and services
    setup_files
    install_services
    setup_cron
    
    # 9. Start services
    start_services
    
    # 10. Validate deployment
    validate_deployment
    test_picamera2
    test_system_status
    
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
    
    # Show service status
    log_info "Service status:"
    for service in "${SERVICES[@]}"; do
        sudo systemctl is-active --quiet ${service}.service && log_info "✅ $service: ACTIVE" || log_error "❌ $service: FAILED"
    done
    
    log_info "🎉 EZREC deployment completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Configure your .env file with your actual credentials"
    log_info "2. Check service logs: sudo journalctl -u dual_recorder.service -f"
    log_info "3. Test system: sudo systemctl status system_status.service"
    log_info ""
    log_info "Services are now running and will start automatically on boot."
    
    # Final comprehensive system check
    log_step "12. Final comprehensive system check"
    log_info "Running comprehensive system health check..."
    
    # Service status check
    echo "=== FULL SYSTEM HEALTH CHECK ==="
    echo "--- SERVICE STATUS ---"
    systemctl status dual_recorder.service video_worker.service ezrec-api.service system_status.service --no-pager
    
    echo -e "\n--- SERVICE VALIDATION ---"
    for service in dual_recorder video_worker ezrec-api system_status; do
        echo "Testing $service:"
        if sudo systemctl is-active --quiet ${service}.service; then
            echo "✅ $service: ACTIVE"
        else
            echo "❌ $service: FAILED"
        fi
    done
    
    echo -e "\n--- PYTHON IMPORT TESTS ---"
    echo "Testing picamera2 import:"
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "import picamera2; print('✅ picamera2 imported successfully')" 2>/dev/null; then
        echo "✅ picamera2 import test passed"
    else
        echo "❌ picamera2 import test failed"
    fi
    
    echo "Testing system_status script:"
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 $DEPLOY_PATH/backend/system_status.py 2>/dev/null; then
        echo "✅ system_status script executed successfully"
    else
        echo "❌ system_status script failed"
    fi
    
    echo -e "\n--- LOG FILES CHECK ---"
    ls -la $DEPLOY_PATH/logs/
    
    echo -e "\n--- RECENT LOGS (Last 5 entries each) ---"
    for service in dual_recorder video_worker ezrec-api system_status; do
        echo "--- $service LOGS ---"
        journalctl -u ${service}.service --no-pager -n 5
    done
    
    echo -e "\n--- SYSTEM STATUS FILE ---"
    cat $DEPLOY_PATH/status.json
    
    echo -e "\n--- KMS.PY CHECK ---"
    if sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "import kms; print('✅ kms.py imported successfully'); print('XBGR8888 available:', hasattr(kms.PixelFormat, 'XBGR8888')); print('YVU420 available:', hasattr(kms.PixelFormat, 'YVU420'))" 2>/dev/null; then
        echo "✅ kms.py placeholder working correctly"
    else
        echo "❌ kms.py placeholder has issues"
    fi
    
    echo -e "\n--- FINAL SUMMARY ---"
    echo "All services should be ACTIVE and all tests should pass ✅"
    log_info "Comprehensive system check completed!"
}

# Run main function
main "$@"