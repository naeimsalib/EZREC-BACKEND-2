#!/bin/bash

# Fix API issues - bookings file and JSON parsing
echo "🔧 Fixing API issues..."

# Create bookings file if it doesn't exist
echo "📝 Creating bookings file..."
sudo mkdir -p /opt/ezrec-backend/api/local_data
sudo touch /opt/ezrec-backend/api/local_data/bookings.json

# Initialize bookings file with empty array if it's empty or corrupted
if [ ! -s /opt/ezrec-backend/api/local_data/bookings.json ]; then
    echo "[]" | sudo tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null
    echo "✅ Initialized empty bookings file"
else
    # Check if it's valid JSON
    if ! python3 -c "import json; json.load(open('/opt/ezrec-backend/api/local_data/bookings.json'))" 2>/dev/null; then
        echo "⚠️ Bookings file is corrupted, reinitializing..."
        echo "[]" | sudo tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null
        echo "✅ Reinitialized corrupted bookings file"
    else
        echo "✅ Bookings file is valid JSON"
    fi
fi

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chown ezrec:ezrec /opt/ezrec-backend/api/local_data/bookings.json
sudo chmod 664 /opt/ezrec-backend/api/local_data/bookings.json

# Test the API endpoints
echo "🧪 Testing API endpoints..."
sleep 2

# Test GET /bookings
echo "🔍 Testing GET /bookings..."
response=$(curl -s http://localhost:8000/bookings)
if [ $? -eq 0 ]; then
    echo "✅ GET /bookings working"
    echo "   Response: $response"
else
    echo "❌ GET /bookings failed"
fi

# Test POST /bookings
echo "🔍 Testing POST /bookings..."
test_booking='{"id":"test_123","user_id":"test_user","camera_id":"test_camera","start_time":"2024-01-15T10:00:00","end_time":"2024-01-15T10:02:00","status":"STARTED"}'
response=$(curl -s -X POST http://localhost:8000/bookings \
    -H "Content-Type: application/json" \
    -d "$test_booking")
if [ $? -eq 0 ]; then
    echo "✅ POST /bookings working"
    echo "   Response: $response"
else
    echo "❌ POST /bookings failed"
fi

echo "✅ API issues fix completed" 