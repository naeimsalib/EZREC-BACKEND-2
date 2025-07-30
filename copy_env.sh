#!/bin/bash

# Copy .env file to the correct location
echo "📁 Copying .env file to /opt/ezrec-backend/.env"

# Check if .env exists in current directory
if [ -f ".env" ]; then
    echo "✅ Found .env file in current directory"
    sudo cp .env /opt/ezrec-backend/.env
    sudo chown ezrec:ezrec /opt/ezrec-backend/.env
    sudo chmod 644 /opt/ezrec-backend/.env
    echo "✅ .env file copied successfully"
else
    echo "❌ .env file not found in current directory"
    echo "Please make sure you have a .env file in the project directory"
    exit 1
fi

echo "🔧 Restarting services to pick up new .env file..."
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service

echo "✅ Done! Services restarted with new .env file" 