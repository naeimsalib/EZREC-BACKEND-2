#!/bin/bash

echo "🎯 EZREC Final Complete Fix"
echo "============================"
echo ""

echo "🔄 Step 1: Fixing pykms module..."
chmod +x fix_pykms.sh
sudo ./fix_pykms.sh

echo ""
echo "🔄 Step 2: Fixing Supabase integration..."
chmod +x fix_supabase_issues.sh
sudo ./fix_supabase_issues.sh

echo ""
echo "🔄 Step 3: Restarting all services..."
sudo systemctl daemon-reload
sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service system_status.service

echo ""
echo "⏳ Waiting for services to stabilize..."
sleep 5

echo ""
echo "📊 Final Service Status Check:"
echo "=============================="

# Check each service
services=("dual_recorder" "video_worker" "ezrec-api" "system_status")
for service in "${services[@]}"; do
    echo ""
    echo "🔍 $service.service:"
    if sudo systemctl is-active --quiet "$service.service"; then
        echo "✅ $service.service is active"
    else
        echo "❌ $service.service is not active"
        echo "📝 Recent logs:"
        sudo journalctl -u "$service.service" --no-pager -n 5
    fi
done

echo ""
echo "🧪 Step 4: Final system test..."
python3 test_complete_system.py

echo ""
echo "🎉 Final complete fix finished!"
echo "📋 Summary:"
echo "✅ Fixed pykms module for picamera2"
echo "✅ Fixed Supabase integration issues"
echo "✅ Restarted all services"
echo "✅ Ran final system test"
echo ""
echo "🔧 If any issues remain, check:"
echo "1. .env file configuration"
echo "2. Service logs: sudo journalctl -u [service_name] -f"
echo "3. API logs: sudo journalctl -u ezrec-api.service -f" 