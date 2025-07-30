#!/bin/bash

# Restart and verify all services
echo "🚀 Restarting and verifying all services..."

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Restart all services
echo "🔄 Restarting services..."
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service
sudo systemctl restart system_status.service

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
echo "=================="

SERVICES=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")

for service in "${SERVICES[@]}"; do
    echo ""
    echo "🔍 $service:"
    if systemctl is-active "$service" &>/dev/null; then
        echo "✅ $service is active"
    else
        echo "❌ $service is not active"
        echo "📝 Recent logs:"
        sudo journalctl -u "$service" -n 5 --no-pager
    fi
done

# Test API response
echo ""
echo "🌐 Testing API response..."
if curl -s http://localhost:8000/status >/dev/null 2>&1; then
    echo "✅ API server is responding"
    response=$(curl -s http://localhost:8000/status)
    echo "   Response: $response"
else
    echo "❌ API server not responding"
    echo "📝 API logs:"
    sudo journalctl -u ezrec-api.service -n 10 --no-pager
fi

echo ""
echo "🎉 Service restart completed!" 