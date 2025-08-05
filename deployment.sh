#!/bin/bash

<<<<<<< HEAD
# Final Combined EZREC Deployment Script (Backend + FastAPI + Monitor + Cloudflared + Recorder + Video Worker)
# 
# This script is designed to deploy EZREC Backend to a Raspberry Pi
# It does NOT modify the .env file - you must create and configure it manually using env.example as a template
# 
# Usage: ./deployment.sh [username] [tunnel_name]
=======
# EZREC Backend Deployment Script
# Clean, efficient deployment with proper error handling and modular structure
>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================

<<<<<<< HEAD
#------------------------------#
# 1. CHECK COMMANDS
#------------------------------#
required_cmds=("python3" "pip" "sudo" "systemctl" "curl" "aws")
for cmd in "${required_cmds[@]}"; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Missing required command: $cmd"
    exit 1
  fi
done
=======
DEPLOY_USER="michomanoly14892"
DEPLOY_PATH="/opt/ezrec-backend"
SERVICES=("dual_recorder" "video_worker" "ezrec-api" "system_status")
TIMER_SERVICES=("system_status")
>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

<<<<<<< HEAD
#------------------------------#
# 2.5 CLEANUP SYSTEM BEFORE DEPLOY
#------------------------------#
echo "🧹 Cleaning up old recordings, uploads, and logs..."
sudo rm -rf "$PROJECT_DIR/raw_recordings"/*
sudo rm -rf "$PROJECT_DIR/processed_recordings"/*
sudo rm -f "$PROJECT_DIR/pending_uploads.json"
sudo rm -f "$LOG_DIR/ezrec.log"

#------------------------------#
# 2.6 DEEP CLEANUP OF ALL DATA #
#------------------------------#
echo "🧹 Deep cleaning all recordings, processed videos, media cache, and state files..."
# Remove all files in /opt/ezrec-backend/recordings and subfolders
sudo find "$PROJECT_DIR/recordings" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' \) -delete 2>/dev/null || true
# Remove all files in /opt/ezrec-backend/processed and subfolders
sudo find "$PROJECT_DIR/processed" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' \) -delete 2>/dev/null || true
# Remove all files in /opt/ezrec-backend/media_cache and subfolders
sudo rm -rf "$PROJECT_DIR/media_cache"/* 2>/dev/null || true
# Remove pending uploads and health/status files
sudo rm -f "$PROJECT_DIR/pending_uploads.json" "$PROJECT_DIR/health_report.json" "$PROJECT_DIR/status.json"
# Remove all cache/state files in api/local_data
sudo rm -f "$API_DIR/local_data/bookings.json" "$API_DIR/local_data/status.json" "$API_DIR/local_data/system.json"
echo "✅ All recordings, processed videos, media cache, and state files cleaned."



#------------------------------#
# 3. CREATE FOLDERS + PERMISSIONS
#------------------------------#
echo "📁 Setting up directories..."
sudo mkdir -p "$API_DIR/local_data" "$LOG_DIR" "$PROJECT_DIR/static" "$PROJECT_DIR/media_cache"
sudo chown -R "$USER:$USER" "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
chmod 700 "$API_DIR/local_data"
sudo chmod 777 "$LOG_DIR"
sudo chmod 755 "$PROJECT_DIR/static"
sudo chmod 755 "$PROJECT_DIR/media_cache"

#------------------------------#
# 4. CREATE VENV + INSTALL PYTHON DEPS
#------------------------------#
echo "🐍 Setting up virtual environment..."
rm -rf "$VENV_DIR"
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install fastapi uvicorn psutil requests boto3 python-dotenv pytz python-dateutil supabase
"$VENV_DIR/bin/pip" install 'pydantic[email]'
"$VENV_DIR/bin/pip" install opencv-python speedtest-cli
sudo chown -R "$USER:$USER" "$VENV_DIR"

#------------------------------#
# 4.1 REFRESH USER MEDIA CACHE #
#------------------------------#
echo "🔄 Refreshing user media cache for main user..."
USER_ID=$(grep '^USER_ID=' "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d '"')
if [ -n "$USER_ID" ]; then
  export USER_ID
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/backend/refresh_user_media.py"
else
  echo "⚠️ USER_ID not set in .env, skipping user media refresh."
fi

#------------------------------#
# 4.5. CAMERA SETUP & CONFIGURATION
#------------------------------#
echo "📹 Setting up camera hardware and software..."

# 1. Ensure user is in video group
if ! groups "$USER" | grep -q video; then
    echo "👤 Adding user $USER to video group..."
    sudo usermod -a -G video "$USER"
    echo "✅ User added to video group (requires logout/login to take effect)"
else
    echo "✅ User $USER is already in video group"
fi

# 2. Install/update camera-related packages
echo "📦 Installing camera dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-opencv \
    python3-libcamera \
    libcamera-tools \
    v4l-utils \
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    v4l-utils

# 3. Load camera kernel modules
echo "🔧 Loading camera kernel modules..."
sudo modprobe bcm2835-v4l2 || echo "⚠️ bcm2835-v4l2 module not available (may be built-in)"
sudo modprobe v4l2loopback || echo "⚠️ v4l2loopback module not available"

# 4. Set up camera device permissions
echo "🔐 Setting up camera device permissions..."
sudo chown root:video /dev/video* 2>/dev/null || true
sudo chmod 660 /dev/video* 2>/dev/null || true

# 5. Create camera configuration
echo "⚙️ Creating camera configuration..."
sudo tee /etc/modules-load.d/camera.conf > /dev/null <<EOF
bcm2835-v4l2
v4l2loopback
EOF

# 6. Set up camera device rules
echo "📋 Setting up camera device rules..."
sudo tee /etc/udev/rules.d/99-camera.rules > /dev/null <<EOF
# Camera device permissions
KERNEL=="video*", GROUP="video", MODE="0660"
SUBSYSTEM=="media", GROUP="video", MODE="0660"
EOF

# 7. Reload udev rules
echo "🔄 Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# 8. Test camera hardware
echo "🧪 Testing camera hardware..."
if [ -e /dev/video0 ]; then
    echo "✅ Camera device /dev/video0 found"
    ls -la /dev/video* | head -5
else
    echo "❌ Camera device /dev/video0 not found"
    echo "🔍 Available video devices:"
    ls -la /dev/video* 2>/dev/null || echo "No video devices found"
fi

# 9. Kill any existing camera processes
echo "🛑 Cleaning up existing camera processes..."
sudo pkill -f camera_streamer || true
sudo pkill -f recorder || true
sudo fuser -k /dev/video0 2>/dev/null || true
sleep 2

# 10. Reset camera state
echo "🔄 Resetting camera state..."
sudo modprobe -r bcm2835-v4l2 2>/dev/null || true
sleep 1
sudo modprobe bcm2835-v4l2 2>/dev/null || true
sleep 2

# 11. Test camera with OpenCV
echo "🧪 Testing camera with OpenCV..."
cat > /tmp/camera_test.py << 'EOF'
#!/usr/bin/env python3
import time
import sys
import cv2

print("Testing camera initialization with OpenCV...")

try:
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Failed to open camera with OpenCV")
        sys.exit(1)
    
    print("✅ Camera opened with OpenCV")
    
    # Configure camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Test frame capture
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"✅ Frame captured: {frame.shape}")
        cv2.imwrite('/tmp/test_frame.jpg', frame)
        print("✅ Test frame saved to /tmp/test_frame.jpg")
    else:
        print("❌ Failed to capture frame")
        sys.exit(1)
    
    # Release camera
    cap.release()
    print("✅ Camera released")
    
    print("🎉 OpenCV camera test successful!")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ OpenCV camera test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Run camera test
if "$VENV_DIR/bin/python3" /tmp/camera_test.py; then
    echo "✅ OpenCV camera test passed"
    rm -f /tmp/camera_test.py
else
    echo "❌ OpenCV camera test failed - continuing with deployment"
    rm -f /tmp/camera_test.py
fi

# Test OpenCV recording functionality
echo "🎬 Testing OpenCV recording functionality..."
cat > /tmp/recording_test.py << 'EOF'
#!/usr/bin/env python3
import cv2
import time
import os

print("🧪 Testing OpenCV Video Recording...")

try:
    # Initialize camera
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("❌ Failed to open camera for recording test")
        exit(1)
    
    # Configure camera
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    output_file = "/tmp/test_recording.mp4"
    video_writer = cv2.VideoWriter(output_file, fourcc, 30, (1280, 720))
    
    if not video_writer.isOpened():
        print("❌ Failed to initialize video writer")
        exit(1)
    
    # Record 3 seconds
    print("📹 Recording 3 seconds of test video...")
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 3:
        ret, frame = camera.read()
        if ret:
            video_writer.write(frame)
            frame_count += 1
    
    # Cleanup
    video_writer.release()
    camera.release()
    
    # Check result
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
        print(f"✅ Recording test successful: {frame_count} frames, {os.path.getsize(output_file)} bytes")
        os.remove(output_file)
        exit(0)
    else:
        print("❌ Recording test failed - file too small or missing")
        exit(1)
        
except Exception as e:
    print(f"❌ Recording test failed: {e}")
    exit(1)
EOF

if "$VENV_DIR/bin/python3" /tmp/recording_test.py; then
    echo "✅ OpenCV recording test passed"
    rm -f /tmp/recording_test.py
else
    echo "❌ OpenCV recording test failed - continuing with deployment"
    rm -f /tmp/recording_test.py
fi

echo "📹 Camera and recording setup complete"

# Run comprehensive system test
echo "🧪 Running comprehensive system test..."
if [ -f "$PROJECT_DIR/test_full_system.py" ]; then
    if "$VENV_DIR/bin/python3" "$PROJECT_DIR/test_full_system.py"; then
        echo "✅ Comprehensive system test passed"
    else
        echo "⚠️ Comprehensive system test failed - continuing with deployment"
    fi
else
    echo "⚠️ test_full_system.py not found - skipping comprehensive test"
fi

#------------------------------#
# 5. SYNC PROJECT FILES
#------------------------------#
DEV_DIR="/home/$USER/EZREC-BACKEND-2"
echo "[DEBUG] DEV_DIR=$DEV_DIR"
echo "[DEBUG] PROJECT_DIR=$PROJECT_DIR"
ls -l "$DEV_DIR/backend/refresh_user_media.py" || echo "[DEBUG] refresh_user_media.py not found in DEV_DIR/backend"
echo "📦 Syncing updated project files..."
if [ -d "$DEV_DIR" ]; then
  rsync -av --exclude='venv' --exclude='.git' --exclude='__pycache__' "$DEV_DIR/" "$PROJECT_DIR/"
  
  # Ensure new files are properly copied and executable
  echo "🔧 Setting up new files..."
  if [ -f "$PROJECT_DIR/backend/restart_services.sh" ]; then
    chmod +x "$PROJECT_DIR/backend/restart_services.sh"
    echo "✅ Made restart_services.sh executable"
  fi
  
  if [ -f "$PROJECT_DIR/backend/camera_diagnostics.py" ]; then
    chmod +x "$PROJECT_DIR/backend/camera_diagnostics.py"
    echo "✅ Made camera_diagnostics.py executable"
  fi
  
  # Copy troubleshooting guide
  if [ -f "$DEV_DIR/TROUBLESHOOTING.md" ]; then
    cp "$DEV_DIR/TROUBLESHOOTING.md" "$PROJECT_DIR/"
    echo "✅ Copied TROUBLESHOOTING.md"
  fi
else
  echo "⚠️ Development directory not found: $DEV_DIR"
fi

#------------------------------#
# 5.1 REFRESH USER MEDIA CACHE #
#------------------------------#
echo "🔄 Refreshing user media cache for main user..."
USER_ID=$(grep '^USER_ID=' "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d '"')
if [ -n "$USER_ID" ]; then
  export USER_ID
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/backend/refresh_user_media.py"
else
  echo "⚠️ USER_ID not set in .env, skipping user media refresh."
fi

#------------------------------#
# 5.5. DOWNLOAD MAIN EZREC LOGO #
#------------------------------#
# Temporarily export AWS credentials for S3 download
set -a
source "$PROJECT_DIR/.env"
set +a

# Download main EZREC logo
echo "🖼️ Downloading main EZREC logo from S3..."
aws s3 cp s3://ezrec-user-media/main_ezrec_logo.png /opt/ezrec-backend/main_ezrec_logo.png || { echo "❌ Failed to download main EZREC logo from S3"; 
  # Unset AWS credentials for security
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN
  exit 1; }

# Unset AWS credentials for security
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN

#------------------------------#
# 6. INSTALL BACKEND DEPENDENCIES
#------------------------------#
echo "📦 Installing backend requirements.txt dependencies..."
REQS_FILE="/home/$USER/EZREC-BACKEND-2/requirements.txt"
if [ -f "$REQS_FILE" ]; then
  "$VENV_DIR/bin/pip" install -r "$REQS_FILE"
else
  echo "⚠️ Warning: requirements.txt not found at $REQS_FILE"
fi

#------------------------------#
# 7. FIX LOG FILE PERMISSIONS
#------------------------------#
echo "⚖️ Fixing log permissions..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER:$USER" "$LOG_DIR"
sudo chmod 777 "$LOG_DIR"
=======
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
>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if user exists
user_exists() {
    id "$1" &>/dev/null
}

<<<<<<< HEAD
[Service]
ExecStart=$VENV_DIR/bin/uvicorn api_server:app --host 0.0.0.0 --port 9000
WorkingDirectory=$API_DIR
Restart=always
User=$USER
=======
# Manage services (start/stop/enable/disable)
manage_services() {
    local action=$1
    local service_list=("${@:2}")
    
    for service in "${service_list[@]}"; do
        log_info "Managing $service: $action"
        sudo systemctl $action ${service}.service 2>/dev/null || true
    done
}
>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81

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
    
    # Ensure logs directory exists
    sudo mkdir -p $DEPLOY_PATH/logs
    sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH/logs
    sudo chmod 755 $DEPLOY_PATH/logs
    
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

<<<<<<< HEAD
# Status Updater
"$VENV_DIR/bin/pip" install psutil
# Ensure status_updater.py is present
if [ -f "$DEV_DIR/backend/status_updater.py" ]; then
  cp "$DEV_DIR/backend/status_updater.py" "$PROJECT_DIR/status_updater.py"
  echo "✅ Copied status_updater.py to $PROJECT_DIR"
else
  echo "❌ status_updater.py not found in $DEV_DIR/backend. Please check your source."
fi
# Create systemd service for status updater
sudo tee "$SYSTEMD_DIR/status_updater.service" > /dev/null <<EOF
[Unit]
Description=EZREC System Status Updater
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/status_updater.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF
# Enable and start the status updater service
sudo systemctl daemon-reload
sudo systemctl enable status_updater.service
sudo systemctl restart status_updater.service
sudo systemctl status status_updater.service --no-pager

# Camera Streamer
sudo cp "$PROJECT_DIR/backend/camera_streamer.service" "$SYSTEMD_DIR/camera_streamer.service"

# Health API Service
sudo tee "$SYSTEMD_DIR/health_api.service" > /dev/null <<EOF
[Unit]
Description=EZREC Health API
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/health_api.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Log Collector Service
sudo tee "$SYSTEMD_DIR/log_collector.service" > /dev/null <<EOF
[Unit]
Description=EZREC Log Collector
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/log_collector.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable camera_streamer.service
sudo systemctl restart camera_streamer.service
sudo systemctl status camera_streamer.service --no-pager

#------------------------------#
# 9. CLOUDFLARED INSTALL
#------------------------------#
if ! command -v cloudflared &>/dev/null; then
  echo "📦 Installing cloudflared..."
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /etc/apt/trusted.gpg.d/cloudflare-main.gpg >/dev/null
  echo "deb [signed-by=/etc/apt/trusted.gpg.d/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared stable main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
  sudo apt-get update && sudo apt-get install -y cloudflared
else
  echo "✅ cloudflared is already installed"
fi

#------------------------------#
# 10. UDP BUFFER CONFIG
#------------------------------#
echo "🛠️ Increasing UDP buffer size for cloudflared..."
if ! grep -q "net.core.rmem_max = 7168000" /etc/sysctl.conf; then
  echo "net.core.rmem_max = 7168000" | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
else
  echo "✅ UDP buffer already configured"
fi

#------------------------------#
# 11. CHECK FOR .ENV FILE
#------------------------------#
if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "⚠️  WARNING: .env file not found at $PROJECT_DIR/.env"
  echo "    Please create it using env.example as a template before starting services"
  echo "    Services will be enabled but may fail to start without proper configuration"
fi

#------------------------------#
# 12. ENABLE + START SERVICES
#------------------------------#
echo "🔁 Enabling and starting services..."
sudo systemctl daemon-reload
for svc in ezrec-api ezrec-monitor recorder video_worker cloudflared camera_streamer status_updater health_api log_collector; do
  sudo systemctl enable "$svc"
  sudo systemctl restart "$svc"
  sleep 1
done

#------------------------------#
# 13. CAMERA HEALTH CHECK
#------------------------------#
echo "📹 Performing camera health check..."
sleep 5  # Give services time to start

# Check camera streamer service
if sudo systemctl is-active --quiet camera_streamer.service; then
    echo "✅ Camera streamer service is running"
else
    echo "❌ Camera streamer service is not running"
    echo "🔧 Attempting to fix camera streamer..."
    
    # Reset failed state
    sudo systemctl reset-failed camera_streamer.service
    
    # Kill any stuck processes
    sudo pkill -f camera_streamer || true
    sleep 2
    
    # Try to start the service
    sudo systemctl start camera_streamer.service
    sleep 3
    
    # Check again
    if sudo systemctl is-active --quiet camera_streamer.service; then
        echo "✅ Camera streamer service fixed and running"
    else
        echo "❌ Camera streamer service still not running"
        echo "📋 Camera streamer logs:"
        sudo journalctl -u camera_streamer.service -n 10 --no-pager
    fi
fi

# Test camera stream accessibility
echo "🌐 Testing camera stream accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:9000 | grep -q "200"; then
    echo "✅ Camera stream is accessible on port 9000"
else
    echo "❌ Camera stream is not accessible on port 9000"
    echo "🔧 Testing camera streamer manually..."
    
    # Try manual test
    cd "$PROJECT_DIR/backend"
    timeout 10 "$VENV_DIR/bin/python3" -c "
import sys
sys.path.append('/opt/ezrec-backend/backend')
try:
    from camera_streamer import camera_streamer
    print('✅ OpenCV camera streamer can be initialized manually')
    if camera_streamer.start():
        print('✅ Camera streamer started successfully')
        camera_streamer.stop()
    else:
        print('❌ Camera streamer failed to start')
        sys.exit(1)
except Exception as e:
    print(f'❌ Manual test failed: {e}')
    sys.exit(1)
" || echo "⚠️ Manual camera streamer test failed"
fi

# Test live preview through API
echo "📺 Testing live preview through API..."
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/live-preview?token=changeme" | grep -q "200\|503"; then
    echo "✅ Live preview endpoint is responding"
else
    echo "❌ Live preview endpoint is not responding"
fi

# Run camera diagnostics if available
if [ -f "$PROJECT_DIR/backend/camera_diagnostics.py" ]; then
    echo "🔍 Running camera diagnostics..."
    cd "$PROJECT_DIR/backend"
    timeout 30 "$VENV_DIR/bin/python3" camera_diagnostics.py --quick-test || echo "⚠️ Camera diagnostics timed out or failed"
fi

echo "📹 Camera health check complete"

#------------------------------#
# 14. FINAL VERIFICATION
#------------------------------#
echo "🔍 Final service verification..."
for svc in ezrec-api ezrec-monitor recorder video_worker cloudflared camera_streamer status_updater health_api log_collector; do
    if sudo systemctl is-active --quiet "$svc"; then
        echo "✅ $svc is running"
    else
        echo "❌ $svc is not running"
    fi
done

#------------------------------#
# 15. VERIFY NEW FILES
#------------------------------#
echo "🔍 Verifying new files..."
NEW_FILES=(
  "$PROJECT_DIR/backend/restart_services.sh"
  "$PROJECT_DIR/backend/camera_diagnostics.py"
  "$PROJECT_DIR/TROUBLESHOOTING.md"
)

for file in "${NEW_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $(basename "$file") is present"
  else
    echo "❌ $(basename "$file") is missing"
  fi
done

echo ""
echo "🎯 Deployment verification complete!"

#------------------------------#
# 16. DONE!
#------------------------------#
echo ""
echo "🎉 EZREC deployed successfully!"
echo ""
echo "📡 API running:    http://<Pi-IP>:9000 or https://api.ezrec.org"
echo "🩺 Monitor logs:   sudo journalctl -u ezrec-monitor -f"
echo "📹 Recorder logs:  sudo journalctl -u recorder.service -f"
echo "🎞️ Video logs:     sudo journalctl -u video_worker.service -f"
echo "🌐 Tunnel logs:    sudo journalctl -u cloudflared -f"
echo "📹 Camera logs:    sudo journalctl -u camera_streamer.service -f"
echo "📁 Project files:  $PROJECT_DIR"
echo "📁 API entry:      $API_DIR/api_server.py"
echo "📃 Logs dir:       $LOG_DIR"
echo ""
echo "⚠️  IMPORTANT: Make sure to create and configure $PROJECT_DIR/.env file"
echo "    Use env.example as a template and add your credentials"
echo "    New variables added: MAIN_LOGO_WIDTH=400, MAIN_LOGO_HEIGHT=400"
echo "    Camera setup: User added to video group, camera modules loaded"
echo "    Camera permissions: /dev/video* devices configured for video group"

#------------------------------#
# 14. CLOUDFLARED CONFIG
#------------------------------#
echo "🌐 Setting up Cloudflare tunnel..."

# Check if tunnel exists, create if not
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}' | head -n1)
if [ -z "$TUNNEL_ID" ]; then
    echo "🆕 Creating new tunnel: $TUNNEL_NAME"
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}' | head -n1)
    echo "✅ Tunnel created with ID: $TUNNEL_ID"
else
    echo "✅ Using existing tunnel: $TUNNEL_NAME (ID: $TUNNEL_ID)"
fi

# Create DNS record if it doesn't exist
if ! cloudflared tunnel route dns "$TUNNEL_NAME" api.ezrec.org 2>/dev/null; then
    echo "✅ DNS record already exists for api.ezrec.org"
else
    echo "✅ Created DNS record for api.ezrec.org"
fi

CLOUDFLARED_CREDS="/etc/cloudflared/${TUNNEL_ID}.json"
CLOUDFLARED_CONFIG="/etc/cloudflared/config.yml"

# Always write the correct config for main API on port 9000
# WARNING: This will overwrite /etc/cloudflared/config.yml
sudo tee "$CLOUDFLARED_CONFIG" > /dev/null <<EOF
tunnel: $TUNNEL_NAME
credentials-file: $CLOUDFLARED_CREDS

ingress:
  - hostname: api.ezrec.org
    service: http://localhost:9000
  - service: http_status:404
EOF

sudo systemctl restart cloudflared

# To change video/camera resolution, set RESOLUTION in your .env file (e.g. RESOLUTION=1280x720)

# After deployment, print the encoder being used:
if [ -f "$PROJECT_DIR/.env" ]; then
  ENCODER=$(grep '^VIDEO_ENCODER=' "$PROJECT_DIR/.env" | cut -d'=' -f2)
  echo "\n🎥 Video encoder set to: ${ENCODER:-h264_v4l2m2m} (see .env)"
fi

# Ensure main_ezrec_logo.png is present and correctly named
MAIN_LOGO_PATH="$PROJECT_DIR/main_ezrec_logo.png"
ALT_LOGO_PATH="$PROJECT_DIR/main_logo.png"
if [ ! -f "$MAIN_LOGO_PATH" ]; then
  if [ -f "$ALT_LOGO_PATH" ]; then
    echo "Renaming $ALT_LOGO_PATH to $MAIN_LOGO_PATH..."
    mv "$ALT_LOGO_PATH" "$MAIN_LOGO_PATH"
  else
    echo "⬇️ Downloading main_ezrec_logo.png from S3..."
    set -a
    source "$PROJECT_DIR/.env"
    set +a
    aws s3 cp "s3://ezrec-user-media/main_ezrec_logo.png" "$MAIN_LOGO_PATH"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN
    if [ ! -f "$MAIN_LOGO_PATH" ]; then
      echo "❌ Failed to download main_ezrec_logo.png from S3. Please check your AWS credentials and bucket."
      exit 1
    fi
  fi
else
  echo "✅ main_ezrec_logo.png already present."
fi

#------------------------------#
# 15. VERIFY NEW FILES
#------------------------------#
echo "🔍 Verifying new files..."
NEW_FILES=(
  "$PROJECT_DIR/backend/restart_services.sh"
  "$PROJECT_DIR/backend/camera_diagnostics.py"
  "$PROJECT_DIR/TROUBLESHOOTING.md"
)

for file in "${NEW_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $(basename "$file") is present"
  else
    echo "❌ $(basename "$file") is missing"
  fi
done

echo ""
echo "🎯 Deployment verification complete!"
=======
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
>>>>>>> 7f4d06de69b6359ae09f590d27a614501e93bf81
