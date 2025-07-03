#!/bin/bash

# Final Combined EZREC Deployment Script (Backend + FastAPI + Monitor + Cloudflared)

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
required_cmds=("python3" "pip" "sudo" "systemctl" "curl")
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
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install fastapi uvicorn psutil requests boto3
sudo chown -R "$USER:$USER" "$VENV_DIR"

#------------------------------#
# 5. SKIP Writing FastAPI + MONITOR (Handled via rsync)
#------------------------------#
echo "📜 Skipping FastAPI and Monitor overwrite... (rsync will update from dev dir)"

#------------------------------#
# 5.5 SYNC PROJECT FILES
#------------------------------#
echo "📦 Syncing updated project files..."
DEV_DIR="/home/$USER/EZREC-BACKEND-2"
if [ -d "$DEV_DIR" ]; then
  rsync -av --exclude='venv' --exclude='.git' --exclude='__pycache__' "$DEV_DIR/" "$PROJECT_DIR/"
else
  echo "⚠️ Development directory not found: $DEV_DIR"
fi

#------------------------------#
# 6. FIX LOG FILE PERMISSIONS
#------------------------------#
echo "⚖️ Fixing log permissions..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER":"$USER" "$LOG_DIR"
chmod 755 "$LOG_DIR"

#------------------------------#
# 7. SYSTEMD SERVICES
#------------------------------#
echo "⚙️ Setting up systemd services..."

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

# Cloudflared systemd
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

#------------------------------#
# 8. CLOUDFLARED INSTALL
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
# 9. UDP BUFFER CONFIG
#------------------------------#
echo "🛠️ Increasing UDP buffer size for cloudflared..."
if ! grep -q "net.core.rmem_max = 7168000" /etc/sysctl.conf; then
  echo "net.core.rmem_max = 7168000" | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
else
  echo "✅ UDP buffer already configured"
fi

#------------------------------#
# 10. ENABLE + START SERVICES
#------------------------------#
echo "🔁 Enabling and starting services..."
sudo systemctl daemon-reload
for svc in ezrec-api ezrec-monitor cloudflared; do
  sudo systemctl enable "$svc"
  sudo systemctl restart "$svc"
done

#------------------------------#
# 11. DONE!
#------------------------------#
echo ""
echo "🎉 EZREC deployed successfully!"
echo "📡 API running:    http://<Pi-IP>:8000 or https://api.ezrec.org"
echo "🩺 Monitor logs:   sudo journalctl -u ezrec-monitor -f"
echo "🌐 Tunnel logs:    sudo journalctl -u cloudflared -f"
echo "📁 Project files:  $PROJECT_DIR"
echo "📁 API entry:      $API_DIR/api_server.py"
echo "📃 Logs dir:       $LOG_DIR"
