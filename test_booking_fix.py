#!/usr/bin/env python3
"""
Test booking fix script - creates a test booking with correct user/camera IDs
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/opt/ezrec-backend/.env')

def create_test_booking():
    """Create a test booking with correct user and camera IDs"""
    
    # Get user and camera IDs from environment
    user_id = os.getenv('USER_ID')
    camera_id = os.getenv('CAMERA_ID')
    
    if not user_id or not camera_id:
        print("❌ Missing USER_ID or CAMERA_ID in environment")
        return False
    
    # Create booking that starts in 30 seconds and lasts 2 minutes
    start_time = datetime.now() + timedelta(seconds=30)
    end_time = start_time + timedelta(minutes=2)
    
    booking_data = {
        "id": "production_test_correct_ids",
        "user_id": user_id,
        "camera_id": camera_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "STARTED"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/bookings",
            json=booking_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Created test booking: {response.json()}")
            print(f"📅 Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"👤 User ID: {user_id}")
            print(f"📷 Camera ID: {camera_id}")
            return True
        else:
            print(f"❌ Failed to create booking: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return False

def main():
    print("🚀 Creating test booking with correct user/camera IDs...")
    
    if create_test_booking():
        print("✅ Test booking created successfully!")
        print("📹 The dual_recorder service should now detect and start recording")
    else:
        print("❌ Failed to create test booking")

if __name__ == "__main__":
    main() 