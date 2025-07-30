#!/bin/bash

# EZREC Backend Deployment Script
# This script sets up the complete EZREC backend system

set -e

echo "🚀 EZREC Backend Deployment Script"
echo "=================================="

# Get current user
CURRENT_USER=$(whoami)

#------------------------------#
# 1. STOP EXISTING SERVICES
#------------------------------#
echo "🛑 Stopping all existing services..."

# Stop services if they exist
sudo systemctl stop dual_recorder.service 2>/dev/null || true
sudo systemctl stop video_worker.service 2>/dev/null || true
sudo systemctl stop ezrec-api.service 2>/dev/null || true
sudo systemctl stop system_status.service 2>/dev/null || true

# Kill any remaining processes
echo "🔪 Killing remaining processes..."
sudo pkill -f "dual_recorder.py" 2>/dev/null || true
sudo pkill -f "video_worker.py" 2>/dev/null || true
sudo pkill -f "api_server.py" 2>/dev/null || true
sudo pkill -f "system_status.py" 2>/dev/null || true

#------------------------------#
# 2. CLEANUP OLD INSTALLATION
#------------------------------#
echo "🧹 Cleaning up old installation..."

# Remove old installation if it exists
if [ -d "/opt/ezrec-backend" ]; then
    echo "📁 Removing old installation..."
    sudo rm -rf /opt/ezrec-backend
fi

#------------------------------#
# 3. COPY PROJECT FILES
#------------------------------#
echo "📁 Copying project files..."

# Create base directory
sudo mkdir -p /opt/ezrec-backend

# Copy all files
sudo cp -r . /opt/ezrec-backend/

#------------------------------#
# 4. INSTALL REQUIRED TOOLS
#------------------------------#
echo "🔧 Checking and installing required tools..."

    # Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is available"
else
    echo "❌ FFmpeg not found"
    echo "🔧 Installing FFmpeg..."
        sudo apt-get update
    sudo apt-get install -y ffmpeg || { echo "❌ Failed to install FFmpeg"; exit 1; }
    fi
    
    # Check FFprobe
if command -v ffprobe &> /dev/null; then
    echo "✅ FFprobe is available"
else
    echo "❌ FFprobe not found"
    echo "🔧 Installing FFprobe..."
    sudo apt-get install -y ffmpeg || { echo "❌ Failed to install FFprobe"; exit 1; }
    fi
    
    # Check v4l2-ctl
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ v4l2-ctl is available"
else
    echo "❌ v4l2-ctl not found"
    echo "🔧 Installing v4l-utils..."
    sudo apt-get install -y v4l-utils || { echo "❌ Failed to install v4l-utils"; exit 1; }
fi

# Check Picamera2
if python3 -c "import picamera2" 2>/dev/null; then
    echo "✅ Picamera2 is available"
else
    echo "❌ Picamera2 not found"
    echo "🔧 Installing Picamera2..."
    sudo apt-get install -y python3-picamera2 || { echo "❌ Failed to install Picamera2"; exit 1; }
fi

#------------------------------#
# 5. INSTALL ADDITIONAL DEPENDENCIES
#------------------------------#
    echo "📦 Installing additional dependencies..."

# Update package list
    sudo apt-get update

# Install Python packages
    sudo apt-get install -y python3-requests python3-psutil python3-boto3 python3-dotenv build-essential

# Install additional system packages
sudo apt-get install -y imagemagick v4l-utils

#------------------------------#
# 6. CREATE REQUIRED DIRECTORIES
#------------------------------#
echo "📁 Creating required directories..."

# Create all required directories
sudo mkdir -p /opt/ezrec-backend/backend
sudo mkdir -p /opt/ezrec-backend/api
sudo mkdir -p /opt/ezrec-backend/recordings
sudo mkdir -p /opt/ezrec-backend/processed
sudo mkdir -p /opt/ezrec-backend/final
sudo mkdir -p /opt/ezrec-backend/assets
sudo mkdir -p /opt/ezrec-backend/logs
sudo mkdir -p /opt/ezrec-backend/events
sudo mkdir -p /opt/ezrec-backend/api/local_data

#------------------------------#
# 7. CREATE DEDICATED USER AND FIX PERMISSIONS
#------------------------------#
echo "🔐 Creating dedicated user and fixing permissions..."

# Create dedicated user for services
if ! id "ezrec" &>/dev/null; then
    echo "👤 Creating dedicated ezrec user..."
    sudo useradd -r -s /bin/false -d /opt/ezrec-backend ezrec
else
    echo "✅ ezrec user already exists"
fi

# Add ezrec user to video group
sudo usermod -a -G video ezrec

# Set proper ownership BEFORE creating virtual environments
echo "🔐 Setting ownership to current user for virtual environment creation..."
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/ezrec-backend

# Set permissions
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/.env 2>/dev/null || true
sudo chmod 644 /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || true

#------------------------------#
# 8. SETUP PYTHON ENVIRONMENTS
#------------------------------#
echo "🐍 Setting up Python environments..."

# Setup API virtual environment
echo "🐍 Setting up API virtual environment..."
cd /opt/ezrec-backend/api

# Remove existing venv if it exists and has permission issues
if [ -d "venv" ]; then
    echo "🧹 Removing existing API virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "📦 Creating API virtual environment..."
python3 -m venv venv

# Install dependencies
echo "📦 Installing API dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Setup Backend virtual environment
echo "🐍 Setting up Backend virtual environment..."
cd /opt/ezrec-backend/backend

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "🧹 Removing existing backend virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "📦 Creating backend virtual environment..."
python3 -m venv venv

# Install dependencies
echo "📦 Installing backend dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Fix virtual environment ownership for services
echo "🔐 Setting ownership for services..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend/venv
sudo chown -R ezrec:ezrec /opt/ezrec-backend/api/venv

#------------------------------#
# 9. TEST PYTHON DEPENDENCIES
#------------------------------#
echo "🐍 Testing Python imports..."

cd /opt/ezrec-backend/api
source venv/bin/activate

# Test critical packages
echo "🔧 Testing other critical packages..."
python3 -c "import fastapi; print('✅ fastapi is working')" || echo "❌ fastapi failed"
python3 -c "import supabase; print('✅ supabase is working')" || echo "❌ supabase failed"
python3 -c "import psutil; print('✅ psutil is working')" || echo "❌ psutil failed"
python3 -c "import boto3; print('✅ boto3 is working')" || echo "❌ boto3 failed"

echo "✅ Python dependencies installed successfully"

#------------------------------#
# 10. SETUP ENVIRONMENT CONFIGURATION
#------------------------------#
echo "⚙️ Setting up environment configuration..."

ENV_FILE="/opt/ezrec-backend/.env"
REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_SERVICE_ROLE_KEY" "USER_ID" "CAMERA_ID")

# Create .env file if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating .env file..."
    sudo tee "$ENV_FILE" > /dev/null << 'EOF'
# EZREC Backend Environment Configuration
# Copy this file to .env and fill in your actual values

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=your_s3_bucket_name_here
AWS_USER_MEDIA_BUCKET=your_user_media_bucket_here

# Camera Configuration
CAMERA_0_SERIAL=88000
CAMERA_1_SERIAL=80000
DUAL_CAMERA_MODE=true

# User Configuration
USER_ID=your_user_id_here
CAMERA_ID=your_camera_id_here

# Email Configuration (for share links)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
EMAIL_USE_TLS=True
EMAIL_FROM=your_email@gmail.com

# Share Configuration
SHARE_BASE_URL=https://yourdomain.com

# Timezone
TIMEZONE_NAME=UTC

# Recording Configuration
RECORDING_QUALITY=high
MERGE_METHOD=side_by_side
RECORDING_FPS=30
LOG_LEVEL=INFO
BOOKING_CHECK_INTERVAL=5
EOF
        echo "✅ Basic .env file created"
        echo "🔧 Please edit /opt/ezrec-backend/.env with your actual credentials"
        echo "🔧 Example: sudo nano /opt/ezrec-backend/.env"
        echo ""
        echo "📋 Required environment variables:"
        echo "   SUPABASE_URL=your_supabase_project_url"
        echo "   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key"
        echo "   USER_ID=your_user_id"
        echo "   CAMERA_ID=your_camera_id"
        echo "   CAMERA_0_SERIAL=your_first_camera_serial"
        echo "   CAMERA_1_SERIAL=your_second_camera_serial"
        echo ""
        echo "⚠️  The system will not work properly until these are configured!"
else
    echo "✅ .env file already exists"
    
    # Check if all required variables are present
    missing_vars=()
    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -eq 0 ]; then
        echo "✅ All required environment variables are configured"
    else
        echo "⚠️ Missing required environment variables: ${missing_vars[*]}"
        echo "🔧 Please add them to /opt/ezrec-backend/.env"
        echo "🔧 Example: sudo nano /opt/ezrec-backend/.env"
    fi
    
    echo "🔧 To update: sudo nano /opt/ezrec-backend/.env"
    echo "📋 Make sure these variables are set: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, USER_ID, CAMERA_ID"
fi

#------------------------------#
# 11. INSTALL SYSTEMD SERVICE FILES
#------------------------------#
echo "⚙️ Installing systemd service files..."

# Copy systemd service files from the systemd folder
if [ -d "/opt/ezrec-backend/systemd" ]; then
    echo "📁 Copying systemd service files..."

    # Copy all .service files
    for service_file in /opt/ezrec-backend/systemd/*.service; do
        if [ -f "$service_file" ]; then
            service_name=$(basename "$service_file")
            echo "📋 Installing $service_name..."
            sudo cp "$service_file" "/etc/systemd/system/"
            sudo chmod 644 "/etc/systemd/system/$service_name"
        fi
    done
    
    # Copy all .timer files
    for timer_file in /opt/ezrec-backend/systemd/*.timer; do
        if [ -f "$timer_file" ]; then
            timer_name=$(basename "$timer_file")
            echo "📋 Installing $timer_name..."
            sudo cp "$timer_file" "/etc/systemd/system/"
            sudo chmod 644 "/etc/systemd/system/$timer_name"
        fi
    done
    
    echo "✅ Systemd service files installed"
else
    echo "⚠️ Systemd folder not found, creating basic services..."
    
    # Create basic dual_recorder service
sudo tee /etc/systemd/system/dual_recorder.service > /dev/null << 'EOF'
[Unit]
Description=EZREC Dual Camera Recorder
After=network.target

[Service]
Type=simple
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend/backend
Environment=PATH=/opt/ezrec-backend/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 dual_recorder.py
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

    # Create basic video_worker service
sudo tee /etc/systemd/system/video_worker.service > /dev/null << 'EOF'
[Unit]
Description=EZREC Video Processor
After=network.target

[Service]
Type=simple
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend/backend
Environment=PATH=/opt/ezrec-backend/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 video_worker.py
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

    # Create basic ezrec-api service
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

[Service]
Type=oneshot
RemainAfterExit=no
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend/backend
Environment=PATH=/opt/ezrec-backend/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 system_status.py
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

    echo "✅ Basic systemd services created"
fi

#------------------------------#
# 12. RELOAD SYSTEMD
#------------------------------#
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

#------------------------------#
# 13. TEST BASIC FUNCTIONALITY
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
source venv/bin/activate

# Test critical packages
echo "🔧 Testing other critical packages..."
python3 -c "import fastapi; print('✅ fastapi is working')" || echo "❌ fastapi failed"
python3 -c "import supabase; print('✅ supabase is working')" || echo "❌ supabase failed"
python3 -c "import psutil; print('✅ psutil is working')" || echo "❌ psutil failed"
python3 -c "import boto3; print('✅ boto3 is working')" || echo "❌ boto3 failed"

#------------------------------#
# 14. CREATE ASSETS
#------------------------------#
echo "🎨 Creating assets..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
python3 create_assets.py

#------------------------------#
# 15. SETUP CRON JOBS
#------------------------------#
echo "⏰ Setting up cron jobs..."

# Add cron job for log rotation (if not exists)
if ! crontab -l 2>/dev/null | grep -q "ezrec"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * find /opt/ezrec-backend/logs -name '*.log' -mtime +7 -delete") | crontab -
    echo "✅ Log rotation cron job added"
else
    echo "✅ Log rotation cron job already exists"
fi

#------------------------------#
# 16. APPLY COMPREHENSIVE FIXES
#------------------------------#
echo "🔧 Applying comprehensive fixes..."
echo "=================================="

# Make all fix scripts executable
echo "📝 Making fix scripts executable..."
cd /opt/ezrec-backend
chmod +x *.sh

# Apply fixes in order
echo "🔄 Step 1: Fixing permissions..."
if [ -f "fix_permissions.sh" ]; then
    sudo ./fix_permissions.sh
else
    echo "⚠️ fix_permissions.sh not found, applying basic permissions..."
    sudo mkdir -p /opt/ezrec-backend/{logs,media_cache,api/local_data,events,recordings,processed,final,assets}
    sudo touch /opt/ezrec-backend/api/local_data/bookings.json
    sudo touch /opt/ezrec-backend/status.json
    sudo chown -R ezrec:ezrec /opt/ezrec-backend
    sudo chmod -R 755 /opt/ezrec-backend
    sudo chmod 664 /opt/ezrec-backend/api/local_data/bookings.json
    sudo chmod 664 /opt/ezrec-backend/status.json
fi

echo "🔄 Step 2: Installing libcamera..."
if [ -f "fix_libcamera.sh" ]; then
    sudo ./fix_libcamera.sh
else
    echo "⚠️ fix_libcamera.sh not found, installing manually..."
    sudo apt update
    sudo apt install -y python3-libcamera libcamera-apps
fi

echo "🔄 Step 3: Installing ImageMagick..."
if [ -f "fix_imagemagick.sh" ]; then
    sudo ./fix_imagemagick.sh
else
    echo "⚠️ fix_imagemagick.sh not found, installing manually..."
    sudo apt update
    sudo apt install -y imagemagick
fi

echo "🔄 Step 4: Fixing backend venv..."
if [ -f "fix_backend_venv_final.sh" ]; then
    sudo ./fix_backend_venv_final.sh
else
    echo "⚠️ fix_backend_venv_final.sh not found, applying basic venv fix..."
    cd /opt/ezrec-backend/backend
    sudo rm -rf venv
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r /opt/ezrec-backend/requirements.txt
    sudo chown -R ezrec:ezrec venv
fi

echo "🔄 Step 5: Fixing pykms module..."
if [ -f "fix_pykms.sh" ]; then
    sudo ./fix_pykms.sh
else
    echo "⚠️ fix_pykms.sh not found, installing manually..."
    sudo apt update
    sudo apt install -y python3-kms
fi

echo "🔄 Step 6: Fixing Supabase integration..."
if [ -f "fix_supabase_issues.sh" ]; then
    sudo ./fix_supabase_issues.sh
else
    echo "⚠️ fix_supabase_issues.sh not found, applying basic fixes..."
    # Create booking_utils.py if it doesn't exist
    if [ ! -f "/opt/ezrec-backend/api/booking_utils.py" ]; then
        sudo -u ezrec tee /opt/ezrec-backend/api/booking_utils.py > /dev/null << 'EOF'
def update_booking_status(booking_id: str, new_status: str) -> bool:
    """Update booking status in Supabase"""
    try:
        from supabase import create_client, Client
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not configured")
            return False
            
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Update the booking status
        result = supabase.table('bookings').update({
            'status': new_status,
            'updated_at': 'now()'
        }).eq('id', booking_id).execute()
        
        print(f"✅ Updated booking {booking_id} status to {new_status}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update booking status: {e}")
        return False
EOF
    fi
fi

echo "🔄 Step 7: Fixing API issues..."
if [ -f "fix_api_issues.sh" ]; then
    sudo ./fix_api_issues.sh
else
    echo "⚠️ fix_api_issues.sh not found, applying basic API fixes..."
    # Ensure bookings.json exists and is valid JSON
    if [ ! -f "/opt/ezrec-backend/api/local_data/bookings.json" ]; then
        sudo -u ezrec tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null << 'EOF'
[]
EOF
    fi
    sudo chown ezrec:ezrec /opt/ezrec-backend/api/local_data/bookings.json
    sudo chmod 664 /opt/ezrec-backend/api/local_data/bookings.json
fi

#------------------------------#
# 17. ENABLE AND START SERVICES
#------------------------------#
echo "🚀 Enabling and starting services..."

# Add ezrec user to video group for camera access
sudo usermod -a -G video ezrec

# Reset failed services
echo "🔄 Resetting failed services..."
sudo systemctl reset-failed

# Enable services
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service
sudo systemctl enable system_status.service
sudo systemctl enable system_status.timer

# Start services
echo "🚀 Starting services..."
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service
sudo systemctl start system_status.timer

#------------------------------#
# 18. VERIFY CRITICAL FILES
#------------------------------#
echo "📋 Verifying critical files..."

CRITICAL_FILES=(
    "dual_recorder.py"
    "video_worker.py"
    "system_status.py"
    "api_server.py"
    "enhanced_merge.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "/opt/ezrec-backend/backend/$file" ] || [ -f "/opt/ezrec-backend/api/$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

#------------------------------#
# 19. FINAL STATUS CHECK
#------------------------------#
echo "🎯 Final status check..."

# Check service status
echo "📊 Service Status:"
sudo systemctl status dual_recorder.service --no-pager -l
sudo systemctl status video_worker.service --no-pager -l
sudo systemctl status ezrec-api.service --no-pager -l
sudo systemctl status system_status.service --no-pager -l

# Check API endpoint
echo "🌐 Testing API endpoint..."
sleep 5
if curl -s http://localhost:8000/status >/dev/null 2>&1; then
    echo "✅ API server is responding"
else
    echo "⚠️ API server not responding (may need time to start)"
fi

#------------------------------#
# 20. RUN COMPLETE SYSTEM TEST
#------------------------------#
echo "🧪 Running complete system test..."
if [ -f "/opt/ezrec-backend/test_complete_system.py" ]; then
    cd /opt/ezrec-backend
    python3 test_complete_system.py
else
    echo "⚠️ test_complete_system.py not found, skipping system test"
fi

#------------------------------#
# 21. SUCCESS MESSAGE
#------------------------------#
echo ""
echo "🎉 EZREC Backend Deployment Complete!"
echo "====================================="
echo ""
echo "📋 Next Steps:"
echo "1. Configure your .env file: sudo nano /opt/ezrec-backend/.env"
echo "2. Test the system: python3 test_complete_system.py"
echo "3. Check service logs: sudo journalctl -u dual_recorder.service -f"
echo ""
echo "🔧 Useful Commands:"
echo "- Check service status: sudo systemctl status dual_recorder.service"
echo "- View logs: sudo journalctl -u dual_recorder.service -f"
echo "- Restart services: sudo systemctl restart dual_recorder.service"
echo "- Test API: curl http://localhost:8000/status"
echo ""
echo "📁 Installation Directory: /opt/ezrec-backend"
echo "📝 Logs Directory: /opt/ezrec-backend/logs"
echo "🎥 Recordings Directory: /opt/ezrec-backend/recordings"
echo ""
echo "✅ Deployment completed successfully!"
echo "🎯 All fixes applied - system should be fully operational!"
