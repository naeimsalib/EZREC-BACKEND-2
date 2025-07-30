#!/bin/bash

# Final fix for backend virtual environment libcamera import
echo "🔧 Final fix for backend virtual environment libcamera import..."

cd /opt/ezrec-backend/backend

# Remove existing venv completely
echo "🧹 Removing existing backend virtual environment..."
sudo rm -rf venv

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
sudo apt-get install -y python3-libcamera python3-picamera2 python3-opencv

# Install Python packages with specific versions
echo "📦 Installing Python packages..."
pip install -r /opt/ezrec-backend/requirements.txt

# Force reinstall picamera2 to ensure libcamera is linked
echo "📦 Force reinstalling picamera2..."
pip uninstall -y picamera2 || true
pip install --force-reinstall picamera2

# Test libcamera import in the venv
echo "🧪 Testing libcamera import in venv..."
if /opt/ezrec-backend/backend/venv/bin/python3 -c "import libcamera; print('✅ libcamera import successful')" 2>/dev/null; then
    echo "✅ libcamera import working in venv"
else
    echo "❌ libcamera import still failing, trying alternative approach..."
    
    # Try to link system libcamera to venv
    echo "🔗 Linking system libcamera to venv..."
    sudo ln -sf /usr/lib/python3/dist-packages/libcamera* /opt/ezrec-backend/backend/venv/lib/python3.11/site-packages/ 2>/dev/null || true
    
    # Test again
    if /opt/ezrec-backend/backend/venv/bin/python3 -c "import libcamera; print('✅ libcamera import successful after linking')" 2>/dev/null; then
        echo "✅ libcamera import working after linking"
    else
        echo "❌ libcamera import still failing"
    fi
fi

# Test picamera2 import
echo "🧪 Testing picamera2 import in venv..."
if /opt/ezrec-backend/backend/venv/bin/python3 -c "import picamera2; print('✅ picamera2 import successful')" 2>/dev/null; then
    echo "✅ picamera2 import working in venv"
else
    echo "❌ picamera2 import failing"
fi

# Set ownership for services
echo "🔐 Setting ownership for services..."
sudo chown -R ezrec:ezrec /opt/ezrec-backend/backend/venv

echo "✅ Backend virtual environment final fix completed" 