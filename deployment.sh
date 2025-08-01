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
pip install --upgrade "typing-extensions>=4.12.0"
pip install -r "$CODE_DIR/requirements.txt"
deactivate

# Ensure .env file exists
echo "🔧 Setting up environment file..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "⚠️ .env file not found, creating template..."
    cat > "$DEPLOY_DIR/.env" << 'EOF'
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket_name_here

# Application Configuration
RECORDING_DIR=/opt/ezrec-backend/recordings
PROCESSED_DIR=/opt/ezrec-backend/processed
ASSETS_DIR=/opt/ezrec-backend/assets
EOF
    echo "⚠️ Please update the .env file with your actual credentials"
fi

# Ensure required directories exist
echo "📁 Creating required directories..."
mkdir -p "$DEPLOY_DIR/recordings"
mkdir -p "$DEPLOY_DIR/processed"
mkdir -p "$DEPLOY_DIR/assets"
mkdir -p "$DEPLOY_DIR/backend/logs"

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

# Enable services
systemctl enable dual_recorder.service || true
systemctl enable video_worker.service || true
systemctl enable ezrec-api.service || true

# Restart services with error handling
echo "🔄 Restarting dual_recorder.service..."
if systemctl restart dual_recorder.service; then
    echo "✅ dual_recorder.service restarted successfully"
else
    echo "⚠️ dual_recorder.service restart failed, checking status..."
    systemctl status dual_recorder.service --no-pager -l
    echo "🔍 Checking dual_recorder logs..."
    journalctl -u dual_recorder.service -n 10 --no-pager
    echo "🔧 Attempting to fix dual_recorder service..."
    systemctl stop dual_recorder.service || true
    sleep 2
    systemctl start dual_recorder.service || true
    sleep 2
    if systemctl is-active dual_recorder.service; then
        echo "✅ dual_recorder.service is now active"
    else
        echo "❌ dual_recorder.service still failed to start"
    fi
fi

echo "🔄 Restarting video_worker.service..."
if systemctl restart video_worker.service; then
    echo "✅ video_worker.service restarted successfully"
else
    echo "⚠️ video_worker.service restart failed, checking status..."
    systemctl status video_worker.service --no-pager -l
fi

echo "🔄 Restarting ezrec-api.service..."
if systemctl restart ezrec-api.service; then
    echo "✅ ezrec-api.service restarted successfully"
else
    echo "⚠️ ezrec-api.service restart failed, checking status..."
    systemctl status ezrec-api.service --no-pager -l
fi

# Final status check
echo "📊 Final service status:"
systemctl is-active dual_recorder.service && echo "✅ dual_recorder: ACTIVE" || echo "❌ dual_recorder: FAILED"
systemctl is-active video_worker.service && echo "✅ video_worker: ACTIVE" || echo "❌ video_worker: FAILED"
systemctl is-active ezrec-api.service && echo "✅ ezrec-api: ACTIVE" || echo "❌ ezrec-api: FAILED"

echo "✅ Deployment complete."
