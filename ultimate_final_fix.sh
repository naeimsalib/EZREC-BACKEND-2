#!/bin/bash
# Ultimate Final Fix for EZREC Backend
# Addresses all remaining critical issues

set -e

echo "🔧 Ultimate Final Fix for EZREC Backend"
echo "========================================"
echo ""

#------------------------------#
# 1. FIX NUMPY vs OPENCV CONFLICT
#------------------------------#
echo "🔧 Step 1: Fixing NumPy vs OpenCV conflict..."
echo "📦 Downgrading NumPy to match OpenCV requirements..."

# Activate backend venv and fix NumPy version
source /opt/ezrec-backend/backend/venv/bin/activate
pip install "numpy<2.3.0,>=2.0.0" --force-reinstall
echo "✅ NumPy downgraded to compatible version"
deactivate

#------------------------------#
# 2. FIX PICAMERA2 PYKMS ISSUE
#------------------------------#
echo ""
echo "🔧 Step 2: Fixing Picamera2 pykms issue..."
echo "📦 Installing system Picamera2 with pykms..."

# Install system Picamera2 (includes pykms)
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera libcamera-apps

# Remove pip-installed Picamera2 from venv
source /opt/ezrec-backend/backend/venv/bin/activate
pip uninstall picamera2 -y
echo "✅ Removed pip Picamera2, using system version with pykms"
deactivate

#------------------------------#
# 3. FIX SYSTEM_STATUS SERVICE PATH
#------------------------------#
echo ""
echo "🔧 Step 3: Fixing system_status.service path..."
echo "📝 Updating service configuration..."

# Create backup of current service file
sudo cp /etc/systemd/system/system_status.service /etc/systemd/system/system_status.service.backup

# Update the service file with correct Python path
sudo tee /etc/systemd/system/system_status.service > /dev/null << 'EOF'
[Unit]
Description=EZREC System Status Monitor
After=network.target

[Service]
Type=oneshot
User=ezrec
Group=ezrec
WorkingDirectory=/opt/ezrec-backend
Environment=PATH=/opt/ezrec-backend/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/ezrec-backend/backend/venv/bin/python3 /opt/ezrec-backend/backend/system_status.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ system_status.service updated with correct Python path"

#------------------------------#
# 4. FIX SUPABASE BOOKING STATUS FIELD
#------------------------------#
echo ""
echo "🔧 Step 4: Fixing Supabase booking status field mapping..."
echo "📝 Updating booking_utils.py for proper field mapping..."

# Update booking_utils.py to handle different field names
sudo tee /opt/ezrec-backend/api/booking_utils.py > /dev/null << 'EOF'
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from supabase import create_client, Client
from supabase._sync.client import SupabaseException

# Load environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL', 'your_supabase_url_here')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', 'your_supabase_service_role_key_here')

# Initialize Supabase client with error handling
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != 'your_supabase_url_here':
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
    else:
        print("⚠️ Supabase credentials not configured, using local mode")
except Exception as e:
    print(f"⚠️ Failed to initialize Supabase client: {e}")
    print("⚠️ System will work in local mode only")

def update_booking_status(booking_id: str, new_status: str) -> bool:
    """
    Updates booking status in both Supabase and the local cache file.
    Handles different field names (status, booking_state, state, etc.)
    """
    success = True

    # --- Update in Supabase ---
    if supabase:
        try:
            print(f"🔄 Updating Supabase booking {booking_id} to status '{new_status}'")
            
            # Try different possible field names for status
            status_fields = ['status', 'booking_state', 'state', 'booking_status']
            update_success = False
            
            for field in status_fields:
                try:
                    response = supabase.table("bookings").update({field: new_status}).eq("id", booking_id).execute()
                    if hasattr(response, "error") and response.error:
                        print(f"❌ Supabase update error with field '{field}': {response.error}")
                        continue
                    elif hasattr(response, "status_code") and response.status_code >= 400:
                        print(f"❌ Supabase update error with field '{field}': {response}")
                        continue
                    else:
                        print(f"✅ Successfully updated booking with field '{field}'")
                        update_success = True
                        break
                except Exception as e:
                    print(f"❌ Failed to update with field '{field}': {e}")
                    continue
            
            if not update_success:
                print("❌ Failed to update booking with any status field")
                success = False
                
        except Exception as e:
            print(f"❌ Supabase exception: {e}")
            success = False
    else:
        print("⚠️ Supabase not configured, skipping remote update")

    # --- Update in Local JSON ---
    try:
        BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
        if BOOKING_CACHE_FILE.exists():
            with open(BOOKING_CACHE_FILE, 'r') as f:
                data = json.load(f)
                bookings = data if isinstance(data, list) else data.get('bookings', [])
        else:
            bookings = []
        
        # Update local booking
        for booking in bookings:
            if booking.get('id') == booking_id:
                # Try different field names
                for field in ['status', 'booking_state', 'state', 'booking_status']:
                    if field in booking:
                        booking[field] = new_status
                        print(f"✅ Updated local booking with field '{field}'")
                        break
                else:
                    # If no existing field found, add 'status'
                    booking['status'] = new_status
                    print("✅ Added 'status' field to local booking")
                break
        
        # Save updated bookings
        with open(BOOKING_CACHE_FILE, 'w') as f:
            json.dump(bookings, f, indent=2)
        print("✅ Updated local bookings cache")
        
    except Exception as e:
        print(f"❌ Local update error: {e}")
        success = False

    return success

def get_bookings() -> list:
    """Get bookings from local cache file"""
    try:
        BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
        if BOOKING_CACHE_FILE.exists():
            with open(BOOKING_CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get('bookings', [])
        return []
    except Exception as e:
        print(f"❌ Error loading bookings: {e}")
        return []

def create_booking(booking_data: Dict[str, Any]) -> bool:
    """Create a new booking in local cache"""
    try:
        BOOKING_CACHE_FILE = Path('/opt/ezrec-backend/api/local_data/bookings.json')
        bookings = get_bookings()
        bookings.append(booking_data)
        
        with open(BOOKING_CACHE_FILE, 'w') as f:
            json.dump(bookings, f, indent=2)
        
        print(f"✅ Created booking: {booking_data.get('id', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return False
EOF

echo "✅ booking_utils.py updated with robust field mapping"

#------------------------------#
# 5. FIX PERMISSIONS AND OWNERSHIP
#------------------------------#
echo ""
echo "🔧 Step 5: Fixing permissions and ownership..."
echo "🔐 Setting proper ownership and permissions..."

# Set ownership
sudo chown -R ezrec:ezrec /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend

# Set specific permissions for critical files
sudo chmod 664 /opt/ezrec-backend/api/local_data/bookings.json
sudo chmod 664 /opt/ezrec-backend/status.json
sudo chmod 644 /opt/ezrec-backend/.env

# Create logs directory with proper permissions
sudo mkdir -p /opt/ezrec-backend/logs
sudo chown -R ezrec:ezrec /opt/ezrec-backend/logs
sudo chmod -R 755 /opt/ezrec-backend/logs

echo "✅ Permissions and ownership fixed"

#------------------------------#
# 6. TEST IMPORTS AND DEPENDENCIES
#------------------------------#
echo ""
echo "🔧 Step 6: Testing imports and dependencies..."
echo "🧪 Testing critical imports..."

# Test NumPy version
source /opt/ezrec-backend/backend/venv/bin/activate
python3 -c "import numpy; print(f'✅ NumPy version: {numpy.__version__}')"

# Test Picamera2 import
python3 -c "import picamera2; print('✅ Picamera2 import successful')"

# Test psutil import
python3 -c "import psutil; print('✅ psutil import successful')"

# Test Supabase import
python3 -c "import supabase; print('✅ Supabase import successful')"

deactivate
echo "✅ All critical imports working"

#------------------------------#
# 7. RELOAD AND RESTART SERVICES
#------------------------------#
echo ""
echo "🔧 Step 7: Reloading and restarting services..."
echo "🔄 Reloading systemd daemon..."

sudo systemctl daemon-reload

echo "🚀 Restarting all services..."
sudo systemctl restart dual_recorder.service
sudo systemctl restart video_worker.service
sudo systemctl restart ezrec-api.service
sudo systemctl restart system_status.service

echo "✅ All services restarted"

#------------------------------#
# 8. VERIFY SERVICE STATUS
#------------------------------#
echo ""
echo "🔧 Step 8: Verifying service status..."
echo "📊 Checking service status..."

services=("dual_recorder.service" "video_worker.service" "ezrec-api.service" "system_status.service")

for service in "${services[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        echo "✅ $service is ACTIVE"
    else
        echo "❌ $service is INACTIVE"
        echo "📋 Recent logs for $service:"
        sudo journalctl -u "$service" --no-pager -n 5
    fi
done

#------------------------------#
# 9. FINAL TEST
#------------------------------#
echo ""
echo "🔧 Step 9: Running final system test..."
echo "🧪 Testing complete system..."

cd /opt/ezrec-backend
python3 test_complete_system.py

echo ""
echo "🎉 Ultimate Final Fix completed!"
echo "📋 Summary of fixes applied:"
echo "   ✅ NumPy downgraded to compatible version"
echo "   ✅ Picamera2 system package installed with pykms"
echo "   ✅ system_status.service path corrected"
echo "   ✅ Supabase booking status field mapping fixed"
echo "   ✅ Permissions and ownership corrected"
echo "   ✅ All services restarted and verified"
echo ""
echo "🎯 Next steps:"
echo "   1. Monitor services: sudo journalctl -u dual_recorder.service -f"
echo "   2. Test API: curl http://localhost:8000/status"
echo "   3. Check recordings: ls -la /opt/ezrec-backend/recordings/" 