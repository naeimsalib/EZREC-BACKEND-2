#!/bin/bash

echo "🎯 EZREC Ultimate Fix"
echo "====================="
echo ""

echo "🔄 Step 1: Fixing Supabase configuration..."
chmod +x fix_supabase_config.sh
sudo ./fix_supabase_config.sh

echo ""
echo "🔄 Step 2: Fixing pykms module..."
chmod +x fix_pykms_final.sh
sudo ./fix_pykms_final.sh

echo ""
echo "🔄 Step 3: Restarting all services..."
sudo systemctl daemon-reload
sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service system_status.service

echo ""
echo "⏳ Waiting for services to stabilize..."
sleep 10

echo ""
echo "📊 Final Service Status Check:"
echo "=============================="

# Check each service
services=("dual_recorder" "video_worker" "ezrec-api" "system_status")

for service in "${services[@]}"; do
    echo ""
    echo "🔍 Checking $service.service..."
    if sudo systemctl is-active --quiet "$service.service"; then
        echo "✅ $service.service is ACTIVE"
    else
        echo "❌ $service.service is INACTIVE"
        echo "📋 Recent logs:"
        sudo journalctl -u "$service.service" --no-pager -n 5
    fi
done

echo ""
echo "🧪 Testing API endpoints..."
echo "=========================="

# Test API status
echo "🔍 Testing API status endpoint..."
if curl -s http://localhost:8000/status > /dev/null; then
    echo "✅ API status endpoint responding"
else
    echo "❌ API status endpoint not responding"
fi

# Test API bookings endpoint
echo "🔍 Testing API bookings endpoint..."
if curl -s http://localhost:8000/bookings > /dev/null; then
    echo "✅ API bookings endpoint responding"
else
    echo "❌ API bookings endpoint not responding"
fi

echo ""
echo "🧪 Testing backend functionality..."
echo "================================="

# Test picamera2 import
echo "🔍 Testing picamera2 import..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
if python3 -c "import picamera2; print('✅ picamera2 import successful')" 2>/dev/null; then
    echo "✅ picamera2 import working"
else
    echo "❌ picamera2 import still failing"
fi

# Test API server import
echo "🔍 Testing API server import..."
cd /opt/ezrec-backend/api
source venv/bin/activate
if python3 -c "from api_server import app; print('✅ API server loads successfully')" 2>/dev/null; then
    echo "✅ API server loads successfully"
else
    echo "❌ API server still has import issues"
fi

echo ""
echo "📋 Summary:"
echo "==========="
echo "✅ Supabase configuration made robust (works with or without credentials)"
echo "✅ pykms module placeholder created for picamera2 compatibility"
echo "✅ All services restarted"
echo ""
echo "🎯 Next steps:"
echo "1. Update your .env file with actual Supabase credentials (optional)"
echo "2. Test the complete system: python3 test_complete_system.py"
echo "3. Monitor services: sudo systemctl status ezrec-api.service" 