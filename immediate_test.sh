#!/bin/bash

echo "🚀 EZREC Immediate Recording Test"
echo "================================="

# Create test start marker
touch /tmp/test_start

# Test 1: Service Status
echo "1️⃣ Testing Service Status..."
services=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service" "cloudflared.service")
for service in "${services[@]}"; do
    status=$(systemctl is-active $service)
    echo "  $service: $status"
done

# Test 2: API Endpoints
echo "2️⃣ Testing API Endpoints..."
endpoints=("/test-alive" "/status" "/api/bookings" "/api/cameras" "/api/recordings")
for endpoint in "${endpoints[@]}"; do
    echo "  Testing $endpoint..."
    response=$(curl -s http://localhost:8000$endpoint)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "    ✅ Success: ${response:0:100}..."
    else
        echo "    ❌ Failed"
    fi
done

# Test 3: Camera Detection
echo "3️⃣ Testing Camera Detection..."
echo "  Camera devices:"
ls -la /dev/video* 2>/dev/null || echo "    No camera devices found"

echo "  rpicam-vid test:"
timeout 30 rpicam-vid --list-cameras 2>&1 | head -5 || echo "    Camera detection failed or timed out"

# Test 4: Create Immediate Test Booking
echo "4️⃣ Creating Immediate Test Booking..."
START_TIME=$(date "+%Y-%m-%dT%H:%M:%S")
END_TIME=$(date -d "+2 minutes" "+%Y-%m-%dT%H:%M:%S")
BOOKING_ID="immediate-test-$(date +%s)"
CURRENT_DATE=$(date +%Y-%m-%d)
CURRENT_DATETIME=$(date +%Y-%m-%dT%H:%M:%S)

echo "  Booking ID: $BOOKING_ID"
echo "  Start: $START_TIME (NOW)"
echo "  End: $END_TIME"

sudo tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null << BOOKING_EOF
[
  {
    "id": "$BOOKING_ID",
    "user_id": "test-user",
    "start_time": "$START_TIME",
    "end_time": "$END_TIME",
    "date": "$CURRENT_DATE",
    "camera_id": "test-camera",
    "recording_id": "rec-$BOOKING_ID",
    "status": null,
    "email": null,
    "created_at": "$CURRENT_DATETIME",
    "updated_at": "$CURRENT_DATETIME"
  }
]
BOOKING_EOF

echo "  ✅ Booking created"

# Test 5: Monitor Recording Immediately
echo "5️⃣ Monitoring Recording (should start immediately)..."
echo "  🎬 Starting recording monitoring..."
for i in {1..15}; do
    echo "  --- Check $i/15 ---"
    
    # Check dual_recorder logs
    echo "    Dual Recorder:"
    sudo journalctl -u dual_recorder.service -n 3 --no-pager | tail -2
    
    # Check recording processes
    processes=$(ps aux | grep rpicam-vid | grep -v grep | wc -l)
    echo "    Recording processes: $processes"
    
    # Check for new files
    new_files=$(find /opt/ezrec-backend/recordings -name "*.mp4" -newer /tmp/test_start 2>/dev/null | wc -l)
    echo "    New recording files: $new_files"
    
    # Show any rpicam-vid processes
    if [ $processes -gt 0 ]; then
        echo "    Active rpicam-vid processes:"
        ps aux | grep rpicam-vid | grep -v grep | head -3
    fi
    
    sleep 10
done

echo "✅ Immediate test completed"
