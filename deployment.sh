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
# Remove all files in /opt/ezrec-backend/recordings and subfolders
sudo find "$PROJECT_DIR/recordings" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' \) -delete 2>/dev/null || true
# Remove all files in /opt/ezrec-backend/processed and subfolders
sudo find "$PROJECT_DIR/processed" -type f \( -name '*.mp4' -o -name '*.json' -o -name '*.done' -o -name '*.lock' -o -name '*.completed' \) -delete 2>/dev/null || true
# Remove all files in /opt/ezrec-backend/media_cache and subfolders
sudo rm -rf "$PROJECT_DIR/media_cache"/* 2>/dev/null || true
# Remove pending uploads and health/status files
sudo rm -f "$PROJECT_DIR/pending_uploads.json" "$PROJECT_DIR/health_report.json" "$PROJECT_DIR/status.json"
# Remove all cache/state files in api/local_data
sudo rm -f "$API_DIR/local_data/bookings.json" "$API_DIR/local_data/status.json" "$API_DIR/local_data/system.json"
echo "✅ All recordings, processed videos, media cache, and state files cleaned."

#------------------------------#
# 2.7 REFRESH USER MEDIA CACHE #
#------------------------------#
echo "🔄 Refreshing user media cache for main user..."
USER_ID=$(grep '^USER_ID=' "$PROJECT_DIR/.env" | cut -d'=' -f2 | tr -d '"')
if [ -n "$USER_ID" ]; then
  export USER_ID
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/backend/refresh_user_media.py"
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
chmod 700 "$API_DIR/local_data"
sudo chmod 755 "$LOG_DIR"

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
echo "📦 Syncing updated project files..."
DEV_DIR="/home/$USER/EZREC-BACKEND-2"
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
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/backend/refresh_user_media.py"
else
  echo "⚠️ USER_ID not set in .env, skipping user media refresh."
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
User=$USER

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

# Recorder
sudo tee "$SYSTEMD_DIR/recorder.service" > /dev/null <<EOF
[Unit]
Description=EZREC Recorder
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

# Camera Streamer
sudo cp "$PROJECT_DIR/backend/camera_streamer.service" "$SYSTEMD_DIR/camera_streamer.service"

sudo systemctl daemon-reload
sudo systemctl enable camera_streamer.service
sudo systemctl restart camera_streamer.service
sudo systemctl status camera_streamer.service --no-pager

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
for svc in ezrec-api ezrec-monitor recorder video_worker cloudflared camera_streamer status_updater; do
  sudo systemctl enable "$svc"
  sudo systemctl restart "$svc"
  sleep 1
done

#------------------------------#
# 13. DONE!
#------------------------------#
echo ""
echo "🎉 EZREC deployed successfully!"
echo ""
echo "📡 API running:    http://<Pi-IP>:8000 or https://api.ezrec.org"
echo "🩺 Monitor logs:   sudo journalctl -u ezrec-monitor -f"
echo "📹 Recorder logs:  sudo journalctl -u recorder.service -f"
echo "🎞️ Video logs:     sudo journalctl -u video_worker.service -f"
echo "🌐 Tunnel logs:    sudo journalctl -u cloudflared -f"
echo "📁 Project files:  $PROJECT_DIR"
echo "📁 API entry:      $API_DIR/api_server.py"
echo "📃 Logs dir:       $LOG_DIR"
echo ""
echo "⚠️  IMPORTANT: Make sure to create and configure $PROJECT_DIR/.env file"
echo "    Use env.example as a template and add your credentials"

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
