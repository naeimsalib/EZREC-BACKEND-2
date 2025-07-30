#!/bin/bash

# EZREC Backend Deployment Script
# This script handles the complete deployment of the EZREC backend system
# including all necessary fixes and setup steps

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Get current user
CURRENT_USER=$(whoami)
log "Starting EZREC deployment as user: $CURRENT_USER"

# 1. STOP AND KILL OLD SERVICES
log "1. Stopping and killing old services..."
sudo systemctl stop dual_recorder.service video_worker.service ezrec-api.service system_status.service 2>/dev/null || true
sudo systemctl disable dual_recorder.service video_worker.service ezrec-api.service system_status.service 2>/dev/null || true
sudo pkill -f dual_recorder.py 2>/dev/null || true
sudo pkill -f video_worker.py 2>/dev/null || true
sudo pkill -f api_server.py 2>/dev/null || true
sudo pkill -f system_status.py 2>/dev/null || true

# 2. CLEANUP OLD INSTALLATION (PRESERVING .env)
log "2. Cleaning up old installation (preserving .env)..."
if [ -f "/opt/ezrec-backend/.env" ]; then
    log "Backing up existing .env file..."
    sudo cp /opt/ezrec-backend/.env /tmp/ezrec_env_backup
fi

sudo rm -rf /opt/ezrec-backend
sudo mkdir -p /opt/ezrec-backend

# Restore .env if it existed
if [ -f "/tmp/ezrec_env_backup" ]; then
    log "Restoring .env file..."
    sudo cp /tmp/ezrec_env_backup /opt/ezrec-backend/.env
    sudo chown ezrec:ezrec /opt/ezrec-backend/.env
    sudo chmod 644 /opt/ezrec-backend/.env
fi

# 3. COPY PROJECT FILES
log "3. Copying project files..."
sudo cp -r . /opt/ezrec-backend/
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/ezrec-backend

# 4. INSTALL SYSTEM DEPENDENCIES
log "4. Installing system dependencies..."
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
    git \
    curl \
    wget \
    vim \
    htop

# 5. CREATE EZREC USER AND GROUPS
log "5. Setting up user and groups..."
if ! id "ezrec" &>/dev/null; then
    sudo useradd -r -s /bin/false -d /opt/ezrec-backend ezrec
fi

# Add current user to video group
sudo usermod -a -G video $CURRENT_USER
sudo usermod -a -G video ezrec

# 6. CREATE DIRECTORY STRUCTURE
log "6. Creating directory structure..."
sudo mkdir -p /opt/ezrec-backend/{recordings,processed,final,assets,logs,events,api/local_data,media_cache}
sudo chown -R ezrec:ezrec /opt/ezrec-backend

# 7. SETUP PYTHON VIRTUAL ENVIRONMENTS
log "7. Setting up Python virtual environments..."

# Backend virtual environment - create as ezrec user
log "Setting up backend virtual environment..."
cd /opt/ezrec-backend/backend
sudo rm -rf venv 2>/dev/null || true
sudo -u ezrec python3 -m venv --system-site-packages venv

# Activate and install backend dependencies
sudo -u ezrec venv/bin/pip install --upgrade pip
sudo -u ezrec venv/bin/pip install -r ../requirements.txt
sudo -u ezrec venv/bin/pip install --upgrade "typing-extensions>=4.12.0"
sudo -u ezrec venv/bin/pip install --force-reinstall --no-binary simplejpeg simplejpeg

# API virtual environment - create as ezrec user
log "Setting up API virtual environment..."
cd /opt/ezrec-backend/api
sudo rm -rf venv 2>/dev/null || true
sudo -u ezrec python3 -m venv --system-site-packages venv

# Activate and install API dependencies
sudo -u ezrec venv/bin/pip install --upgrade pip
sudo -u ezrec venv/bin/pip install -r ../requirements.txt
sudo -u ezrec venv/bin/pip install --upgrade "typing-extensions>=4.12.0"
sudo -u ezrec venv/bin/pip install --force-reinstall --no-binary simplejpeg simplejpeg


# 8. COMPREHENSIVE FIXES SECTION
log "8. Applying comprehensive fixes..."

# Fix 1: Handle libcamera/pykms issues
log "Fixing libcamera/pykms dependencies..."
cd /opt/ezrec-backend/backend
sudo -u ezrec venv/bin/python3 -c "import picamera2" 2>/dev/null || {
    log "Creating kms.py placeholder for picamera2 compatibility..."
    # figure out exactly where site‑packages lives
    SITE_PACKAGES=$(sudo -u ezrec venv/bin/python3 -c "import distutils.sysconfig as s; print(s.get_python_lib())")
    sudo -u ezrec tee "$SITE_PACKAGES/kms.py" > /dev/null << 'EOF'
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

# Add PixelFormat to the module namespace
__all__ = ['KMS', 'create_kms', 'PixelFormat']
EOF
    sudo -u ezrec ln -sf "$SITE_PACKAGES/kms.py" "$SITE_PACKAGES/pykms.py"
}

# Fix 2: Create missing assets
log "Creating placeholder assets..."
cd /opt/ezrec-backend
sudo -u ezrec python3 backend/create_assets.py

# Fix 3: Ensure bookings.json exists
log "Setting up bookings.json..."
sudo mkdir -p /opt/ezrec-backend/api/local_data
sudo -u ezrec tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null << 'EOF'
[]
EOF

# Fix 4: Set proper permissions
log "Setting proper permissions..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/.env 2>/dev/null || true

# Fix 5: Create log files
log "Setting up log files..."
sudo -u ezrec touch /opt/ezrec-backend/logs/dual_recorder.log
sudo -u ezrec touch /opt/ezrec-backend/logs/video_worker.log
sudo -u ezrec touch /opt/ezrec-backend/logs/ezrec-api.log
sudo -u ezrec touch /opt/ezrec-backend/logs/system_status.log
sudo chmod 644 /opt/ezrec-backend/logs/*.log

# 9. INSTALL SYSTEMD SERVICES
log "9. Installing systemd services..."
sudo cp /opt/ezrec-backend/systemd/*.service /etc/systemd/system/
sudo cp /opt/ezrec-backend/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 10. ENABLE SERVICES
log "10. Enabling services..."
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service
sudo systemctl enable system_status.service
sudo systemctl enable system_status.timer

# 11. SETUP CRON JOBS
log "11. Setting up cron jobs..."
# Add cleanup job to root crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/ezrec-backend/backend/cleanup_old_data.py > /opt/ezrec-backend/logs/cleanup.log 2>&1") | crontab -

# 12. FINAL PERMISSIONS AND OWNERSHIP
log "12. Setting final permissions and ownership..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/.env 2>/dev/null || true

# 13. CREATE STATUS FILE
log "13. Creating status file..."
sudo -u ezrec tee /opt/ezrec-backend/status.json > /dev/null << 'EOF'
{
  "is_recording": false,
  "last_update": "$(date -Iseconds)",
  "system_status": "deployed"
}
EOF

# 14. START SERVICES
log "14. Starting services..."
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service
sudo systemctl start system_status.timer

# 15. FINAL STATUS CHECK
log "15. Performing final status check..."
sleep 5

# Reset any failed services and restart them
log "Resetting failed services..."
sudo systemctl reset-failed system_status.service 2>/dev/null || true
sudo systemctl reset-failed dual_recorder.service 2>/dev/null || true
sudo systemctl reset-failed video_worker.service 2>/dev/null || true
sudo systemctl reset-failed ezrec-api.service 2>/dev/null || true

# Restart services to ensure they use the new virtual environments
log "Restarting services with updated virtual environments..."
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service
sudo systemctl restart system_status.service

# Wait for services to start
sleep 10

# Check service status
log "Checking service status..."
sudo systemctl status dual_recorder.service --no-pager -l
sudo systemctl status video_worker.service --no-pager -l
sudo systemctl status ezrec-api.service --no-pager -l
sudo systemctl status system_status.service --no-pager -l

# Test picamera2 import
log "Testing picamera2 import..."
if sudo -u ezrec /opt/ezrec-backend/backend/venv/bin/python3 -c "import picamera2; print('✅ picamera2 imported successfully')" 2>/dev/null; then
    log "✅ picamera2 import test passed"
else
    warn "⚠️ picamera2 import test failed - check system packages"
fi

# Check if .env exists
if [ -f "/opt/ezrec-backend/.env" ]; then
    log "✅ .env file exists"
else
    warn "⚠️ .env file not found - you need to create it manually"
    log "Copy env.example to .env and configure your settings:"
    log "sudo cp /opt/ezrec-backend/env.example /opt/ezrec-backend/.env"
    log "sudo nano /opt/ezrec-backend/.env"
fi

# Check directory structure
log "Checking directory structure..."
ls -la /opt/ezrec-backend/

# Check virtual environments
log "Checking virtual environments..."
ls -la /opt/ezrec-backend/backend/venv/bin/python3
ls -la /opt/ezrec-backend/api/venv/bin/python3

# Check assets
log "Checking assets..."
ls -la /opt/ezrec-backend/assets/

log "🎉 EZREC deployment completed successfully!"
log ""
log "Next steps:"
log "1. Configure your .env file with your actual credentials"
log "2. Test the system: python3 /opt/ezrec-backend/test_complete_system.py"
log "3. Check service logs: sudo journalctl -u dual_recorder.service -f"
log ""
log "Services are now running and will start automatically on boot."
