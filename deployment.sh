#!/bin/bash

# Final Combined EZREC Deployment Script (Backend + FastAPI + Monitor + Cloudflared + Recorder + Video Worker)
# 
# This script is designed to deploy EZREC Backend to a Raspberry Pi
# It does NOT modify the .env file - you must create and configure it manually using env.example as a template
# 
# Usage: ./deployment.sh [username] [tunnel_name]

set -euo pipefail

#------------------------------#
# 0. ENV & ARG SETUP
#------------------------------#
USER="${1:-$(whoami)}"
TUNNEL_NAME="${2:-ezrec-tunnel}"
PROJECT_DIR="/opt/ezrec-backend"
API_DIR="$PROJECT_DIR/api"
VENV_DIR="$API_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"
LOCK_FILE="/tmp/ezrec_deploy.lock"
LOG_DIR="$PROJECT_DIR/logs"
CLOUDFLARED_BIN="/usr/local/bin/cloudflared"

#------------------------------#
# 1. CHECK COMMANDS
#------------------------------#
required_cmds=("python3" "pip" "sudo" "systemctl" "curl" "aws")
for cmd in "${required_cmds[@]}"; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Missing required command: $cmd"
    exit 1
  fi
done

#------------------------------#
# 2. LOCK FOR SAFETY
#------------------------------#
if [ -f "$LOCK_FILE" ]; then
  echo "🛑 Deployment already running. Remove $LOCK_FILE to retry."
  exit 1
fi
trap "rm -f \"$LOCK_FILE\"" EXIT
touch "$LOCK_FILE"

echo "🚀 Starting EZREC Deployment as user '$USER' with tunnel name '$TUNNEL_NAME'..."

#------------------------------#
# 2.5 CLEANUP SYSTEM BEFORE DEPLOY
#------------------------------#
echo "🧹 Cleaning up old recordings, uploads, and logs..."
sudo rm -rf "$PROJECT_DIR/raw_recordings"/*
sudo rm -rf "$PROJECT_DIR/processed_recordings"/*
sudo rm -f "$PROJECT_DIR/pending_uploads.json"
sudo rm -f "$LOG_DIR/ezrec.log"

#------------------------------#
# 2.6 DEEP CLEANUP OF ALL DATA #
#------------------------------#
echo "🧹 Deep cleaning all recordings, processed videos, media cache, and state files..."

# Stop all EZREC services before cleanup
echo "🛑 Stopping all EZREC services for clean deployment..."
sudo systemctl stop recorder.service 2>/dev/null || true
sudo systemctl stop dual_recorder.service 2>/dev/null || true
sudo systemctl stop video_worker.service 2>/dev/null || true
sudo systemctl stop system_status.service 2>/dev/null || true
sudo systemctl stop log_collector.service 2>/dev/null || true
sudo systemctl stop health_api.service 2>/dev/null || true

# Kill any remaining Python processes that might be holding files
echo "🔪 Killing any remaining EZREC Python processes..."
sudo pkill -f "recorder.py" 2>/dev/null || true
sudo pkill -f "dual_recorder.py" 2>/dev/null || true
sudo pkill -f "video_worker.py" 2>/dev/null || true
sudo pkill -f "system_status.py" 2>/dev/null || true
sudo pkill -f "log_collector.py" 2>/dev/null || true
sudo pkill -f "health_api.py" 2>/dev/null || true

# Remove all files in /opt/ezrec-backend/recordings and subfolders
echo "🗑️ Removing all recordings and related files..."
sudo find "$PROJECT_DIR/recordings" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' -o -name '*.tmp' -o -name '*.partial' \) -delete 2>/dev/null || true

# Remove all files in /opt/ezrec-backend/processed and subfolders
echo "🗑️ Removing all processed videos..."
sudo find "$PROJECT_DIR/processed" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' -o -name '*.tmp' -o -name '*.partial' \) -delete 2>/dev/null || true

# Remove all files in /opt/ezrec-backend/media_cache and subfolders
echo "🗑️ Removing media cache..."
sudo rm -rf "$PROJECT_DIR/media_cache"/* 2>/dev/null || true

# Remove pending uploads and health/status files
echo "🗑️ Removing state files..."
sudo rm -f "$PROJECT_DIR/pending_uploads.json" "$PROJECT_DIR/health_report.json" "$PROJECT_DIR/status.json"
sudo rm -f "$PROJECT_DIR/failed_uploads.json" "$PROJECT_DIR/upload_retry.json"

# Remove all cache/state files in api/local_data
echo "🗑️ Removing API cache files..."
sudo rm -f "$API_DIR/local_data/bookings.json" "$API_DIR/local_data/status.json" "$API_DIR/local_data/system.json"

# Fix permissions for bookings.json file to prevent permission errors
echo "🔧 Fixing permissions for bookings.json file..."
sudo chown "$USER:$USER" "$API_DIR/local_data/bookings.json" 2>/dev/null || true
sudo chmod 644 "$API_DIR/local_data/bookings.json" 2>/dev/null || true

# Clean up any temporary files
echo "🗑️ Removing temporary files..."
sudo find "$PROJECT_DIR" -name "*.tmp" -delete 2>/dev/null || true
sudo find "$PROJECT_DIR" -name "*.partial" -delete 2>/dev/null || true
sudo find "$PROJECT_DIR" -name "*.lock" -delete 2>/dev/null || true

# Clean up log files (keep recent ones)
echo "🗑️ Cleaning old log files..."
sudo find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Reset any failed booking statuses in local cache
echo "🔄 Resetting booking cache..."
if [ -f "$API_DIR/local_data/bookings.json" ]; then
  sudo sed -i 's/"status": "Recording"/"status": "Scheduled"/g' "$API_DIR/local_data/bookings.json" 2>/dev/null || true
  sudo sed -i 's/"status": "Processing"/"status": "Scheduled"/g' "$API_DIR/local_data/bookings.json" 2>/dev/null || true
  sudo sed -i 's/"status": "RecordingFinished"/"status": "Scheduled"/g' "$API_DIR/local_data/bookings.json" 2>/dev/null || true
fi

echo "✅ All recordings, processed videos, media cache, and state files cleaned."
echo "✅ All EZREC services stopped and processes killed."

#------------------------------#
# 2.7 REFRESH USER MEDIA CACHE #
#------------------------------#
echo "🔄 Refreshing user media cache for main user..."
USER_ID=$(grep '^USER_ID=' "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d '"')
if [ -n "$USER_ID" ]; then
  export USER_ID
  # Use simplified refresh script to avoid logging permission issues
  # Note: This will be called again after file sync
  echo "⏳ User media refresh will be done after file sync..."
else
  echo "⚠️ USER_ID not set in .env, skipping user media refresh."
fi

#------------------------------#
# 3. CREATE FOLDERS + PERMISSIONS
#------------------------------#
echo "📁 Setting up directories..."
sudo mkdir -p "$API_DIR/local_data" "$LOG_DIR"
sudo chown -R "$USER:$USER" "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
sudo chmod 755 "$API_DIR/local_data"
sudo chmod 755 "$LOG_DIR"

# Ensure proper permissions for bookings.json file
echo "🔧 Setting up proper permissions for bookings.json..."
sudo touch "$API_DIR/local_data/bookings.json" 2>/dev/null || true
sudo chown "$USER:$USER" "$API_DIR/local_data/bookings.json"
sudo chmod 644 "$API_DIR/local_data/bookings.json"

#------------------------------#
# 4. CREATE VENV + INSTALL PYTHON DEPS
#------------------------------#
echo "🐍 Setting up virtual environment..."
rm -rf "$VENV_DIR"
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install fastapi uvicorn psutil requests boto3 python-dotenv pytz python-dateutil supabase
"$VENV_DIR/bin/pip" install 'pydantic[email]'
"$VENV_DIR/bin/pip" install opencv-python picamera2
sudo chown -R "$USER:$USER" "$VENV_DIR"

#------------------------------#
# 5. SYNC PROJECT FILES
#------------------------------#
DEV_DIR="/home/$USER/EZREC-BACKEND-2"
echo "[DEBUG] DEV_DIR=$DEV_DIR"
echo "[DEBUG] PROJECT_DIR=$PROJECT_DIR"
ls -l "$DEV_DIR/backend/refresh_user_media.py" || echo "[DEBUG] refresh_user_media.py not found in DEV_DIR/backend"
echo "\U0001F4E6 Syncing updated project files..."
if [ -d "$DEV_DIR" ]; then
  rsync -av --exclude='venv' --exclude='.git' --exclude='__pycache__' "$DEV_DIR/" "$PROJECT_DIR/"
else
  echo "⚠️ Development directory not found: $DEV_DIR"
fi

#------------------------------#
# 5.1 REFRESH USER MEDIA CACHE #
#------------------------------#
echo "🔄 Refreshing user media cache for main user..."
USER_ID=$(grep '^USER_ID=' "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d '"')
if [ -n "$USER_ID" ]; then
  export USER_ID
  # Use simplified refresh script to avoid logging permission issues
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/backend/refresh_user_media_simple.py"
else
  echo "⚠️ USER_ID not set in .env, skipping user media refresh."
fi

#------------------------------#
# 5.2 AUTOMATIC CAMERA DETECTION #
#------------------------------#
echo "📷 Detecting cameras automatically..."

# Function to detect camera serials
detect_camera_serials() {
  echo "🔍 Running camera detection..."
  
  # Check if libcamera-hello is available
  if ! command -v libcamera-hello &>/dev/null; then
    echo "⚠️ libcamera-hello not found, installing..."
    sudo apt-get update && sudo apt-get install -y libcamera-tools
  fi
  
  # Run camera detection
  CAMERA_OUTPUT=$(libcamera-hello --list-cameras 2>/dev/null || echo "")
  
  if [ -z "$CAMERA_OUTPUT" ]; then
    echo "❌ No cameras detected or libcamera-hello failed"
    return 1
  fi
  
  echo "📋 Camera detection output:"
  echo "$CAMERA_OUTPUT"
  
  # Extract serial numbers using regex
  SERIALS=($(echo "$CAMERA_OUTPUT" | grep -o 'i2c@[0-9a-f]*' | sed 's/i2c@//' | sort -u))
  
  if [ ${#SERIALS[@]} -eq 0 ]; then
    echo "❌ No camera serials found in output"
    return 1
  fi
  
  echo "✅ Found ${#SERIALS[@]} camera(s) with serials: ${SERIALS[*]}"
  
  # Set camera serials based on count
  if [ ${#SERIALS[@]} -eq 1 ]; then
    CAMERA_0_SERIAL="${SERIALS[0]}"
    CAMERA_1_SERIAL=""
    echo "📷 Single camera detected: $CAMERA_0_SERIAL"
  elif [ ${#SERIALS[@]} -eq 2 ]; then
    CAMERA_0_SERIAL="${SERIALS[0]}"
    CAMERA_1_SERIAL="${SERIALS[1]}"
    echo "📷 Dual cameras detected: $CAMERA_0_SERIAL, $CAMERA_1_SERIAL"
  else
    echo "⚠️ More than 2 cameras detected, using first two: ${SERIALS[0]}, ${SERIALS[1]}"
    CAMERA_0_SERIAL="${SERIALS[0]}"
    CAMERA_1_SERIAL="${SERIALS[1]}"
  fi
  
  return 0
}

# Detect cameras
if detect_camera_serials; then
  echo "✅ Camera detection successful"
  
  # Update .env file with detected camera serials
  if [ -f "$PROJECT_DIR/.env" ]; then
    echo "📝 Updating .env file with detected camera serials..."
    
    # Update or add CAMERA_0_SERIAL
    if grep -q "^CAMERA_0_SERIAL=" "$PROJECT_DIR/.env"; then
      sed -i "s/^CAMERA_0_SERIAL=.*/CAMERA_0_SERIAL=$CAMERA_0_SERIAL/" "$PROJECT_DIR/.env"
    else
      echo "CAMERA_0_SERIAL=$CAMERA_0_SERIAL" >> "$PROJECT_DIR/.env"
    fi
    
    # Update or add CAMERA_1_SERIAL (only if dual camera detected)
    if [ -n "$CAMERA_1_SERIAL" ]; then
      if grep -q "^CAMERA_1_SERIAL=" "$PROJECT_DIR/.env"; then
        sed -i "s/^CAMERA_1_SERIAL=.*/CAMERA_1_SERIAL=$CAMERA_1_SERIAL/" "$PROJECT_DIR/.env"
      else
        echo "CAMERA_1_SERIAL=$CAMERA_1_SERIAL" >> "$PROJECT_DIR/.env"
      fi
      
      # Set dual camera mode
      if grep -q "^DUAL_CAMERA_MODE=" "$PROJECT_DIR/.env"; then
        sed -i "s/^DUAL_CAMERA_MODE=.*/DUAL_CAMERA_MODE=true/" "$PROJECT_DIR/.env"
      else
        echo "DUAL_CAMERA_MODE=true" >> "$PROJECT_DIR/.env"
      fi
      
      # Set merge method
      if grep -q "^MERGE_METHOD=" "$PROJECT_DIR/.env"; then
        sed -i "s/^MERGE_METHOD=.*/MERGE_METHOD=side_by_side/" "$PROJECT_DIR/.env"
      else
        echo "MERGE_METHOD=side_by_side" >> "$PROJECT_DIR/.env"
      fi
      
      echo "✅ Dual camera mode enabled with merge method: side_by_side"
    else
      # Single camera mode
      if grep -q "^DUAL_CAMERA_MODE=" "$PROJECT_DIR/.env"; then
        sed -i "s/^DUAL_CAMERA_MODE=.*/DUAL_CAMERA_MODE=false/" "$PROJECT_DIR/.env"
      else
        echo "DUAL_CAMERA_MODE=false" >> "$PROJECT_DIR/.env"
      fi
      echo "✅ Single camera mode enabled"
    fi
    
    echo "📝 Camera configuration updated in .env file"
  else
    echo "⚠️ .env file not found, camera serials not updated"
  fi
else
  echo "⚠️ Camera detection failed, using default values"
  CAMERA_0_SERIAL="88000"
  CAMERA_1_SERIAL="80000"
fi

#------------------------------#
# 5.5. DOWNLOAD MAIN EZREC LOGO #
#------------------------------#
# Temporarily export AWS credentials for S3 download
set -a
source "$PROJECT_DIR/.env"
set +a

# Download main EZREC logo
echo "🖼️ Downloading main EZREC logo from S3..."
aws s3 cp s3://ezrec-user-media/main_ezrec_logo.png /opt/ezrec-backend/main_ezrec_logo.png || { echo "❌ Failed to download main EZREC logo from S3"; 
  # Unset AWS credentials for security
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN
  exit 1; }

# Unset AWS credentials for security
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN

#------------------------------#
# 6. INSTALL BACKEND DEPENDENCIES
#------------------------------#
echo "📦 Installing backend requirements.txt dependencies..."
REQS_FILE="/home/$USER/EZREC-BACKEND-2/requirements.txt"
if [ -f "$REQS_FILE" ]; then
  "$VENV_DIR/bin/pip" install -r "$REQS_FILE"
else
  echo "⚠️ Warning: requirements.txt not found at $REQS_FILE"
fi

#------------------------------#
# 7. FIX LOG FILE PERMISSIONS
#------------------------------#
echo "⚖️ Fixing log permissions..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER:$USER" "$LOG_DIR"
chmod 755 "$LOG_DIR"

#------------------------------#
# 8. SYSTEMD SERVICES
#------------------------------#
echo "⚙️ Setting up systemd services..."

# FastAPI
sudo tee "$SYSTEMD_DIR/ezrec-api.service" > /dev/null <<EOF
[Unit]
Description=EZREC FastAPI Backend
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
WorkingDirectory=$API_DIR
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Monitor
sudo tee "$SYSTEMD_DIR/ezrec-monitor.service" > /dev/null <<EOF
[Unit]
Description=EZREC System Monitor
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 monitor.py
WorkingDirectory=$API_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Single Camera Recorder (legacy)
sudo tee "$SYSTEMD_DIR/recorder.service" > /dev/null <<EOF
[Unit]
Description=EZREC Single Camera Recorder
After=network.target

[Service]
Type=simple
User=$USER
Group=video
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/bash -c 'for dev in /dev/video*; do fuser -k "\$dev" || true; done'
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/recorder.py
Restart=on-failure
RestartSec=5
PrivateDevices=no

[Install]
WantedBy=multi-user.target
EOF

# Dual Camera Recorder (new)
sudo tee "$SYSTEMD_DIR/dual_recorder.service" > /dev/null <<EOF
[Unit]
Description=EZREC Dual Camera Recorder
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=video
WorkingDirectory=$PROJECT_DIR/backend
Environment=PYTHONPATH=$PROJECT_DIR/backend:$PROJECT_DIR/api
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/dual_recorder.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Camera device access
ExecStartPre=/bin/bash -c 'for dev in /dev/video*; do fuser -k "\$dev" 2>/dev/null || true; done'
ExecStartPre=/bin/sleep 2

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR/recordings $LOG_DIR $API_DIR/local_data $PROJECT_DIR/status.json

[Install]
WantedBy=multi-user.target
EOF

# Video Worker
sudo tee "$SYSTEMD_DIR/video_worker.service" > /dev/null <<EOF
[Unit]
Description=EZREC Video Processor
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/video_worker.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# System Status
sudo tee "$SYSTEMD_DIR/system_status.service" > /dev/null <<EOF
[Unit]
Description=EZREC System Status Service
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/system_status.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Log Collector
sudo tee "$SYSTEMD_DIR/log_collector.service" > /dev/null <<EOF
[Unit]
Description=EZREC Log Collector Service
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/log_collector.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Health API
sudo tee "$SYSTEMD_DIR/health_api.service" > /dev/null <<EOF
[Unit]
Description=EZREC Health API Service
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/backend/health_api.py
WorkingDirectory=$PROJECT_DIR/backend
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Cloudflared
sudo tee "$SYSTEMD_DIR/cloudflared.service" > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network-online.target
Wants=network-online.target

[Service]
TimeoutStartSec=0
Type=simple
ExecStart=$CLOUDFLARED_BIN tunnel run $TUNNEL_NAME
Restart=on-failure
RestartSec=5s
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Status Updater
"$VENV_DIR/bin/pip" install psutil
# Ensure status_updater.py is present
if [ -f "$DEV_DIR/backend/status_updater.py" ]; then
  cp "$DEV_DIR/backend/status_updater.py" "$PROJECT_DIR/status_updater.py"
  echo "✅ Copied status_updater.py to $PROJECT_DIR"
else
  echo "❌ status_updater.py not found in $DEV_DIR/backend. Please check your source."
fi
# Create systemd service for status updater
sudo tee "$SYSTEMD_DIR/status_updater.service" > /dev/null <<EOF
[Unit]
Description=EZREC System Status Updater
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/status_updater.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF
# Enable and start the status updater service
sudo systemctl daemon-reload
sudo systemctl enable status_updater.service
sudo systemctl restart status_updater.service
sudo systemctl status status_updater.service --no-pager

#------------------------------#
# 9. CLOUDFLARED INSTALL
#------------------------------#
if ! command -v cloudflared &>/dev/null; then
  echo "📦 Installing cloudflared..."
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /etc/apt/trusted.gpg.d/cloudflare-main.gpg >/dev/null
  echo "deb [signed-by=/etc/apt/trusted.gpg.d/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared stable main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
  sudo apt-get update && sudo apt-get install -y cloudflared
else
  echo "✅ cloudflared is already installed"
fi

#------------------------------#
# 10. UDP BUFFER CONFIG
#------------------------------#
echo "🛠️ Increasing UDP buffer size for cloudflared..."
if ! grep -q "net.core.rmem_max = 7168000" /etc/sysctl.conf; then
  echo "net.core.rmem_max = 7168000" | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
else
  echo "✅ UDP buffer already configured"
fi

#------------------------------#
# 11. CHECK FOR .ENV FILE
#------------------------------#
if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "⚠️  WARNING: .env file not found at $PROJECT_DIR/.env"
  echo "    Please create it using env.example as a template before starting services"
  echo "    Services will be enabled but may fail to start without proper configuration"
fi

#------------------------------#
# 12. ENABLE + START SERVICES
#------------------------------#
echo "🔁 Enabling and starting services..."
sudo systemctl daemon-reload

# Determine which recorder service to start based on camera configuration
if [ -f "$PROJECT_DIR/.env" ] && grep -q "^DUAL_CAMERA_MODE=true" "$PROJECT_DIR/.env"; then
  echo "🎬 Starting dual camera recorder..."
  RECORDER_SERVICE="dual_recorder"
  # Disable single camera recorder
  sudo systemctl disable recorder.service 2>/dev/null || true
else
  echo "📷 Starting single camera recorder..."
  RECORDER_SERVICE="recorder"
  # Disable dual camera recorder
  sudo systemctl disable dual_recorder.service 2>/dev/null || true
fi

# Start services in the correct order
echo "🚀 Starting EZREC services..."
for svc in system_status log_collector health_api $RECORDER_SERVICE video_worker; do
  echo "Starting $svc.service..."
  sudo systemctl enable "$svc.service"
  sudo systemctl start "$svc.service"
  sleep 2
  
  # Check if service started successfully
  if sudo systemctl is-active --quiet "$svc.service"; then
    echo "✅ $svc.service started successfully"
  else
    echo "❌ $svc.service failed to start"
    sudo systemctl status "$svc.service" --no-pager -l
  fi
done

# Start cloudflared tunnel
echo "🌐 Starting cloudflared tunnel..."
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sleep 2

if sudo systemctl is-active --quiet cloudflared; then
  echo "✅ cloudflared started successfully"
else
  echo "❌ cloudflared failed to start"
  sudo systemctl status cloudflared --no-pager -l
fi

#------------------------------#
# 12.5 FINAL PERMISSION FIXES #
#------------------------------#
echo "🔧 Applying final permission fixes..."
# Change ownership to root for API service compatibility
sudo chown -R root:root "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
sudo chmod 755 "$API_DIR/local_data"

# Ensure bookings.json exists and has proper content
if [ ! -f "$API_DIR/local_data/bookings.json" ]; then
  echo "📝 Creating bookings.json file..."
  echo '[]' | sudo tee "$API_DIR/local_data/bookings.json" > /dev/null
fi

# Set proper permissions for bookings.json
sudo chown root:root "$API_DIR/local_data/bookings.json"
sudo chmod 644 "$API_DIR/local_data/bookings.json"

# Verify the file is writable
if [ -w "$API_DIR/local_data/bookings.json" ]; then
  echo "✅ bookings.json is writable by root"
else
  echo "❌ bookings.json is not writable by root"
  sudo chmod 666 "$API_DIR/local_data/bookings.json"
  echo "🔧 Temporarily set permissions to 666 for debugging"
fi

# Start the API service
echo "🚀 Starting API service..."
sudo systemctl enable ezrec-api.service
sudo systemctl start ezrec-api.service
sleep 3

if sudo systemctl is-active --quiet ezrec-api.service; then
  echo "✅ ezrec-api.service started successfully"
  
  # Test API write permissions
  echo "🧪 Testing API write permissions..."
  sleep 2
  if curl -s http://localhost:8000/status > /dev/null; then
    echo "✅ API is responding correctly"
    
    # Test creating a temporary booking to verify write permissions
    TEST_BOOKING='[{"id":"test-perm-001","user_id":"test-user","start_time":"2025-01-01T00:00:00Z","end_time":"2025-01-01T00:01:00Z","date":"2025-01-01","camera_id":"test-cam","booking_id":"test-perm-001"}]'
    if curl -s -X POST http://localhost:8000/bookings \
       -H "Content-Type: application/json" \
       -d "$TEST_BOOKING" > /dev/null; then
      echo "✅ API can write to bookings.json successfully"
      
      # Clean up test booking
      curl -s -X DELETE http://localhost:8000/bookings/test-perm-001 > /dev/null
    else
      echo "⚠️ API write test failed - check permissions manually"
    fi
  else
    echo "⚠️ API is not responding - check service status"
  fi
else
  echo "❌ ezrec-api.service failed to start"
  sudo systemctl status ezrec-api.service --no-pager -l
fi

#------------------------------#
# 13. DONE!
#------------------------------#
echo ""
echo "🎉 EZREC deployed successfully!"
echo ""
echo "📡 API running:    http://<Pi-IP>:8000 or https://api.ezrec.org"
echo "🩺 Monitor logs:   sudo journalctl -u ezrec-monitor -f"
if [ "$RECORDER_SERVICE" = "dual_recorder" ]; then
  echo "📹 Dual recorder logs: sudo journalctl -u dual_recorder.service -f"
else
  echo "📹 Recorder logs:  sudo journalctl -u recorder.service -f"
fi
echo "🎞️ Video logs:     sudo journalctl -u video_worker.service -f"
echo "🌐 Tunnel logs:    sudo journalctl -u cloudflared -f"
echo "📁 Project files:  $PROJECT_DIR"
echo "📁 API entry:      $API_DIR/api_server.py"
echo "📃 Logs dir:       $LOG_DIR"
echo ""

# Show camera configuration
if [ -f "$PROJECT_DIR/.env" ]; then
  echo "📷 Camera Configuration:"
  if grep -q "^DUAL_CAMERA_MODE=true" "$PROJECT_DIR/.env"; then
    echo "   Mode: Dual Camera"
    echo "   Camera 0 Serial: $(grep '^CAMERA_0_SERIAL=' "$PROJECT_DIR/.env" | cut -d'=' -f2)"
    echo "   Camera 1 Serial: $(grep '^CAMERA_1_SERIAL=' "$PROJECT_DIR/.env" | cut -d'=' -f2)"
    echo "   Merge Method: $(grep '^MERGE_METHOD=' "$PROJECT_DIR/.env" | cut -d'=' -f2)"
  else
    echo "   Mode: Single Camera"
    echo "   Camera Serial: $(grep '^CAMERA_0_SERIAL=' "$PROJECT_DIR/.env" | cut -d'=' -f2)"
  fi
fi

echo ""
echo "⚠️  IMPORTANT: Make sure to create and configure $PROJECT_DIR/.env file"
echo "    Use env.example as a template and add your credentials"

#------------------------------#
# 15. NEXT STEPS & TROUBLESHOOTING
#------------------------------#
echo ""
echo "🚀 NEXT STEPS AFTER DEPLOYMENT:"
echo "================================"
echo ""
echo "1. 📝 CREATE TEST BOOKING:"
echo "   echo '[\"id\": \"test-001\", \"start_time\": \"$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")\", \"end_time\": \"$(date -u -d \"+5 minutes\" +\"%Y-%m-%dT%H:%M:%SZ\")\", \"status\": \"active\", \"user_id\": \"YOUR_USER_ID\", \"camera_id\": \"YOUR_CAMERA_ID\"}]' | sudo tee $API_DIR/local_data/bookings.json"
echo ""
echo "2. 📊 MONITOR SERVICES:"
echo "   sudo journalctl -u dual_recorder.service -f    # Watch dual camera recording"
echo "   sudo journalctl -u video_worker.service -f     # Watch video processing"
echo "   sudo journalctl -u system_status.service -f    # Watch system status"
echo ""
echo "3. 🔧 TROUBLESHOOTING COMMANDS:"
echo "   sudo systemctl status dual_recorder.service     # Check service status"
echo "   sudo systemctl restart dual_recorder.service    # Restart if needed"
echo "   ls -la $PROJECT_DIR/recordings/$(date +%Y-%m-%d)/  # Check recordings"
echo "   vcgencmd measure_temp                           # Check temperature"
echo "   df -h                                           # Check disk space"
echo ""
echo "4. 📷 CAMERA TESTING:"
echo "   cd $PROJECT_DIR/backend"
echo "   python3 detect_cameras.py                       # Test camera detection"
echo "   python3 test_dual_camera.py                     # Test dual camera setup"
echo ""
echo "5. 🌐 NETWORK TESTING:"
echo "   curl http://localhost:8000/status               # Test API locally"
echo "   curl https://api.ezrec.org/status              # Test API via tunnel"
echo "   sudo systemctl status ezrec-api.service        # Check API service status"
echo ""
echo "6. 📁 CHECK FILES:"
echo "   ls -la $API_DIR/local_data/                    # Check booking cache"
echo "   ls -la $PROJECT_DIR/recordings/                # Check recordings"
echo "   ls -la $LOG_DIR/                               # Check logs"
echo ""
echo "7. 🔄 PERMISSION FIXES (if needed):"
echo "   # Permissions are now automatically fixed during deployment"
echo "   # If issues persist, check: sudo journalctl -u ezrec-api.service -n 20"
echo ""
echo "8. 📊 SYSTEM MONITORING:"
echo "   htop                                           # Monitor system resources"
echo "   sudo journalctl -f                             # Monitor all logs"
echo "   sudo systemctl list-units --type=service | grep ezrec  # List all EZREC services"
echo ""
echo "✅ Your dual camera EZREC system is now ready for production use!"
echo "🎬 Both cameras will record simultaneously and merge into one video"
echo "📡 Videos will be automatically processed and uploaded to S3"
echo "🌐 API is available at https://api.ezrec.org"

#------------------------------#
# 14. CLOUDFLARED CONFIG
#------------------------------#
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}' | head -n1)
CLOUDFLARED_CREDS="/etc/cloudflared/${TUNNEL_ID}.json"
CLOUDFLARED_CONFIG="/etc/cloudflared/config.yml"

# Always write the correct config for main API on port 8000
# WARNING: This will overwrite /etc/cloudflared/config.yml
sudo tee "$CLOUDFLARED_CONFIG" > /dev/null <<EOF
tunnel: $TUNNEL_NAME
credentials-file: $CLOUDFLARED_CREDS

ingress:
  - hostname: api.ezrec.org
    service: http://localhost:8000
  - service: http_status:404
EOF

sudo systemctl restart cloudflared

# To change video/camera resolution, set RESOLUTION in your .env file (e.g. RESOLUTION=1280x720)

# After deployment, print the encoder being used:
if [ -f "$PROJECT_DIR/.env" ]; then
  ENCODER=$(grep '^VIDEO_ENCODER=' "$PROJECT_DIR/.env" | cut -d'=' -f2)
  echo "\n🎥 Video encoder set to: ${ENCODER:-h264_v4l2m2m} (see .env)"
fi

# Ensure main_ezrec_logo.png is present and correctly named
MAIN_LOGO_PATH="$PROJECT_DIR/main_ezrec_logo.png"
ALT_LOGO_PATH="$PROJECT_DIR/main_logo.png"
if [ ! -f "$MAIN_LOGO_PATH" ]; then
  if [ -f "$ALT_LOGO_PATH" ]; then
    echo "Renaming $ALT_LOGO_PATH to $MAIN_LOGO_PATH..."
    mv "$ALT_LOGO_PATH" "$MAIN_LOGO_PATH"
  else
    echo "⬇️ Downloading main_ezrec_logo.png from S3..."
    set -a
    source "$PROJECT_DIR/.env"
    set +a
    aws s3 cp "s3://ezrec-user-media/main_ezrec_logo.png" "$MAIN_LOGO_PATH"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION AWS_SESSION_TOKEN
    if [ ! -f "$MAIN_LOGO_PATH" ]; then
      echo "❌ Failed to download main_ezrec_logo.png from S3. Please check your AWS credentials and bucket."
      exit 1
    fi
  fi
else
  echo "✅ main_ezrec_logo.png already present."
fi
