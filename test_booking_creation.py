#!/usr/bin/env python3
"""
Test script for creating bookings to test the dual recorder
"""

import json
import requests
import time
from datetime import datetime, timedelta
import pytz

# Configuration
API_BASE_URL = "https://api.ezrec.org"  # or "http://localhost:8000" for local testing
USER_ID = "65aa2e2a-e463-424d-b88f-0724bb0bea3a"
CAMERA_ID = "pi-001"

def create_test_booking(duration_minutes=2):
    """Create a test booking for the next few minutes"""
    
    # Calculate start and end times
    now = datetime.now(pytz.UTC)
    start_time = now + timedelta(minutes=1)  # Start in 1 minute
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    booking = {
        "id": f"test-{int(time.time())}",
        "user_id": USER_ID,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "date": start_time.strftime("%Y-%m-%d"),
        "camera_id": CAMERA_ID,
        "recording_id": f"rec-{int(time.time())}",
        "booking_id": f"test-{int(time.time())}",
        "email": None
    }
    
    print(f"🎬 Creating test booking:")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Duration: {duration_minutes} minutes")
    
    try:
        # Create booking via API
        response = requests.post(
            f"{API_BASE_URL}/bookings",
            json=[booking],
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Booking created successfully via API")
            return booking
        else:
            print(f"❌ API request failed: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None

def create_local_booking(duration_minutes=2):
    """Create a booking directly in the local cache file"""
    
    # Calculate start and end times
    now = datetime.now(pytz.UTC)
    start_time = now + timedelta(minutes=1)  # Start in 1 minute
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    booking = {
        "id": f"test-local-{int(time.time())}",
        "user_id": USER_ID,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "date": start_time.strftime("%Y-%m-%d"),
        "camera_id": CAMERA_ID,
        "recording_id": f"rec-local-{int(time.time())}",
        "booking_id": f"test-local-{int(time.time())}",
        "email": None
    }
    
    try:
        # Read existing bookings
        cache_file = "/opt/ezrec-backend/api/local_data/bookings.json"
        try:
            with open(cache_file, 'r') as f:
                bookings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            bookings = []
        
        # Add new booking
        bookings.append(booking)
        
        # Write back to file
        with open(cache_file, 'w') as f:
            json.dump(bookings, f, indent=2)
        
        print(f"✅ Local booking created successfully")
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Duration: {duration_minutes} minutes")
        return booking
        
    except Exception as e:
        print(f"❌ Failed to create local booking: {e}")
        return None

def monitor_recording():
    """Monitor the recording process"""
    print("\n📊 Monitoring recording process...")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            # Check if recording is active
            try:
                with open("/opt/ezrec-backend/status.json", 'r') as f:
                    status = json.load(f)
                    is_recording = status.get("is_recording", False)
                    print(f"🎥 Recording status: {'🟢 Active' if is_recording else '🔴 Inactive'}")
            except:
                print("🎥 Recording status: ❓ Unknown")
            
            # Check for recent recordings
            import subprocess
            try:
                result = subprocess.run(
                    ["find", "/opt/ezrec-backend/recordings", "-name", "*.mp4", "-mmin", "-5"],
                    capture_output=True, text=True
                )
                if result.stdout.strip():
                    print("📹 Recent recordings found:")
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            print(f"   {line}")
                else:
                    print("📹 No recent recordings found")
            except:
                print("📹 Could not check recordings")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

def main():
    print("🧪 EZREC Dual Recorder Test Script")
    print("==================================")
    
    while True:
        print("\nOptions:")
        print("1. Create test booking via API")
        print("2. Create test booking locally")
        print("3. Monitor recording process")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            duration = input("Enter duration in minutes (default 2): ").strip()
            duration = int(duration) if duration.isdigit() else 2
            create_test_booking(duration)
            
        elif choice == "2":
            duration = input("Enter duration in minutes (default 2): ").strip()
            duration = int(duration) if duration.isdigit() else 2
            create_local_booking(duration)
            
        elif choice == "3":
            monitor_recording()
            
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 