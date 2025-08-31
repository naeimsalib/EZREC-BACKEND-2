#!/bin/bash

# EZREC Deployment Completion Script
# This script completes any interrupted deployment steps

set -e

DEPLOY_USER="michomanoly14892"
DEPLOY_PATH="/opt/ezrec-backend"

echo "🔧 Completing interrupted EZREC deployment..."

# Check if we're in the right directory
if [[ ! -d "$DEPLOY_PATH" ]]; then
    echo "❌ Deployment directory not found: $DEPLOY_PATH"
    exit 1
fi

cd "$DEPLOY_PATH"

# 1. Complete setup_files if needed
if [[ ! -f "status.json" ]]; then
    echo "🔄 Completing setup_files step..."
    
    # Create logs directory and files
    sudo mkdir -p logs
    sudo chown $DEPLOY_USER:$DEPLOY_USER logs
    sudo chmod 755 logs
    
    # Create log files
    sudo -u $DEPLOY_USER touch logs/dual_recorder.log
    sudo -u $DEPLOY_USER touch logs/video_worker.log
    sudo -u $DEPLOY_USER touch logs/ezrec-api.log
    sudo -u $DEPLOY_USER touch logs/system_status.log
    sudo chown $DEPLOY_USER:$DEPLOY_USER logs/*.log
    sudo chmod 644 logs/*.log
    
    # Create status file
    sudo -u $DEPLOY_USER tee status.json > /dev/null << EOF
{
  "is_recording": false,
  "last_update": "$(date -Iseconds)",
  "system_status": "deployed"
}
EOF
    sudo chown $DEPLOY_USER:$DEPLOY_USER status.json
    sudo chmod 664 status.json
    
    echo "✅ setup_files completed"
fi

# 2. Complete install_services if needed
if [[ ! -f "/etc/systemd/system/dual_recorder.service" ]]; then
    echo "🔄 Completing install_services step..."
    
    # Copy systemd services
    sudo cp systemd/*.service /etc/systemd/system/
    sudo cp systemd/*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    
    # Enable services
    sudo systemctl enable dual_recorder.service
    sudo systemctl enable video_worker.service
    sudo systemctl enable ezrec-api.service
    sudo systemctl enable system_status.service
    
    # Enable timers
    sudo systemctl enable system_status.timer
    
    echo "✅ install_services completed"
fi

# 3. Complete setup_cron if needed
if ! crontab -l 2>/dev/null | grep -q "ezrec-backend"; then
    echo "🔄 Completing setup_cron step..."
    
    # Add cleanup job to root crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * $DEPLOY_PATH/backend/cleanup_old_data.py > $DEPLOY_PATH/logs/cleanup.log 2>&1") | crontab -
    
    echo "✅ setup_cron completed"
fi

# 4. Start services
echo "🔄 Starting services..."
sudo systemctl start dual_recorder.service
sudo systemctl start video_worker.service
sudo systemctl start ezrec-api.service
sudo systemctl start system_status.service

# 5. Start timers
sudo systemctl start system_status.timer

echo "✅ All deployment steps completed!"
echo "📋 Service status:"
sudo systemctl status dual_recorder.service --no-pager -l | head -10
sudo systemctl status video_worker.service --no-pager -l | head -10
sudo systemctl status ezrec-api.service --no-pager -l | head -10
sudo systemctl status system_status.service --no-pager -l | head -10

echo "🎉 Deployment completed successfully!" 