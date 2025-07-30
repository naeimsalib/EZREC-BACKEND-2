#!/bin/bash

# Comprehensive EZREC Fix Script
# Fixes all issues found in the deployment logs

set -e

echo "🔧 EZREC Comprehensive Fix Script"
echo "================================="

# Get current user
CURRENT_USER=$(whoami)

echo "👤 Current user: $CURRENT_USER"

#------------------------------#
# 1. STOP ALL SERVICES
#------------------------------#
echo "🛑 Stopping all services..."
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
# 2. FIX OWNERSHIP AND PERMISSIONS
#------------------------------#
echo "🔐 Fixing ownership and permissions..."

# Set ownership to current user for all operations
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/ezrec-backend

# Set proper permissions
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/.env 2>/dev/null || true

#------------------------------#
# 3. REMOVE AND RECREATE VIRTUAL ENVIRONMENTS
#------------------------------#
echo "🐍 Removing existing virtual environments..."

# Remove API venv
cd /opt/ezrec-backend/api
if [ -d "venv" ]; then
    echo "🧹 Removing API virtual environment..."
    rm -rf venv
fi

# Remove backend venv
cd /opt/ezrec-backend/backend
if [ -d "venv" ]; then
    echo "🧹 Removing backend virtual environment..."
    rm -rf venv
fi

#------------------------------#
# 4. CREATE API VIRTUAL ENVIRONMENT
#------------------------------#
echo "🐍 Creating API virtual environment..."
cd /opt/ezrec-backend/api

# Create new virtual environment
echo "📦 Creating API virtual environment..."
python3 -m venv venv

# Install dependencies
echo "📦 Installing API dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Test API imports
echo "🧪 Testing API imports..."
python3 -c "import fastapi, uvicorn, supabase; print('✅ API imports successful')" || {
    echo "❌ API imports failed, trying alternative installation..."
    pip install fastapi==0.116.1 uvicorn==0.35.0 supabase==2.16.0
    python3 -c "import fastapi, uvicorn, supabase; print('✅ API imports successful after retry')"
}

#------------------------------#
# 5. CREATE BACKEND VIRTUAL ENVIRONMENT
#------------------------------#
echo "🐍 Creating backend virtual environment..."
cd /opt/ezrec-backend/backend

# Create new virtual environment
echo "📦 Creating backend virtual environment..."
python3 -m venv venv

# Install dependencies
echo "📦 Installing backend dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Test backend imports
echo "🧪 Testing backend imports..."
python3 -c "import psutil, boto3; print('✅ Backend imports successful')" || {
    echo "❌ Backend imports failed, trying alternative installation..."
    pip install psutil==5.9.5 boto3==1.39.14
    python3 -c "import psutil, boto3; print('✅ Backend imports successful after retry')"
}

#------------------------------#
# 6. SET OWNERSHIP FOR SERVICES
#------------------------------#
echo "🔐 Setting ownership for services..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend/venv
sudo chown -R ezrec:ezrec /opt/ezrec-backend/api/venv

#------------------------------#
# 7. CREATE ASSETS
#------------------------------#
echo "🎨 Creating assets..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
python3 create_assets.py

#------------------------------#
# 8. FIX SERVICE FILES
#------------------------------#
echo "⚙️ Fixing service files..."

# Update dual_recorder service
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

# Update video_worker service
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

# Update ezrec-api service
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

#------------------------------#
# 9. RELOAD SYSTEMD
#------------------------------#
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

#------------------------------#
# 10. RESET FAILED SERVICES
#------------------------------#
echo "🔄 Resetting failed services..."
sudo systemctl reset-failed

#------------------------------#
# 11. ENABLE SERVICES
#------------------------------#
echo "🚀 Enabling services..."
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service

#------------------------------#
# 12. START SERVICES
#------------------------------#
echo "🚀 Starting services..."
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service

#------------------------------#
# 13. WAIT AND CHECK STATUS
#------------------------------#
echo "⏳ Waiting for services to start..."
sleep 10

echo "📊 Service Status:"
sudo systemctl status dual_recorder.service --no-pager -l
sudo systemctl status video_worker.service --no-pager -l
sudo systemctl status ezrec-api.service --no-pager -l

#------------------------------#
# 14. TEST API
#------------------------------#
echo "🌐 Testing API..."
sleep 5

if curl -s http://localhost:8000/status >/dev/null 2>&1; then
    echo "✅ API server is responding"
else
    echo "⚠️ API server not responding, checking logs..."
    sudo journalctl -u ezrec-api.service -n 20 --no-pager
fi

#------------------------------#
# 15. FINAL VERIFICATION
#------------------------------#
echo "🎯 Final verification..."

# Check virtual environments
echo "🐍 Virtual Environment Check:"
ls -la /opt/ezrec-backend/api/venv/bin/python3
ls -la /opt/ezrec-backend/backend/venv/bin/python3

# Check service files
echo "⚙️ Service File Check:"
ls -la /etc/systemd/system/dual_recorder.service
ls -la /etc/systemd/system/video_worker.service
ls -la /etc/systemd/system/ezrec-api.service

# Check assets
echo "🎨 Assets Check:"
ls -la /opt/ezrec-backend/assets/

echo ""
echo "🎉 Comprehensive fix completed!"
echo "📋 Next steps:"
echo "1. Test the API: curl http://localhost:8000/status"
echo "2. Run complete test: python3 test_complete_system.py"
echo "3. Check logs: sudo journalctl -u ezrec-api.service -f" 