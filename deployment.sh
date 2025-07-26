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
sudo find /opt/ezrec-backend -mindepth 1 ! -name '.env' -exec rm -rf {} +
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
    sudo apt-get install -y python3-requests python3-psutil python3-boto3 python3-dotenv
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

# Create new virtual environment
echo "📦 Creating new virtual environment..."
sudo python3 -m venv venv

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
venv/bin/pip install fastapi uvicorn python-multipart jinja2
venv/bin/pip install supabase boto3 python-dotenv requests psutil pytz numpy
echo "✅ Python dependencies installed successfully"

#------------------------------#
# 8. FIX PERMISSIONS AND OWNERSHIP
#------------------------------#
echo "🔐 Fixing permissions and ownership..."
sudo chown -R root:root /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || true

#------------------------------#
# 9. CREATE SYSTEMD SERVICE FILES
#------------------------------#
echo "⚙️ Creating systemd service files..."

# Create proper dual_recorder service
sudo tee /etc/systemd/system/dual_recorder.service > /dev/null << 'EOF'
[Unit]
Description=EZREC Dual Camera Recorder
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ezrec-backend
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/dual_recorder.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

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
User=root
WorkingDirectory=/opt/ezrec-backend
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/video_worker.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

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
User=root
WorkingDirectory=/opt/ezrec-backend/api
Environment=PATH=/opt/ezrec-backend/api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/api/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

#------------------------------#
# 10. RELOAD SYSTEMD
#------------------------------#
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

#------------------------------#
# 11. TEST BASIC FUNCTIONALITY
#------------------------------#
echo "🧪 Testing basic functionality..."

# Test FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is available"
else
    echo "❌ FFmpeg not found"
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
if python3 -c "import picamera2; print('✅ Picamera2 imported successfully')" 2>/dev/null; then
    echo "✅ Picamera2 is working"
else
    echo "❌ Picamera2 import failed"
fi

#------------------------------#
# 12. SETUP CRON JOBS
#------------------------------#
echo "⏰ Setting up cron jobs..."
sudo tee /etc/cron.d/ezrec-maintenance > /dev/null << 'EOF'
# Daily cleanup at 3 AM
0 3 * * * root /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/cleanup_old_data.py --recordings-days 7 --logs-days 14 --processed-days 3 --temp-days 1 --cache-days 30 --bookings-days 90 >> /opt/ezrec-backend/logs/cleanup_cron.log 2>&1

# Weekly system health check at 2 AM on Sundays
0 2 * * 0 root /opt/ezrec-backend/api/venv/bin/python3 /opt/ezrec-backend/backend/test_system_health.py >> /opt/ezrec-backend/logs/health_check.log 2>&1

# Restart services if they're down (every 30 minutes)
*/30 * * * * root /opt/ezrec-backend/restart_services.sh >> /opt/ezrec-backend/logs/service_monitor.log 2>&1
EOF

#------------------------------#
# 13. ENABLE AND START SERVICES
#------------------------------#
echo "🚀 Enabling and starting services..."
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service

sudo systemctl start ezrec-api.service
sleep 3
sudo systemctl start video_worker.service
sleep 3
sudo systemctl start dual_recorder.service

#------------------------------#
# 14. CHECK SERVICE STATUS
#------------------------------#
echo "📊 Checking service status..."
sudo systemctl status dual_recorder.service --no-pager -l
echo ""
sudo systemctl status video_worker.service --no-pager -l
echo ""
sudo systemctl status ezrec-api.service --no-pager -l

#------------------------------#
# 15. TEST API ENDPOINT
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
# 16. RUN SYSTEM READINESS TEST
#------------------------------#
echo "🔍 Running system readiness test..."
cd /opt/ezrec-backend
if sudo python3 test_system_readiness.py; then
    echo "✅ System readiness test passed"
else
    echo "⚠️ System readiness test failed - check the output above"
fi

#------------------------------#
# 17. FINAL SETUP COMPLETION
#------------------------------#
echo ""
echo "🎉 EZREC Backend Deployment Completed!"
echo "======================================"
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
echo "✅ Deployment completed successfully!"
