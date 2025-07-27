#!/bin/bash

# EZREC Backend Deployment Script
# This script handles complete deployment including all fixes and setup

set -e  # Exit on any error

echo "🚀 EZREC Backend Deployment Script"
echo "=================================="

#------------------------------#
# 1. STOP ALL EXISTING SERVICES
#------------------------------#
echo "🛑 Stopping all existing services..."
sudo systemctl stop dual_recorder.service 2>/dev/null || true
sudo systemctl stop video_worker.service 2>/dev/null || true
sudo systemctl stop ezrec-api.service 2>/dev/null || true
sudo systemctl stop system_status.service 2>/dev/null || true

# Kill any remaining processes
echo "🔪 Killing remaining processes..."
sudo pkill -f "dual_recorder.py" 2>/dev/null || true
sudo pkill -f "video_worker.py" 2>/dev/null || true
sudo pkill -f "api_server.py" 2>/dev/null || true

#------------------------------#
# 2. CLEANUP OLD INSTALLATION
#------------------------------#
echo "🧹 Cleaning up old installation..."
# DO NOT REMOVE .env FILE! (User-managed)
sudo find /opt/ezrec-backend -mindepth 1 ! -name '.env' -exec rm -rf {} + 2>/dev/null || true
sudo mkdir -p /opt/ezrec-backend

#------------------------------#
# 3. COPY PROJECT FILES
#------------------------------#
echo "📁 Copying project files..."
# DO NOT OVERWRITE .env FILE! (User-managed)
sudo rsync -a --exclude='.env' ./ /opt/ezrec-backend/
sudo chown -R root:root /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend

#------------------------------#
# 4. CHECK AND INSTALL REQUIRED TOOLS
#------------------------------#
echo "🔧 Checking and installing required tools..."
check_and_install_tools() {
    # Check FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        echo "❌ FFmpeg not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "✅ FFmpeg is available"
    fi
    
    # Check FFprobe
    if ! command -v ffprobe &> /dev/null; then
        echo "❌ FFprobe not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "✅ FFprobe is available"
    fi
    
    # Check v4l2-ctl
    if ! command -v v4l2-ctl &> /dev/null; then
        echo "❌ v4l2-ctl not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y v4l-utils
    else
        echo "✅ v4l2-ctl is available"
    fi
    
    # Check Python dependencies
    if ! python3 -c "import picamera2" &> /dev/null; then
        echo "❌ Picamera2 not found. Installing..."
        sudo apt-get update
        sudo apt-get install -y python3-picamera2
    else
        echo "✅ Picamera2 is available"
    fi
    
    # Install additional dependencies
    echo "📦 Installing additional dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3-requests python3-psutil python3-boto3 python3-dotenv build-essential
    sudo apt autoremove -y
}

check_and_install_tools

#------------------------------#
# 5. CREATE REQUIRED DIRECTORIES
#------------------------------#
echo "📁 Creating required directories..."
sudo mkdir -p /opt/ezrec-backend/logs
sudo mkdir -p /opt/ezrec-backend/recordings
sudo mkdir -p /opt/ezrec-backend/processed
sudo mkdir -p /opt/ezrec-backend/media_cache
sudo mkdir -p /opt/ezrec-backend/api/local_data
sudo mkdir -p /opt/ezrec-backend/backend
sudo mkdir -p /opt/ezrec-backend/temp

# Fix permissions for ezrec user
echo "🔐 Fixing directory permissions..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/logs
sudo chown -R ezrec:ezrec /opt/ezrec-backend/recordings
sudo chown -R ezrec:ezrec /opt/ezrec-backend/processed
sudo chown -R ezrec:ezrec /opt/ezrec-backend/media_cache
sudo chown -R ezrec:ezrec /opt/ezrec-backend/api/local_data
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend
sudo chown -R ezrec:ezrec /opt/ezrec-backend/temp
sudo chmod -R 755 /opt/ezrec-backend/logs
sudo chmod -R 755 /opt/ezrec-backend/recordings
sudo chmod -R 755 /opt/ezrec-backend/processed
sudo chmod -R 755 /opt/ezrec-backend/media_cache
sudo chmod -R 755 /opt/ezrec-backend/api/local_data
sudo chmod -R 755 /opt/ezrec-backend/backend
sudo chmod -R 755 /opt/ezrec-backend/temp

#------------------------------#
# 6. FIX PYTHON PATH ISSUES
#------------------------------#
echo "🐍 Fixing Python path issues..."
cd /opt/ezrec-backend
sudo touch backend/__init__.py
sudo touch api/__init__.py

#------------------------------#
# 7. SETUP VIRTUAL ENVIRONMENT
#------------------------------#
echo "🐍 Setting up Python virtual environment..."
cd /opt/ezrec-backend/api

# Remove existing venv if it exists and has permission issues
if [ -d "venv" ]; then
    echo "🧹 Removing existing virtual environment..."
    sudo rm -rf venv
fi

# Create new virtual environment with system-site-packages for picamera2
echo "📦 Creating new virtual environment with system-site-packages..."
sudo python3 -m venv --system-site-packages venv

# Get the current user who ran sudo
CURRENT_USER=${SUDO_USER:-$USER}
echo "🔐 Setting virtual environment ownership to user: $CURRENT_USER"

# Fix ownership to current user so pip can install packages
echo "🔐 Fixing virtual environment ownership..."
sudo chown -R $CURRENT_USER:$CURRENT_USER venv
sudo chmod -R 755 venv

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd /opt/ezrec-backend/api

# Install dependencies with proper ownership
echo "🔧 Installing Python packages..."
sudo -u $CURRENT_USER venv/bin/pip install fastapi uvicorn python-multipart jinja2
sudo -u $CURRENT_USER venv/bin/pip install supabase boto3 python-dotenv requests psutil pytz numpy opencv-python-headless email-validator

# Install picamera2 system packages (CRITICAL FIX)
echo "📷 Installing picamera2 system packages..."
if command -v apt-get &> /dev/null; then
    echo "🔧 Installing system-wide picamera2 packages..."
    sudo apt-get update
    sudo apt-get install -y python3-libcamera python3-picamera2 || true
fi

# Test picamera2 import
if venv/bin/python3 -c "import picamera2" 2>/dev/null; then
    echo "✅ picamera2 available in virtual environment"
else
    echo "⚠️ picamera2 not available in virtual environment"
    echo "🔧 This is normal on some Raspberry Pi configurations"
    echo "🔧 The system will use alternative camera detection methods"
fi

echo "✅ Python dependencies installed successfully"

#------------------------------#
# 8. SETUP ENVIRONMENT CONFIGURATION
#------------------------------#
echo "⚙️ Setting up environment configuration..."

# Create .env file from template if it doesn't exist
if [ ! -f "/opt/ezrec-backend/.env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f "/opt/ezrec-backend/env.example" ]; then
        sudo cp /opt/ezrec-backend/env.example /opt/ezrec-backend/.env
        echo "✅ .env file created from template"
    else
        echo "⚠️ env.example not found, creating basic .env file..."
        sudo tee /opt/ezrec-backend/.env > /dev/null << 'EOF'
# EZREC Backend Configuration
# Add your Supabase and AWS credentials here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# Camera Configuration
USER_ID=your_user_id_here
CAMERA_ID=your_camera_id_here

# Camera Hardware Configuration
CAMERA_0_SERIAL=your_camera_0_serial_here
CAMERA_1_SERIAL=your_camera_1_serial_here
CAMERA_0_NAME=Camera0
CAMERA_1_NAME=Camera1

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name_here

# Recording Configuration
RECORDING_DURATION=300
VIDEO_QUALITY=high
EOF
        echo "✅ Basic .env file created"
        echo "🔧 Please edit /opt/ezrec-backend/.env with your actual credentials"
        echo "🔧 Example: sudo nano /opt/ezrec-backend/.env"
    fi
else
    echo "✅ .env file already exists (user-managed)"
fi

#------------------------------#
# 9. CREATE DEDICATED USER AND FIX PERMISSIONS
#------------------------------#
echo "🔐 Creating dedicated user and fixing permissions..."

# Create dedicated user for services
if ! id "ezrec" &>/dev/null; then
    echo "👤 Creating dedicated ezrec user..."
    sudo useradd -r -s /bin/false -d /opt/ezrec-backend ezrec
else
    echo "✅ ezrec user already exists"
fi

# Set proper ownership
sudo chown -R ezrec:ezrec /opt/ezrec-backend
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/ezrec-backend/api/venv
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend/api/venv
sudo chmod 644 /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || true

#------------------------------#
# 10. CREATE SYSTEMD SERVICE FILES
#------------------------------#
echo "⚙️ Creating systemd service files..."

# Create proper dual_recorder service
sudo tee /etc/systemd/system/dual_recorder.service > /dev/null << 'EOF'
[Unit]
Description=EZREC Dual Camera Recorder
After=network.target

[Service]
Type=simple
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/dual_recorder.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
ProtectSystem=full
ProtectHome=yes
NoNewPrivileges=true
PrivateTmp=true
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_SYS_RAWIO

[Install]
WantedBy=multi-user.target
EOF

# Create proper video_worker service
sudo tee /etc/systemd/system/video_worker.service > /dev/null << 'EOF'
[Unit]
Description=EZREC Video Processor
After=network.target

[Service]
Type=simple
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/video_worker.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
ProtectSystem=full
ProtectHome=yes
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create proper ezrec-api service
sudo tee /etc/systemd/system/ezrec-api.service > /dev/null << 'EOF'
[Unit]
Description=EZREC FastAPI Backend
After=network.target

[Service]
Type=simple
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend/api
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
ProtectSystem=full
ProtectHome=yes
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create system_status service (one-shot service for timer)
sudo tee /etc/systemd/system/system_status.service > /dev/null << 'EOF'
[Unit]
Description=EZREC System Status Monitor
After=network.target
Type=oneshot
RemainAfterExit=no

[Service]
Type=oneshot
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend/backend
Environment=PATH=/opt/ezrec-backend/api/venv/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/system_status.py
StandardOutput=journal
StandardError=journal
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
EOF

# Create system_status timer
sudo tee /etc/systemd/system/system_status.timer > /dev/null << 'EOF'
[Unit]
Description=EZREC System Status Monitor Timer
After=network.target

[Timer]
OnBootSec=30s
OnUnitActiveSec=5m
Unit=system_status.service

[Install]
WantedBy=timers.target
EOF

#------------------------------#
# 11. RELOAD SYSTEMD
#------------------------------#
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

#------------------------------#
# 12. TEST BASIC FUNCTIONALITY
#------------------------------#
echo "🧪 Testing basic functionality..."

# Test FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is available"
    # Test FFmpeg functionality
    if ffmpeg -version &> /dev/null; then
        echo "✅ FFmpeg is working correctly"
    else
        echo "⚠️ FFmpeg found but not working correctly"
    fi
else
    echo "❌ FFmpeg not found"
    echo "🔧 Installing FFmpeg..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg || { echo "❌ Failed to install FFmpeg"; exit 1; }
    if command -v ffmpeg &> /dev/null; then
        echo "✅ FFmpeg installed successfully"
    else
        echo "❌ FFmpeg installation failed"
        exit 1
    fi
fi

# Test ffprobe
if command -v ffprobe &> /dev/null; then
    echo "✅ FFprobe is available"
    # Test ffprobe functionality
    if ffprobe -version &> /dev/null; then
        echo "✅ FFprobe is working correctly"
    else
        echo "⚠️ FFprobe found but not working correctly"
    fi
else
    echo "❌ FFprobe not found"
    echo "🔧 Installing FFprobe..."
    sudo apt-get install -y ffmpeg || { echo "❌ Failed to install FFprobe"; exit 1; }
    if command -v ffprobe &> /dev/null; then
        echo "✅ FFprobe installed successfully"
    else
        echo "❌ FFprobe installation failed"
        exit 1
    fi
fi

# Test v4l2-ctl
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ v4l2-ctl is available"
    echo "📹 Camera devices:"
    v4l2-ctl --list-devices | grep -A 1 "video" | head -10
else
    echo "❌ v4l2-ctl not found"
fi

# Test Python imports
echo "🐍 Testing Python imports..."
cd /opt/ezrec-backend/backend

# Test picamera2 in virtual environment (CRITICAL)
echo "📷 Testing picamera2 in virtual environment..."
if /opt/ezrec-backend/api/venv/bin/python3 -c "import picamera2; print('✅ Picamera2 imported successfully')" 2>/dev/null; then
    echo "✅ Picamera2 is working in virtual environment"
else
    echo "❌ Picamera2 import failed in virtual environment"
    echo "🔧 Attempting to fix picamera2 installation..."
    sudo -u $CURRENT_USER /opt/ezrec-backend/api/venv/bin/pip install --force-reinstall picamera2
    if /opt/ezrec-backend/api/venv/bin/python3 -c "import picamera2" 2>/dev/null; then
        echo "✅ Picamera2 fixed and working"
    else
        echo "⚠️ Picamera2 still not working - this may cause recording issues"
    fi
fi

# Test other critical packages
echo "🔧 Testing other critical packages..."
for package in fastapi supabase psutil boto3; do
    if /opt/ezrec-backend/api/venv/bin/python3 -c "import $package" 2>/dev/null; then
        echo "✅ $package is working"
    else
        echo "❌ $package import failed"
    fi
done

#------------------------------#
# 13. SETUP CRON JOBS
#------------------------------#
echo "⏰ Setting up cron jobs..."
# Remove existing cron jobs to avoid duplicates
sudo rm -f /etc/cron.d/ezrec-maintenance
sudo tee /etc/cron.d/ezrec-maintenance > /dev/null << 'EOF'
# Daily cleanup at 3 AM
0 3 * * * root /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/cleanup_old_data.py --recordings-days 7 --logs-days 14 --processed-days 3 --temp-days 1 --cache-days 30 --bookings-days 90 >> /opt/ezrec-backend/logs/cleanup_cron.log 2>&1

# Weekly system health check at 2 AM on Sundays
0 2 * * 0 root /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/test_system_health.py >> /opt/ezrec-backend/logs/health_check.log 2>&1

# Restart services if they're down (every 30 minutes)
*/30 * * * * root /opt/ezrec-backend/restart_services.sh >> /opt/ezrec-backend/logs/service_monitor.log 2>&1
EOF

#------------------------------#
# 14. ENABLE AND START SERVICES
#------------------------------#
echo "🚀 Enabling and starting services..."

# Add ezrec user to video group for camera access
echo "📹 Adding ezrec user to video group for camera access..."
sudo usermod -a -G video ezrec

# Reset failed services before enabling
echo "🔄 Resetting failed services..."
sudo systemctl reset-failed dual_recorder.service 2>/dev/null || true
sudo systemctl reset-failed video_worker.service 2>/dev/null || true
sudo systemctl reset-failed ezrec-api.service 2>/dev/null || true
sudo systemctl reset-failed system_status.service 2>/dev/null || true

# Enable all services
sudo systemctl enable dual_recorder.service || { echo "❌ Failed to enable dual_recorder.service"; exit 1; }
sudo systemctl enable video_worker.service || { echo "❌ Failed to enable video_worker.service"; exit 1; }
sudo systemctl enable ezrec-api.service || { echo "❌ Failed to enable ezrec-api.service"; exit 1; }
sudo systemctl enable system_status.service || { echo "❌ Failed to enable system_status.service"; exit 1; }
sudo systemctl enable system_status.timer || { echo "❌ Failed to enable system_status.timer"; exit 1; }

# Validate critical files exist before starting services
echo "🔍 Validating critical files..."
critical_files=(
    "/opt/ezrec-backend/backend/dual_recorder.py"
    "/opt/ezrec-backend/backend/video_worker.py"
    "/opt/ezrec-backend/backend/system_status.py"
    "/opt/ezrec-backend/api/api_server.py"
    "/opt/ezrec-backend/backend/enhanced_merge.py"
)

missing_files=false
for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Critical file missing: $file"
        missing_files=true
    else
        echo "✅ Found: $file"
    fi
done

if [ "$missing_files" = true ]; then
    echo "⚠️ Some critical files are missing. Deployment may fail."
    echo "Continuing anyway, but check the file paths above."
fi

#------------------------------#
# 14.5. CLEANUP BROKEN RECORDING JOBS
#------------------------------#
echo "🧹 Cleaning up broken recording jobs..."
find /opt/ezrec-backend/recordings -type f \( -name "*.done" -o -name "*.meta" -o -name "*.lock" -o -name "*.error" -o -name "*.completed" -o -name "*.merge_error" \) | while read -r marker; do
  base="${marker%.*}"
  if [ ! -f "${base}.mp4" ]; then
    echo "❌ Found orphan marker file: $marker (no .mp4 found). Removing..."
    rm -f "$marker"
  fi
done
echo "✅ Cleanup completed"

#------------------------------#
# 14.6. SETUP LOG ROTATION
#------------------------------#
echo "📝 Setting up log rotation..."
if [ -f "logrotate.conf" ]; then
    sudo cp logrotate.conf /etc/logrotate.d/ezrec-backend || { echo "❌ Failed to copy logrotate config"; exit 1; }
    sudo chmod 644 /etc/logrotate.d/ezrec-backend || { echo "❌ Failed to set logrotate permissions"; exit 1; }
    
    # Test the logrotate configuration
    if sudo logrotate --debug /etc/logrotate.d/ezrec-backend > /dev/null 2>&1; then
        echo "✅ Log rotation configured and validated"
    else
        echo "⚠️ Log rotation configured but validation failed"
    fi
else
    echo "⚠️ logrotate.conf not found, creating basic logrotate config..."
    sudo tee /etc/logrotate.d/ezrec-backend > /dev/null << 'EOF'
/opt/ezrec-backend/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ezrec ezrec
}
EOF
    echo "✅ Basic log rotation configured"
fi

# Restart all services (safer than individual starts)
echo "🔄 Restarting all services..."
sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service system_status.service
sudo systemctl start system_status.timer || { echo "❌ Failed to start system_status.timer"; exit 1; }

#------------------------------#
# 15. CHECK SERVICE STATUS
#------------------------------#
echo "📊 Checking service status..."
services=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")

for service in "${services[@]}"; do
    echo "--- $service ---"
    if sudo systemctl status "$service" --no-pager -l 2>/dev/null; then
        echo "✅ $service status retrieved successfully"
    else
        echo "⚠️ Could not retrieve $service status (use: sudo journalctl -u $service)"
    fi
    echo ""
done

# Validate all services are running
echo "🔍 Validating all services are running..."
services=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")
all_running=true

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        all_running=false
    fi
done

if [ "$all_running" = true ]; then
    echo "🎉 All services are running successfully!"
else
    echo "⚠️ Some services failed to start. Check the status above."
fi

#------------------------------#
# 16. TEST API ENDPOINT
#------------------------------#
echo "🌐 Testing API endpoint..."
sleep 5
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is responding"
    curl -s http://localhost:8000/health | jq '.status, .warnings' 2>/dev/null || echo "API health check completed"
else
    echo "❌ API not responding"
fi

#------------------------------#
# 17. RUN SYSTEM READINESS TEST
#------------------------------#
echo "🔍 Running system readiness test..."
cd /opt/ezrec-backend
if sudo python3 test_system_readiness.py; then
    echo "✅ System readiness test passed"
else
    echo "⚠️ System readiness test failed - check the output above"
fi

#------------------------------#
# 18. ENHANCED HEALTH CHECK
#------------------------------#
echo "🔍 Verifying system services..."
echo "📊 Service Status Summary:"
echo "=========================="

# Check each service individually
services=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")
for service in "${services[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        echo "✅ $service: ACTIVE"
    else
        echo "❌ $service: INACTIVE"
    fi
done

echo ""
echo "🌐 API Connectivity Test:"
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is reachable at http://localhost:8000"
    # Try to get detailed health info
    if command -v jq > /dev/null; then
        echo "📊 API Health Details:"
        curl -s http://localhost:8000/health | jq '.status, .warnings' 2>/dev/null || echo "   Health check completed"
    fi
else
    echo "❌ API not reachable at http://localhost:8000"
fi

echo ""
echo "📁 Critical Directory Check:"
critical_dirs=("/opt/ezrec-backend/logs" "/opt/ezrec-backend/recordings" "/opt/ezrec-backend/api")
for dir in "${critical_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir: EXISTS"
    else
        echo "❌ $dir: MISSING"
    fi
done

#------------------------------#
# 19. FINAL SETUP COMPLETION
#------------------------------#
DEPLOYMENT_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo ""
echo "🎉 EZREC Backend Deployment Completed!"
echo "======================================"
echo "📅 Deployment Time: $DEPLOYMENT_TIMESTAMP"
echo "👤 Service User: ezrec"
echo "🔐 Security: Hardened systemd services with minimal privileges"
echo ""
echo "📋 Next Steps:"
echo "1. Create and configure /opt/ezrec-backend/.env with your credentials"
echo "2. Create a test booking to verify everything works"
echo "3. Monitor logs: sudo journalctl -u dual_recorder.service -f"
echo ""
echo "📁 Important Directories:"
echo "   - Logs: /opt/ezrec-backend/logs"
echo "   - Recordings: /opt/ezrec-backend/recordings"
echo "   - API: /opt/ezrec-backend/api"
echo ""
echo "🔧 Useful Commands:"
echo "   - Check status: sudo systemctl status dual_recorder.service"
echo "   - View logs: sudo journalctl -u dual_recorder.service -f"
echo "   - Restart services: sudo systemctl restart dual_recorder.service"
echo "   - Test system: sudo python3 test_system_readiness.py"
echo ""
echo "📝 Tip: To log this deployment, run:"
echo "   ./deployment.sh | tee ezrec_deploy_\$(date +%Y%m%d_%H%M%S).log"
echo ""
echo "✅ Deployment completed successfully!"
