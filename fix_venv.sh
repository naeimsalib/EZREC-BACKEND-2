#!/bin/bash

# Fix Virtual Environment Issues
echo "🔧 Fixing Virtual Environment Issues"
echo "===================================="

# Get current user
CURRENT_USER=$(whoami)

# Fix ownership issues
echo "🔐 Fixing ownership issues..."
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/ezrec-backend

# Remove existing virtual environments
echo "🧹 Removing existing virtual environments..."
cd /opt/ezrec-backend/api
if [ -d "venv" ]; then
    rm -rf venv
fi

cd /opt/ezrec-backend/backend
if [ -d "venv" ]; then
    rm -rf venv
fi

# Create API virtual environment
echo "🐍 Creating API virtual environment..."
cd /opt/ezrec-backend/api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Create backend virtual environment
echo "🐍 Creating backend virtual environment..."
cd /opt/ezrec-backend/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r /opt/ezrec-backend/requirements.txt

# Set ownership for services
echo "🔐 Setting ownership for services..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend/venv
sudo chown -R ezrec:ezrec /opt/ezrec-backend/api/venv

# Create assets
echo "🎨 Creating assets..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
python3 create_assets.py

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service

# Check service status
echo "📊 Checking service status..."
sleep 3
sudo systemctl status dual_recorder.service --no-pager -l
sudo systemctl status video_worker.service --no-pager -l
sudo systemctl status ezrec-api.service --no-pager -l

echo "✅ Virtual environment fix completed!" 