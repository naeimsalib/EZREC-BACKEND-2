#!/bin/bash

echo "🔧 Comprehensive EZREC Fix Script"
echo "=================================="

# 1. Stop all services first
echo "🛑 Stopping all services..."
sudo systemctl stop dual_recorder.service 2>/dev/null || true
sudo systemctl stop video_worker.service 2>/dev/null || true
sudo systemctl stop ezrec-api.service 2>/dev/null || true
sudo systemctl stop system_status.service 2>/dev/null || true

# 2. Kill any remaining processes
echo "🔪 Killing remaining processes..."
sudo pkill -f "dual_recorder.py" 2>/dev/null || true
sudo pkill -f "video_worker.py" 2>/dev/null || true
sudo pkill -f "api_server.py" 2>/dev/null || true

# 3. Fix permissions and ownership
echo "🔐 Fixing permissions..."
sudo chown -R root:root /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 644 /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || true

# 4. Create missing directories
echo "📁 Creating missing directories..."
sudo mkdir -p /opt/ezrec-backend/logs
sudo mkdir -p /opt/ezrec-backend/recordings
sudo mkdir -p /opt/ezrec-backend/processed
sudo mkdir -p /opt/ezrec-backend/media_cache
sudo mkdir -p /opt/ezrec-backend/api/local_data
sudo mkdir -p /opt/ezrec-backend/backend

# 5. Fix Python path issues
echo "🐍 Fixing Python path issues..."
cd /opt/ezrec-backend
sudo touch backend/__init__.py
sudo touch api/__init__.py

# 6. Install missing dependencies
echo "📦 Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-picamera2 v4l-utils ffmpeg python3-requests

# 7. Fix systemd service files
echo "⚙️ Fixing systemd services..."

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

# 8. Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# 9. Test basic functionality
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

# 10. Start services
echo "🚀 Starting services..."
sudo systemctl enable dual_recorder.service
sudo systemctl enable video_worker.service
sudo systemctl enable ezrec-api.service

sudo systemctl start ezrec-api.service
sleep 3
sudo systemctl start video_worker.service
sleep 3
sudo systemctl start dual_recorder.service

# 11. Check service status
echo "📊 Service status:"
sudo systemctl status dual_recorder.service --no-pager -l
echo ""
sudo systemctl status video_worker.service --no-pager -l
echo ""
sudo systemctl status ezrec-api.service --no-pager -l

# 12. Test API endpoint
echo "🌐 Testing API endpoint..."
sleep 5
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is responding"
    curl -s http://localhost:8000/health | jq '.status, .warnings' 2>/dev/null || echo "API health check completed"
else
    echo "❌ API not responding"
fi

echo ""
echo "✅ Comprehensive fix completed!"
echo "📋 Next steps:"
echo "1. Run: sudo python3 test_system_readiness.py"
echo "2. If all tests pass, create a test booking"
echo "3. Monitor logs: sudo journalctl -u dual_recorder.service -f" 