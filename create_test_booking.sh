#!/bin/bash

echo "🚀 Creating Test Booking and Monitoring Recording"

# Calculate start time (1 minute from now)
START_TIME=$(date -d "+1 minute" "+%Y-%m-%dT%H:%M:%S")
END_TIME=$(date -d "+3 minutes" "+%Y-%m-%dT%H:%M:%S")
BOOKING_ID="test-$(date +%s)"

echo "📋 Creating test booking: $BOOKING_ID"
echo "⏰ Start time: $START_TIME"
echo "⏰ End time: $END_TIME"

# Create booking
sudo tee /opt/ezrec-backend/api/local_data/bookings.json > /dev/null << BOOKING_EOF
[
  {
    "id": "$BOOKING_ID",
    "user_id": "test-user",
    "start_time": "$START_TIME",
    "end_time": "$END_TIME",
    "date": "$(date +%Y-%m-%d)",
    "camera_id": "test-camera",
    "recording_id": "rec-$BOOKING_ID",
    "status": null,
    "email": null,
    "created_at": "$(date +%Y-%m-%dT%H:%M:%S)",
    "updated_at": "$(date +%Y-%m-%dT%H:%M:%S)"
  }
]
BOOKING_EOF

echo "✅ Booking created successfully"
echo "📹 Monitoring recording for 5 minutes..."

# Monitor for 5 minutes
for i in {1..30}; do
    echo "--- Check $i/30 ---"
    
    # Check dual_recorder logs
    echo "🎬 Dual Recorder Status:"
    sudo journalctl -u dual_recorder.service -n 5 --no-pager | tail -3
    
    # Check for recording processes
    echo "📷 Recording Processes:"
    ps aux | grep rpicam-vid | grep -v grep || echo "No recording processes"
    
    # Check for new recording files
    echo "📁 Recording Files:"
    find /opt/ezrec-backend/recordings -name "*.mp4" -newer /tmp/test_start 2>/dev/null | head -5 || echo "No new recording files"
    
    echo "---"
    sleep 10
done

echo "✅ Test monitoring completed"
