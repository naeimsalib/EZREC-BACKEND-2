#!/bin/bash

# Quick fix script for EZREC Backend deployment
echo "🔧 Fixing EZREC Backend deployment..."

USER=$(whoami)
PROJECT_DIR="/opt/ezrec-backend"
SERVICE_NAME="ezrec-backend"

# Create project directory with correct ownership
echo "📁 Setting up project directory..."
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# Create subdirectories
mkdir -p $PROJECT_DIR/{temp,logs}

# Copy project files
echo "📄 Copying project files..."
cp *.py $PROJECT_DIR/ 2>/dev/null || true
cp requirements.txt $PROJECT_DIR/ 2>/dev/null || true
cp env.example $PROJECT_DIR/ 2>/dev/null || true

# Set permissions
chmod +x $PROJECT_DIR/*.py

# Setup Python virtual environment
# (removed venv setup)
# Install Python packages system-wide
pip3 install --upgrade pip --break-system-packages
pip3 install -r requirements.txt --break-system-packages

# Copy environment file if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp env.example .env
    echo "⚠️  Environment file created. Please edit $PROJECT_DIR/.env with your settings."
fi

# Update systemd service file with correct user
echo "⚙️  Installing systemd service..."
sed "s/User=pi/User=$USER/g; s/Group=pi/Group=$USER/g" ezrec-backend.service > /tmp/ezrec-backend.service
sudo cp /tmp/ezrec-backend.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# Setup camera permissions
echo "📹 Setting up camera permissions..."
sudo usermod -a -G video $USER

# Test camera
echo "🧪 Testing camera..."
if command -v libcamera-hello &> /dev/null; then
    if timeout 5 libcamera-hello --list-cameras &> /dev/null; then
        echo "✅ Camera detected successfully"
    else
        echo "⚠️  Camera not detected or not accessible"
    fi
fi

echo ""
echo "🎉 Deployment fixed! Next steps:"
echo "1. Edit environment: sudo nano $PROJECT_DIR/.env"
echo "2. Start service: sudo systemctl start $SERVICE_NAME"
echo "3. Check status: sudo systemctl status $SERVICE_NAME"
echo "4. View logs: sudo journalctl -u $SERVICE_NAME -f" 