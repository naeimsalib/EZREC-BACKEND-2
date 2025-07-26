#!/bin/bash

echo "🔧 Fixing deployment issues..."

# 1. Fix missing imports and dependencies
echo "📦 Installing missing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-picamera2 v4l-utils ffmpeg

# 2. Fix permissions
echo "🔐 Fixing permissions..."
sudo chown -R root:root /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/api/local_data/bookings.json

# 3. Create missing directories
echo "📁 Creating missing directories..."
sudo mkdir -p /opt/ezrec-backend/logs
sudo mkdir -p /opt/ezrec-backend/recordings
sudo mkdir -p /opt/ezrec-backend/processed
sudo mkdir -p /opt/ezrec-backend/media_cache
sudo mkdir -p /opt/ezrec-backend/api/local_data

# 4. Fix Python path issues
echo "🐍 Fixing Python path issues..."
cd /opt/ezrec-backend/backend

# Create __init__.py files if missing
sudo touch __init__.py
sudo touch ../api/__init__.py

# 5. Test camera health check with reduced output
echo "📷 Testing camera health check..."
sudo python3 camera_health_check.py --verbose 2>&1 | head -50

# 6. Check systemd services
echo "⚙️ Checking systemd services..."
sudo systemctl daemon-reload
sudo systemctl status dual_recorder.service
sudo systemctl status video_worker.service

# 7. Test API health endpoint
echo "🌐 Testing API health endpoint..."
curl -s http://localhost:8000/health | jq '.status, .warnings' 2>/dev/null || echo "API not responding"

# 8. Check camera devices
echo "📹 Checking camera devices..."
v4l2-ctl --list-devices | head -20

echo "✅ Fix script completed. Check the output above for any remaining issues." 