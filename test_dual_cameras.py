#!/usr/bin/env python3
"""
Simple test script to verify dual camera recording
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

def create_test_booking():
    """Create a test booking that starts immediately"""
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=2)  # 2 minute recording
    
    booking = {
        "id": f"test-{int(time.time())}",
        "user_id": "test-user",
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "date": start_time.strftime("%Y-%m-%d"),
        "camera_id": "test-camera",
        "recording_id": f"rec-test-{int(time.time())}",
        "status": None,
        "email": None,
        "created_at": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": start_time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    # Write to bookings file
    bookings_path = Path("/opt/ezrec-backend/api/local_data/bookings.json")
    bookings_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(bookings_path, 'w') as f:
        json.dump([booking], f, indent=2)
    
    print(f"✅ Test booking created:")
    print(f"   ID: {booking['id']}")
    print(f"   Start: {booking['start_time']}")
    print(f"   End: {booking['end_time']}")
    print(f"   Duration: 2 minutes")
    
    return booking

if __name__ == "__main__":
    print("🎬 Creating test booking for dual camera recording...")
    booking = create_test_booking()
    print("\n📋 The dual_recorder service should detect this booking and start recording.")
    print("📁 Check /opt/ezrec-backend/recordings/ for the output files.")
    print("⏱️ Recording will run for 2 minutes.")
