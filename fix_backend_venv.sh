#!/bin/bash

# Fix backend virtual environment libcamera import issue
echo "🔧 Fixing backend virtual environment libcamera import..."

cd /opt/ezrec-backend/backend

# Remove existing venv
echo "🧹 Removing existing backend virtual environment..."
rm -rf venv

# Create new virtual environment
echo "📦 Creating new backend virtual environment..."
python3 -m venv venv

# Install dependencies
echo "📦 Installing backend dependencies..."
source venv/bin/activate
pip install --upgrade pip

# Install system packages first
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3-libcamera python3-picamera2

# Install Python packages
echo "📦 Installing Python packages..."
pip install -r /opt/ezrec-backend/requirements.txt

# Test libcamera import
echo "🧪 Testing libcamera import..."
python3 -c "import libcamera; print('✅ libcamera import successful')" || {
    echo "❌ libcamera import failed, trying alternative installation..."
    pip install --force-reinstall picamera2
    python3 -c "import libcamera; print('✅ libcamera import successful after reinstall')"
}

# Test picamera2 import
echo "🧪 Testing picamera2 import..."
python3 -c "import picamera2; print('✅ picamera2 import successful')" || {
    echo "❌ picamera2 import failed"
}

# Set ownership for services
echo "🔐 Setting ownership for services..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend/venv

echo "✅ Backend virtual environment fix completed" 