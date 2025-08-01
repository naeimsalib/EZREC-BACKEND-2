#!/bin/bash

set -e

echo "🚀 Starting EZREC backend deployment..."

# Define variables
CODE_DIR="/home/michomanoly14892/EZREC-BACKEND-2"
DEPLOY_DIR="/opt/ezrec-backend"
USER="michomanoly14892"

# Stop services
echo "🛑 Stopping all EZREC services..."
systemctl stop dual_recorder.service || true
systemctl stop video_worker.service || true
systemctl stop ezrec-api.service || true

# Create deployment dir if not exists
mkdir -p "$DEPLOY_DIR"

# Sync code
echo "📂 Syncing code from $CODE_DIR to $DEPLOY_DIR..."
rsync -av --exclude='venv' --delete "$CODE_DIR/" "$DEPLOY_DIR/"

# Set ownership and permissions
echo "🔐 Fixing permissions..."
chown -R $USER:$USER "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"

# Setup virtual environment
if [ ! -d "$DEPLOY_DIR/backend/venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$DEPLOY_DIR/backend/venv"
fi

echo "📦 Installing Python dependencies..."
source "$DEPLOY_DIR/backend/venv/bin/activate"
pip install --upgrade pip
pip install -r "$CODE_DIR/requirements.txt"
deactivate

# ----------------------------------------
# ✅ Deploy updated video_worker.py
# ----------------------------------------
echo "📦 Deploying updated video_worker.py..."
cp "$CODE_DIR/backend/video_worker.py" "$DEPLOY_DIR/backend/video_worker.py"
chown $USER:$USER "$DEPLOY_DIR/backend/video_worker.py"
chmod +x "$DEPLOY_DIR/backend/video_worker.py"

# Restart services
echo "🔁 Restarting services..."
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable dual_recorder.service
systemctl enable video_worker.service
systemctl enable ezrec-api.service
systemctl restart dual_recorder.service
systemctl restart video_worker.service
systemctl restart ezrec-api.service

echo "✅ Deployment complete."
