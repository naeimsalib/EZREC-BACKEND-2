#!/bin/bash

# Debug API issues
echo "🔍 Debugging API issues..."

# Check API logs
echo "📝 Checking API logs..."
sudo journalctl -u ezrec-api.service -n 20 --no-pager

# Check if API is running
echo "🔍 Checking API process..."
if pgrep -f "api_server.py" > /dev/null; then
    echo "✅ API process is running"
else
    echo "❌ API process is not running"
fi

# Check API response
echo "🔍 Testing API endpoints..."
echo "GET /status:"
curl -s http://localhost:8000/status || echo "❌ Failed"

echo "GET /bookings:"
curl -s http://localhost:8000/bookings || echo "❌ Failed"

# Check bookings file
echo "🔍 Checking bookings file..."
if [ -f "/opt/ezrec-backend/api/local_data/bookings.json" ]; then
    echo "✅ Bookings file exists"
    echo "📄 Content:"
    cat /opt/ezrec-backend/api/local_data/bookings.json
else
    echo "❌ Bookings file missing"
fi

# Check permissions
echo "🔍 Checking permissions..."
ls -la /opt/ezrec-backend/api/local_data/
ls -la /opt/ezrec-backend/api/local_data/bookings.json 2>/dev/null || echo "File not found"

# Test API with verbose output
echo "🔍 Testing API with verbose output..."
curl -v http://localhost:8000/bookings 2>&1 | head -20

echo "✅ API debug completed" 