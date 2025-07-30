#!/bin/bash

# Fix directory permissions and ownership
echo "🔐 Fixing directory permissions and ownership..."

# Create required directories
sudo mkdir -p /opt/ezrec-backend/{logs,media_cache,api/local_data,events,recordings,processed,final,assets}

# Create required files
sudo touch /opt/ezrec-backend/api/local_data/bookings.json
sudo touch /opt/ezrec-backend/status.json

# Set ownership to ezrec user
sudo chown -R ezrec:ezrec /opt/ezrec-backend

# Set proper permissions
sudo chmod -R 755 /opt/ezrec-backend
sudo chmod 664 /opt/ezrec-backend/api/local_data/bookings.json
sudo chmod 664 /opt/ezrec-backend/status.json

# Ensure log files are writable
sudo touch /opt/ezrec-backend/logs/dual_recorder.log
sudo touch /opt/ezrec-backend/logs/video_worker.log
sudo touch /opt/ezrec-backend/logs/api_server.log
sudo chown ezrec:ezrec /opt/ezrec-backend/logs/*.log
sudo chmod 664 /opt/ezrec-backend/logs/*.log

echo "✅ Directory permissions and ownership fixed"
echo "🔍 Testing write permissions..."
sudo -u ezrec touch /opt/ezrec-backend/logs/test_write.log && echo "✅ Write permissions working" || echo "❌ Write permissions failed" 