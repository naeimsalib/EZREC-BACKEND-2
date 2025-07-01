#!/bin/bash

# Final Combined EZREC Deployment Script (Backend + FastAPI + Monitor + Cloudflared)

set -euo pipefail

#------------------------------#
# 0. ENV & ARG SETUP
#------------------------------#
USER="${1:-$(whoami)}"
TUNNEL_NAME="${2:-ezrec}"
PROJECT_DIR="/opt/ezrec-backend"
API_DIR="$PROJECT_DIR/api"
VENV_DIR="$API_DIR/venv"
SYSTEMD_DIR="/etc/systemd/system"
LOCK_FILE="/tmp/ezrec_deploy.lock"

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
  echo "🚫 Deployment already running. Remove $LOCK_FILE to retry."
  exit 1
fi
trap "rm -f \"$LOCK_FILE\"" EXIT
touch "$LOCK_FILE"

echo "🚀 Starting EZREC Deployment as user '$USER' with tunnel name '$TUNNEL_NAME'..."

#------------------------------#
# 3. CREATE FOLDERS + PERMISSIONS
#------------------------------#
echo "📁 Setting up directories..."
sudo mkdir -p "$API_DIR/local_data"
sudo chown -R "$USER:$USER" "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
chmod 700 "$API_DIR/local_data"

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
# 5. WRITE FastAPI + MONITOR
#------------------------------#
echo "📝 Writing FastAPI app..."
cat > "$API_DIR/api_server.py" <<EOF
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from datetime import datetime

app = FastAPI()

BOOKINGS_FILE = "/opt/ezrec-backend/api/local_data/bookings.json"
SETTINGS_FILE = "/opt/ezrec-backend/api/local_data/settings.json"

class Booking(BaseModel):
    id: str
    user_id: str
    camera_id: str
    start_time: str
    end_time: str
    title: Optional[str] = None

class SystemSettings(BaseModel):
    logo_paths: Optional[List[str]] = None
    intro_video_path: Optional[str] = None

@app.get("/status")
def get_status():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/bookings")
def get_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    with open(BOOKINGS_FILE, "r") as f:
        return json.load(f)

@app.post("/bookings")
def post_bookings(bookings: List[Booking]):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump([b.dict() for b in bookings], f)
    return {"message": "Bookings saved", "count": len(bookings)}

@app.delete("/bookings")
def delete_bookings():
    if os.path.exists(BOOKINGS_FILE):
        os.remove(BOOKINGS_FILE)
    return {"message": "Bookings deleted"}

@app.get("/recordings")
def get_recordings():
    recordings_dir = "/opt/ezrec-backend/recordings"
    results = []
    if not os.path.exists(recordings_dir):
        return results
    for date_dir in os.listdir(recordings_dir):
        full_dir = os.path.join(recordings_dir, date_dir)
        if os.path.isdir(full_dir):
            for file in os.listdir(full_dir):
                if file.endswith(".mp4"):
                    results.append({
                        "date": date_dir,
                        "filename": file
                    })
    return results

@app.post("/system")
def post_system_settings(settings: SystemSettings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.dict(), f)
    return {"message": "System settings saved"}
EOF

echo "📡 Writing system monitor..."
cat > "$API_DIR/monitor.py" <<EOF
import time
import psutil
import json
import os
from datetime import datetime

MONITOR_OUTPUT = "/opt/ezrec-backend/api/local_data/monitor.json"

def get_metrics():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict(),
        "uptime_sec": int(time.time() - psutil.boot_time())
    }

while True:
    metrics = get_metrics()
    with open(MONITOR_OUTPUT, "w") as f:
        json.dump(metrics, f)
    time.sleep(10)
EOF

#------------------------------#
# 6. SYSTEMD SERVICES
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

sudo tee "$SYSTEMD_DIR/ezrec-tunnel.service" > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel for EZREC
After=network-online.target

[Service]
ExecStart=/usr/bin/cloudflared tunnel run $TUNNEL_NAME
WorkingDirectory=$API_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

#------------------------------#
# 7. CLOUDFLARED INSTALL
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
# 7.5 INCREASE UDP BUFFER FOR CLOUDFLARED (RECOMMENDED FOR VIDEO/LIVE)
#------------------------------#
echo "🛠️  Increasing UDP buffer size for cloudflared (for video upload/live)..."
if ! grep -q "net.core.rmem_max = 7168000" /etc/sysctl.conf; then
  echo "net.core.rmem_max = 7168000" | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
else
  echo "✅ UDP buffer already configured"
fi

#------------------------------#
# 8. ENABLE + START SERVICES
#------------------------------#
echo "🔁 Enabling and starting services..."
sudo systemctl daemon-reload
for svc in ezrec-api ezrec-monitor ezrec-tunnel; do
  sudo systemctl enable "$svc"
  sudo systemctl restart "$svc"
done

#------------------------------#
# 9. DONE!
#------------------------------#
echo ""
echo "🎉 EZREC deployed successfully!"
echo "📡 API running:    http://<Pi-IP>:8000 or via Cloudflare Tunnel: $TUNNEL_NAME"
echo "🩺 Monitor service: logs at: sudo journalctl -u ezrec-monitor -f"
echo "🌐 Tunnel status:   sudo journalctl -u ezrec-tunnel -f"
echo "📝 API location:    $API_DIR/api_server.py"
echo "📁 Protected Data:  $API_DIR/local_data (chmod 700)"
