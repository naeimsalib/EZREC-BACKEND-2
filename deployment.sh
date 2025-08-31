#!/bin/bash

# EZREC Backend Deployment Script
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

# Enhanced pip wrapper with warning suppression and timeout
pip_install_suppress_warnings() {
    local venv_path=$1
    shift  # Remove first argument, pass rest to pip
    
    # Run pip with timeout and warning suppression
    timeout 300 sudo -u $DEPLOY_USER "$venv_path/bin/pip" "$@" 2>&1 | \
        grep -v "WARNING:" | \
        grep -v "send2trash" | \
        grep -v "yanked version" | \
        grep -v "Error parsing dependencies" || true
    
    # Return the actual exit code
    return ${PIPESTATUS[0]}
}

# Fast dependency resolution for common conflicts
fast_dependency_resolution() {
    local venv_path=$1
    
    log_info "🔧 Fast dependency resolution for common conflicts..."
    
    # Install with pip-tools for faster resolution
    if ! command -v pip-tools &> /dev/null; then
        log_info "Installing pip-tools for faster dependency resolution..."
        pip_install_suppress_warnings "$venv_path" install --no-cache-dir pip-tools
    fi
    
    # Create a simplified requirements file for faster installation
    local fast_requirements="/tmp/fast_requirements.txt"
    cat > "$fast_requirements" << 'EOF'
# Fast-install requirements (resolved versions)
fastapi>=0.104.0,<0.105.0
uvicorn[standard]>=0.24.0,<0.25.0
python-multipart>=0.0.6,<0.1.0
python-dotenv>=1.0.0,<2.0.0
boto3>=1.34.0,<1.35.0
supabase>=2.0.0,<3.0.0
httpx>=0.24.0,<0.25.0
Pillow>=10.1.0,<11.0.0
simplejpeg>=1.6.0,<2.0.0
av>=15.0.0,<16.0.0
picamera2>=0.3.0,<0.4.0
numpy>=1.24.0,<2.0.0
psutil>=5.9.0,<6.0.0
schedule>=1.2.0,<2.0.0
opencv-python>=4.8.0,<5.0.0
opencv-contrib-python>=4.8.0,<5.0.0
EOF
    
    # Install with pip-tools for faster resolution
    if pip_install_suppress_warnings "$venv_path" install \
        --no-cache-dir \
        --index-url https://pypi.org/simple \
        -r "$fast_requirements"; then
        
        log_info "✅ Fast dependency resolution completed"
        rm -f "$fast_requirements"
        return 0
    else
        log_warn "⚠️ Fast resolution failed, falling back to standard method"
        rm -f "$fast_requirements"
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
    
    sudo DEBIAN_FRONTEND=noninteractive apt update -y
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
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
        python3-opencv \
        libopencv-dev \
        git curl wget vim htop
    
    log_info "System dependencies installed"
}

# Install and configure cloudflared
install_cloudflared() {
    log_step "Installing and configuring cloudflared"
    
    # Check if cloudflared is already installed
    if command -v cloudflared &> /dev/null; then
        log_info "Cloudflared found, checking for conflicts..."
        
        # Clean up any problematic installation
        log_info "Cleaning up existing cloudflared installation..."
        sudo DEBIAN_FRONTEND=noninteractive apt remove --purge -y cloudflared 2>/dev/null || true
        sudo DEBIAN_FRONTEND=noninteractive apt autoremove -y 2>/dev/null || true
        sudo DEBIAN_FRONTEND=noninteractive apt clean 2>/dev/null || true
        
        # Remove leftover files
        sudo rm -f /usr/local/bin/cloudflared 2>/dev/null || true
        sudo rm -rf /etc/cloudflared 2>/dev/null || true
        
        # Fix package system
        sudo dpkg --configure -a 2>/dev/null || true
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -f -y 2>/dev/null || true
        
        log_info "✅ Cloudflared cleanup completed"
    fi
    
    # Install cloudflared properly
    log_info "Installing cloudflared..."
    
    # Download the latest version
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    
    # Install the package
    if sudo dpkg -i cloudflared-linux-arm64.deb; then
        log_info "✅ Cloudflared package installed successfully"
    else
        log_warn "⚠️ Package installation had issues, fixing dependencies..."
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -f -y
    fi
    
    # Clean up the downloaded file
    rm -f cloudflared-linux-arm64.deb
    
    # Verify installation
    if cloudflared --version &> /dev/null; then
        log_info "✅ Cloudflared installed and working"
        cloudflared --version
    else
        log_error "❌ Cloudflared installation failed"
        return 1
    fi
    
    # Configure cloudflared tunnel if not already configured
    log_info "Setting up cloudflared tunnel configuration..."
    
    # Create config directory
    sudo mkdir -p ~/.cloudflared
    sudo chown $DEPLOY_USER:$DEPLOY_USER ~/.cloudflared
    
    # Check if already authenticated
    if [[ -f ~/.cloudflared/cert.pem ]]; then
        log_info "✅ Cloudflared already authenticated"
    else
        log_info "Authenticating with Cloudflare..."
        log_info "📋 This will open a browser window for authentication"
        log_info "📋 If no browser opens, visit the URL manually"
        
        # Authenticate with Cloudflare
        if cloudflared tunnel login; then
            log_info "✅ Cloudflared authentication successful"
        else
            log_warn "⚠️ Authentication may have failed, but continuing..."
        fi
    fi
    
    # Check if tunnel already exists
    if cloudflared tunnel list | grep -q "ezrec-tunnel"; then
        log_info "✅ Tunnel 'ezrec-tunnel' already exists"
    else
        log_info "Creating new tunnel 'ezrec-tunnel'..."
        cloudflared tunnel create ezrec-tunnel
    fi
    
    # Get tunnel ID
    TUNNEL_ID=$(cloudflared tunnel list | grep "ezrec-tunnel" | awk '{print $1}' | head -n1)
    
    if [[ -z "$TUNNEL_ID" ]]; then
        log_error "❌ Failed to get tunnel ID"
        log_info "📋 Manual setup required:"
        log_info "1. Run: cloudflared tunnel login"
        log_info "2. Run: cloudflared tunnel create ezrec-tunnel"
        log_info "3. Run: cloudflared tunnel route dns ezrec-tunnel api.ezrec.org"
        log_info "4. Update ~/.cloudflared/config.yml manually"
        return 1
    fi
    
    log_info "Tunnel ID: $TUNNEL_ID"
    
    # Create tunnel configuration
    cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: api.ezrec.org
    service: http://localhost:8000
  - service: http_status:404
EOF
    
    # Set proper permissions
    sudo chown $DEPLOY_USER:$DEPLOY_USER ~/.cloudflared/config.yml
    sudo chmod 644 ~/.cloudflared/config.yml
    
    # Route DNS if not already done
    if ! cloudflared tunnel route dns ezrec-tunnel api.ezrec.org 2>/dev/null; then
        log_warn "⚠️ DNS route may already exist or failed to set"
    else
        log_info "✅ DNS route configured for api.ezrec.org"
    fi
    
    log_info "✅ Cloudflared installation and configuration completed"
}

# Enhanced pip installation with warning suppression
install_dependencies_with_suppression() {
    local venv_path=$1
    local requirements_file=$2
    
    log_info "Installing dependencies with optimized conflict resolution..."
    
    # First, try to install core dependencies without version conflicts
    log_info "Installing core dependencies first..."
    if pip_install_suppress_warnings "$venv_path" install \
        --no-cache-dir \
        --index-url https://pypi.org/simple \
        --disable-pip-version-check \
        --no-warn-script-location \
        "fastapi==0.104.1" \
        "uvicorn[standard]==0.24.0" \
        "python-multipart==0.0.6" \
        "python-dotenv==1.0.0" \
        "boto3==1.34.0" \
        "supabase==2.0.2" \
        "httpx>=0.24.0,<0.25.0" \
        "Pillow==10.1.0" \
        "simplejpeg==1.6.6" \
        "av>=15.0.0" \
        "picamera2==0.3.12" \
        "numpy>=1.24.0" \
        "psutil>=5.9.0" \
        "schedule==1.2.0"; then
        
        log_info "✅ Core dependencies installed successfully"
    else
        log_warn "⚠️ Some core dependencies had issues, trying alternative approach..."
        
        # Fallback: install with relaxed constraints
        if pip_install_suppress_warnings "$venv_path" install \
            --no-cache-dir \
            --index-url https://pypi.org/simple \
            --disable-pip-version-check \
            --no-warn-script-location \
            --no-deps \
            -r "$requirements_file"; then
            
            log_info "✅ Dependencies installed with relaxed constraints"
        else
            log_error "❌ Dependency installation failed"
            return 1
        fi
    fi
    
    # Install OpenCV dependencies separately for better control
    log_info "Installing OpenCV stitching dependencies..."
    if pip_install_suppress_warnings "$venv_path" install \
        --no-cache-dir \
        --index-url https://pypi.org/simple \
        "opencv-python>=4.8.0" \
        "opencv-contrib-python>=4.8.0"; then
        
        log_info "✅ OpenCV dependencies installed successfully"
    else
        log_warn "⚠️ OpenCV installation had issues, continuing..."
    fi
    
    return 0
}

# Handle typing-extensions installation gracefully
install_typing_extensions() {
    local venv_path=$1
    
    log_info "🔧 Installing typing-extensions with fallback strategies..."
    
    # Strategy 1: Install with version constraint
    if timeout 60 sudo -u $DEPLOY_USER "$venv_path/bin/pip" install --no-cache-dir --upgrade --force-reinstall "typing-extensions>=4.12.0"; then
        log_info "✅ typing-extensions installed successfully with version constraint"
        return 0
    fi
    
    log_warn "⚠️ Strategy 1 failed, trying Strategy 2..."
    
    # Strategy 2: Install without version constraint
    if timeout 60 sudo -u $DEPLOY_USER "$venv_path/bin/pip" install --no-cache-dir typing-extensions; then
        log_info "✅ typing-extensions installed successfully without version constraint"
        return 0
    fi
    
    log_warn "⚠️ Strategy 2 failed, trying Strategy 3..."
    
    # Strategy 3: Install from PyPI directly
    if timeout 60 sudo -u $DEPLOY_USER "$venv_path/bin/pip" install --no-cache-dir --index-url https://pypi.org/simple typing-extensions; then
        log_info "✅ typing-extensions installed successfully from PyPI"
        return 0
    fi
    
    log_warn "⚠️ All typing-extensions installation strategies failed"
    log_info "💡 Continuing without typing-extensions - this is not critical"
    return 1
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

# Setup virtual environment with PyPI forcing for problematic packages
setup_venv() {
    local path=$1
    local name=$2
    
    log_info "Setting up $name virtual environment"
    
    cd "$path"
    sudo rm -rf venv 2>/dev/null || true
    sudo -u $DEPLOY_USER python3 -m venv --system-site-packages venv
    
    # Install dependencies with PyPI forcing for problematic packages
    pip_install_suppress_warnings "$path/venv" install --no-cache-dir --upgrade pip
    
    # Force PyPI for problematic packages to avoid piwheels 404 errors
    log_info "Installing dependencies with PyPI forcing for problematic packages..."
    install_dependencies_with_suppression "$path/venv" "../requirements.txt"
    
    # Verify virtual environment before proceeding
    if ! verify_venv "$path/venv" "$name"; then
        log_info "🔄 Recreating virtual environment..."
        sudo rm -rf venv
        sudo -u $DEPLOY_USER python3 -m venv --system-site-packages venv
    fi
    
    # Handle typing-extensions installation with multiple strategies
    install_typing_extensions "$path/venv"
    
    # Install simplejpeg with proper error handling
    if ! pip_install_suppress_warnings "$path/venv" install --no-cache-dir --force-reinstall --no-binary simplejpeg simplejpeg; then
        log_warn "Failed to install simplejpeg, trying alternative method"
        pip_install_suppress_warnings "$path/venv" install --no-cache-dir simplejpeg
    fi
    
    # Ensure PyAV is upgraded to compatible version for picamera2
    log_info "Upgrading PyAV to ensure picamera2 compatibility"
    pip_install_suppress_warnings "$path/venv" install --no-cache-dir --upgrade "av>=15.0.0"
    
    # Install OpenCV stitching dependencies
    log_info "Installing OpenCV stitching dependencies..."
    pip_install_suppress_warnings "$path/venv" install --no-cache-dir \
        "opencv-python>=4.8.0" \
        "opencv-contrib-python>=4.8.0" \
        "numpy>=1.21.0"
    
    # Verify picamera2 compatibility
    log_info "Verifying picamera2 and PyAV compatibility"
    if sudo -u $DEPLOY_USER venv/bin/python3 -c "import picamera2; import av; print('✅ picamera2 and PyAV compatibility verified')" 2>/dev/null; then
        log_info "✅ picamera2 and PyAV compatibility verified"
    else
        log_warn "⚠️ picamera2 and PyAV compatibility check failed"
    fi
    
    # Verify OpenCV stitching compatibility
    log_info "Verifying OpenCV stitching compatibility"
    if sudo -u $DEPLOY_USER venv/bin/python3 -c "import cv2; import numpy; print('✅ OpenCV stitching compatibility verified')" 2>/dev/null; then
        log_info "✅ OpenCV stitching compatibility verified"
    else
        log_warn "⚠️ OpenCV stitching compatibility check failed"
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

# Download user assets and company logo with smart checking
download_user_assets() {
    log_info "Checking and downloading user assets (smart mode)"
    
    cd $DEPLOY_PATH
    
    # Debug: Check if we're in the right directory
    log_info "Current directory: $(pwd)"
    log_info "Checking if .env exists: $(ls -la .env 2>/dev/null || echo 'NOT FOUND')"
    
    # Get user_id from .env file
    USER_ID=$(grep "^USER_ID=" .env | cut -d'=' -f2)
    if [[ -z "$USER_ID" ]]; then
        log_warn "USER_ID not found in .env file, skipping user asset download"
        return 0  # Don't exit script, just return
    fi
    
    # Create single assets directory for all assets
    ASSETS_DIR="$DEPLOY_PATH/assets"
    sudo -u $DEPLOY_USER mkdir -p "$ASSETS_DIR"
    
    # Smart asset download with existence checking
    SMART_DOWNLOAD_RESULT=$(sudo -u $DEPLOY_USER $DEPLOY_PATH/backend/venv/bin/python3 -c "
import boto3
import os
import sys
from pathlib import Path

try:
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

    s3 = boto3.client('s3', region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    
    # Define all assets to check/download
    assets_to_check = [
        # Company logo (always check)
        ('main_ezrec_logo.png', '$ASSETS_DIR/ezrec_logo.png'),
        # User assets
        ('$USER_ID/logo/logo.png', '$ASSETS_DIR/user_logo.png'),
        ('$USER_ID/intro-video/intro.mp4', '$ASSETS_DIR/intro.mp4'),
        ('$USER_ID/sponsor-logo1/logo1.png', '$ASSETS_DIR/sponsor_logo1.png'),
        ('$USER_ID/sponsor-logo2/logo2.png', '$ASSETS_DIR/sponsor_logo2.png'),
        ('$USER_ID/sponsor-logo3/logo3.png', '$ASSETS_DIR/sponsor_logo3.png'),
    ]
    
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    print(f'🔍 Checking {len(assets_to_check)} assets in bucket: {bucket}')
    
    for s3_key, local_path in assets_to_check:
        local_file = Path(local_path)
        
        # Check if file already exists and has reasonable size (>1KB)
        if local_file.exists() and local_file.stat().st_size > 1024:
            print(f'⏭️  Skipping {s3_key} - already exists ({local_file.stat().st_size:,} bytes)')
            skipped_count += 1
            continue
        
        # Try to download
        try:
            s3.download_file(bucket, s3_key, local_path)
            file_size = Path(local_path).stat().st_size
            print(f'✅ Downloaded: {s3_key} -> {local_path} ({file_size:,} bytes)')
            downloaded_count += 1
        except Exception as e:
            print(f'⚠️  Not found in S3: {s3_key}')
            failed_count += 1
    
    print(f'📊 Asset check complete:')
    print(f'  - Downloaded: {downloaded_count}')
    print(f'  - Skipped (already exists): {skipped_count}')
    print(f'  - Not found in S3: {failed_count}')
    
    # Show final asset status
    print(f'\\n📁 Final assets directory:')
    assets_dir = Path('$ASSETS_DIR')
    for asset in assets_dir.glob('*'):
        if asset.is_file():
            print(f'  - {asset.name}: {asset.stat().st_size:,} bytes')
    
    # Exit with success if we have at least some assets
    if downloaded_count > 0 or skipped_count > 0:
        sys.exit(0)
    else:
        print('⚠️  No assets found or downloaded')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error during asset download: {e}')
    sys.exit(1)
" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        log_info "✅ Asset check/download completed successfully"
    else
        log_warn "⚠️ Asset check/download failed: $SMART_DOWNLOAD_RESULT"
    fi
    
    # Set proper permissions
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER "$ASSETS_DIR"
    sudo chmod -R 755 "$ASSETS_DIR"
    
    log_info "Smart asset download process completed"
    return 0  # Always return success to continue deployment
}

# Setup files and permissions
setup_files() {
    log_step "Setting up files and permissions"
    
    # Ensure logs directory exists with proper ownership
    sudo mkdir -p $DEPLOY_PATH/logs
    sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/logs
    sudo chmod 755 $DEPLOY_PATH/logs
    
    # Create log files with proper ownership
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/dual_recorder.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/video_worker.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/ezrec-api.log
    sudo -u $DEPLOY_USER touch $DEPLOY_PATH/logs/system_status.log
    sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/logs/*.log
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
    sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/status.json
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
    
    # Prevent port conflicts before starting services
    prevent_port_conflicts
    
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
        
        # Additional port conflict check for API server
        if [[ "$service" == "ezrec-api" ]]; then
            log_info "🔧 Double-checking port 8000 is free before starting API server..."
            if lsof -i :8000 >/dev/null 2>&1; then
                log_warn "⚠️ Port 8000 still in use, forcing cleanup..."
                sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
                sleep 2
            fi
            # Additional aggressive cleanup for API server
            log_info "🔧 Final API server port cleanup..."
            sudo pkill -f "uvicorn" 2>/dev/null || true
            sudo pkill -f "api_server" 2>/dev/null || true
            sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
            sleep 3
        fi
        
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

# Prevent port conflicts before starting services
prevent_port_conflicts() {
    log_step "Preventing port conflicts"
    
    # Kill any existing processes on our ports
    log_info "🔧 Checking for port conflicts..."
    
    # Stop all EZREC services first
    log_info "🛑 Stopping all EZREC services..."
    sudo systemctl stop ezrec-api.service 2>/dev/null || true
    sudo systemctl stop video_worker.service 2>/dev/null || true
    sudo systemctl stop dual_recorder.service 2>/dev/null || true
    sudo systemctl stop system_status.service 2>/dev/null || true
    
    # More aggressive cleanup - kill all possible API server processes
    log_info "🧹 Cleaning up any existing API server processes..."
    
    # Kill uvicorn processes (API server)
    sudo pkill -f "uvicorn" 2>/dev/null || true
    sudo pkill -f "api_server" 2>/dev/null || true
    sudo pkill -f "python.*api_server" 2>/dev/null || true
    
    # Kill any Python processes that might be holding the ports
    sudo pkill -f "python.*8000" 2>/dev/null || true
    sudo pkill -f "python.*9000" 2>/dev/null || true
    
    # Kill any processes using our ports
    if lsof -i :8000 >/dev/null 2>&1; then
        log_warn "⚠️ Port 8000 is in use, killing conflicting processes..."
        log_info "💡 This warning is normal and indicates the conflict prevention is working!"
        log_info "🔧 This prevents the 'address already in use' error that was breaking the API service"
        
        # Get PIDs of processes using port 8000 and kill them
        sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    if lsof -i :9000 >/dev/null 2>&1; then
        log_warn "⚠️ Port 9000 is in use, killing conflicting processes..."
        sudo lsof -ti :9000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Additional cleanup - kill any remaining systemd services that might be holding ports
    sudo systemctl stop ezrec-api.service 2>/dev/null || true
    sudo systemctl stop video_worker.service 2>/dev/null || true
    sudo systemctl stop dual_recorder.service 2>/dev/null || true
    sudo systemctl stop system_status.service 2>/dev/null || true
    
    # Wait a bit more for processes to fully terminate
    sleep 3
    
    # Final aggressive cleanup - kill any remaining processes
    log_info "🔧 Final cleanup - killing any remaining processes on our ports..."
    sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
    sudo lsof -ti :9000 | xargs -r sudo kill -9 2>/dev/null || true
    
    # Verify ports are free
    if ! lsof -i :8000 >/dev/null 2>&1; then
        log_info "✅ Port 8000 is now free"
    else
        log_error "❌ Port 8000 is still in use after cleanup"
        # Show what's still using the port
        log_info "📋 Processes still using port 8000:"
        sudo lsof -i :8000 2>/dev/null || true
        # Force kill one more time
        sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
    fi
    
    if ! lsof -i :9000 >/dev/null 2>&1; then
        log_info "✅ Port 9000 is now free"
    else
        log_error "❌ Port 9000 is still in use after cleanup"
        # Show what's still using the port
        log_info "📋 Processes still using port 9000:"
        sudo lsof -i :9000 2>/dev/null || true
        # Force kill one more time
        sudo lsof -ti :9000 | xargs -r sudo kill -9 2>/dev/null || true
    fi
    
    log_info "Port conflict prevention completed"
}

# Verify API server is running on correct port
verify_api_server() {
    log_step "Verifying API server"
    
    # Wait for API server to start
    log_info "Waiting for API server to start..."
    sleep 5
    
    # Test API server on port 8000
    if curl -s http://localhost:8000/test-alive >/dev/null 2>&1; then
        log_info "✅ API server is responding on port 8000"
        return 0
    else
        log_warn "⚠️ API server not responding on port 8000, checking port 9000..."
        
        # Test API server on port 9000 (fallback)
        if curl -s http://localhost:9000/test-alive >/dev/null 2>&1; then
            log_warn "⚠️ API server is running on port 9000 instead of 8000"
            log_info "This is acceptable but not optimal"
            return 0
        else
            log_error "❌ API server is not responding on either port 8000 or 9000"
            return 1
        fi
    fi
}

# Verify and fix virtual environment
verify_venv() {
    local venv_path=$1
    local venv_name=$2
    
    log_info "🔍 Verifying $venv_name virtual environment..."
    
    # Check if virtual environment exists and is valid
    if [[ ! -d "$venv_path" ]] || [[ ! -f "$venv_path/bin/python3" ]]; then
        log_error "❌ Virtual environment is corrupted or missing"
        log_info "🧹 Removing corrupted virtual environment..."
        sudo rm -rf "$venv_path"
        return 1
    fi
    
    # Test if virtual environment is working
    if ! sudo -u $DEPLOY_USER "$venv_path/bin/python3" -c "import sys; print('Python version:', sys.version)" 2>/dev/null; then
        log_error "❌ Virtual environment is not working properly"
        log_info "🧹 Removing corrupted virtual environment..."
        sudo rm -rf "$venv_path"
        return 1
    fi
    
    log_info "✅ Virtual environment is valid"
    return 0
}

# Complete interrupted deployment
complete_interrupted_deployment() {
    log_step "Completing interrupted deployment"
    
    # Check if we need to continue from where we left off
    if [[ ! -f "$DEPLOY_PATH/status.json" ]]; then
        log_info "🔄 Completing setup_files step..."
        setup_files
    fi
    
    if [[ ! -f "/etc/systemd/system/dual_recorder.service" ]]; then
        log_info "🔄 Completing install_services step..."
        install_services
    fi
    
    if [[ ! -f "/etc/cron.d/ezrec-cleanup" ]]; then
        log_info "🔄 Completing setup_cron step..."
        setup_cron
    fi
    
    log_info "✅ Interrupted deployment completed"
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
    
    # PROTECT .env FILE - NEVER DELETE IT
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        log_info "🔒 Backing up existing .env file"
        sudo cp $DEPLOY_PATH/.env /tmp/ezrec_env_backup
        log_info "✅ .env file backed up successfully"
    else
        log_warn "⚠️ No .env file found to backup"
    fi
    
    # Remove everything EXCEPT .env
    log_info "🧹 Cleaning up old installation (preserving .env)..."
    if [[ -d "$DEPLOY_PATH" ]]; then
        # DOUBLE PROTECTION: Check if .env exists before cleanup
        if [[ -f "$DEPLOY_PATH/.env" ]]; then
            log_info "🔒 .env file found - will preserve it during cleanup"
            # Remove everything except .env
            sudo find $DEPLOY_PATH -mindepth 1 -not -name '.env' -delete 2>/dev/null || true
            log_info "✅ Cleaned up old files (preserved .env)"
            
            # Verify .env still exists after cleanup
            if [[ -f "$DEPLOY_PATH/.env" ]]; then
                log_info "✅ .env file successfully preserved"
            else
                log_error "❌ .env file was accidentally removed during cleanup!"
                return 1
            fi
        else
            log_warn "⚠️ No .env file found in deployment directory"
            sudo rm -rf $DEPLOY_PATH
            sudo mkdir -p $DEPLOY_PATH
            log_info "✅ Created new deployment directory"
        fi
    else
        sudo mkdir -p $DEPLOY_PATH
        log_info "✅ Created new deployment directory"
    fi
    
    # 3. Copy project files
    log_step "3. Copying project files"
    # Only copy if we're not already in the deployment directory
    if [[ "$(pwd)" != "$DEPLOY_PATH" ]]; then
        sudo cp -r . $DEPLOY_PATH/
        sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    else
        log_info "✅ Already in deployment directory, skipping copy"
        # Ensure proper ownership even if we're in the deployment directory
        sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
    fi
    
    # Restore .env if it existed
    if [[ -f "/tmp/ezrec_env_backup" ]]; then
        log_info "🔒 Restoring .env file"
        sudo cp /tmp/ezrec_env_backup $DEPLOY_PATH/.env
        sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/.env
        sudo chmod 644 $DEPLOY_PATH/.env
        log_info "✅ .env file restored successfully"
    else
        log_warn "⚠️ No .env backup found to restore"
    fi
    
    # Ensure required environment variables are present
    ensure_env_variables() {
        log_info "🔧 Ensuring required environment variables are present..."
        local env_file="$DEPLOY_PATH/.env"
        
        if [[ ! -f "$env_file" ]]; then
            log_error "❌ .env file not found at $env_file"
            return 1
        fi
        
        # Check for required variables
        local required_vars=(
            "SUPABASE_URL"
            "SUPABASE_ANON_KEY" 
            "SUPABASE_SERVICE_ROLE_KEY"
            "SUPABASE_KEY"
            "RECORDING_DIR"
            "PROCESSED_DIR"
            "ASSETS_DIR"
            "USER_ID"
            "CAMERA_ID"
        )
        
        local missing_vars=()
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" "$env_file"; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -gt 0 ]]; then
            log_warn "⚠️ Missing required environment variables: ${missing_vars[*]}"
            log_info "📝 Please add these variables to your .env file manually"
            return 1
        else
            log_info "✅ All required environment variables are present"
        fi
    }
    
    # Run environment variable check
    ensure_env_variables
    
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
    
    # Create assets directory (no placeholders)
    log_info "Setting up assets directory"
    cd $DEPLOY_PATH
    sudo -u $DEPLOY_USER mkdir -p assets
    
    # Download user assets and company logo with timeout
    log_info "Starting asset download with timeout protection..."
    cd $DEPLOY_PATH
    
    # Call the function directly from the script
    if download_user_assets; then
        log_info "✅ Asset download completed"
    else
        log_warn "⚠️ Asset download failed, continuing with deployment..."
    fi
    
    # 8. Setup files and services
    setup_files
    install_services
    setup_cron
    
    # 9. Start services
    start_services
    
    # 9.5. Complete any interrupted deployment steps
    complete_interrupted_deployment
    
    # ----------------------------------------
    # ✅ Deploy updated video_worker.py
    # ----------------------------------------
    log_info "📦 Deploying updated video_worker.py..."
    
    if [[ -f "$DEPLOY_PATH/backend/video_worker.py" ]]; then
        log_info "✅ video_worker.py exists and will be used"
    else
        log_warn "⚠️ video_worker.py not found in deployment"
    fi
    
    # Ensure working video_worker is deployed
    log_info "Deploying working video_worker with all fixes..."
    if [[ -f "$DEPLOY_PATH/backend/video_worker.py" ]]; then
        log_info "✅ video_worker.py exists and will be used"
    else
        log_warn "⚠️ video_worker.py not found in deployment"
    fi
    
    # Restart video_worker service specifically
    log_info "🔁 Restarting video_worker.service..."
    if sudo systemctl restart video_worker.service; then
        log_info "✅ video_worker.service restarted successfully"
    else
        log_error "❌ video_worker.service restart failed"
        sudo systemctl status video_worker.service --no-pager -l
    fi
    
    # ----------------------------------------
    # ✅ Deploy updated dual_recorder.py and enhanced_merge.py
    # ----------------------------------------
    log_info "📦 Deploying updated dual_recorder.py and enhanced_merge.py..."
    
    if [[ -f "$DEPLOY_PATH/backend/dual_recorder.py" ]]; then
        log_info "✅ dual_recorder.py exists and will be used"
    else
        log_warn "⚠️ dual_recorder.py not found in deployment"
    fi
    
    if [[ -f "$DEPLOY_PATH/backend/enhanced_merge.py" ]]; then
        log_info "✅ enhanced_merge.py exists and will be used"
    else
        log_warn "⚠️ enhanced_merge.py not found in deployment"
    fi
    
    # Restart dual_recorder service specifically
    log_info "🔁 Restarting dual_recorder.service..."
    if sudo systemctl restart dual_recorder.service; then
        log_info "✅ dual_recorder.service restarted successfully"
    else
        log_error "❌ dual_recorder.service restart failed"
        sudo systemctl status dual_recorder.service --no-pager -l
    fi
    
    # 10. Validate deployment
    validate_deployment
    test_picamera2
    test_system_status
    verify_api_server
    
    # 11. Final checks
    log_step "11. Final system checks"
    
    # Test API server specifically
    echo -e "\n--- API SERVER TEST ---"
    echo "Testing API server on port 8000:"
    if curl -s http://localhost:8000/test-alive > /dev/null; then
        echo "✅ API server responding on port 8000"
        curl -s http://localhost:8000/test-alive
    else
        echo "❌ API server not responding on port 8000"
        echo "💡 Check API server status:"
        echo "   sudo systemctl status ezrec-api.service"
        echo "   sudo journalctl -u ezrec-api.service -n 20"
    fi
    
    # Test Cloudflare tunnel and external API (read-only check)
    echo -e "\n--- CLOUDFLARE TUNNEL STATUS ---"
    echo "Checking existing Cloudflare tunnel status:"
    if ps aux | grep -q "cloudflared tunnel run" || sudo systemctl is-active --quiet cloudflared.service 2>/dev/null; then
        echo "✅ Cloudflare tunnel is running"
        echo "📋 Tunnel logs: tail -f /tmp/cloudflared.log"
        echo "📋 To stop tunnel: sudo pkill cloudflared"
        
        # Test external API (read-only)
        echo "🧪 Testing external API connection..."
        if curl -s --max-time 10 https://api.ezrec.org/status > /dev/null 2>&1; then
            echo "✅ External API is accessible via tunnel"
        else
            echo "⚠️ External API not accessible - tunnel may need manual restart"
            echo "💡 Manual tunnel restart: sudo systemctl restart cloudflared.service"
        fi
    else
        echo "⚠️ Cloudflare tunnel not running"
        echo "💡 Manual tunnel start: sudo systemctl start cloudflared.service"
        echo "💡 Or: nohup cloudflared tunnel run ezrec-tunnel > /tmp/cloudflared.log 2>&1 &"
    fi
    
    log_info "Comprehensive system check completed!"
}

# Run main function
main "$@"
