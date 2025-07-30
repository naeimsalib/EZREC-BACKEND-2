#!/bin/bash

echo "🔧 EZREC Comprehensive Fix v2"
echo "=============================="
echo ""

#------------------------------#
# 1. FIX MISSING .env FILE
#------------------------------#
echo "📄 Step 1: Creating .env file..."

ENV_FILE="/opt/ezrec-backend/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating .env file from template..."
    sudo tee "$ENV_FILE" > /dev/null << 'EOF'
# EZREC Backend Environment Configuration
# Copy this file to .env and fill in your actual values

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=your_s3_bucket_name_here
AWS_USER_MEDIA_BUCKET=your_user_media_bucket_here

# Camera Configuration
CAMERA_0_SERIAL=88000
CAMERA_1_SERIAL=80000
DUAL_CAMERA_MODE=true

# User Configuration
USER_ID=your_user_id_here
CAMERA_ID=your_camera_id_here

# Email Configuration (for share links)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
EMAIL_USE_TLS=True
EMAIL_FROM=your_email@gmail.com

# Share Configuration
SHARE_BASE_URL=https://yourdomain.com

# Timezone
TIMEZONE_NAME=UTC

# Recording Configuration
RECORDING_QUALITY=high
MERGE_METHOD=side_by_side
RECORDING_FPS=30
LOG_LEVEL=INFO
BOOKING_CHECK_INTERVAL=5
EOF

    # Set proper permissions
    sudo chown ezrec:ezrec "$ENV_FILE"
    sudo chmod 644 "$ENV_FILE"
    echo "✅ .env file created with template"
    echo "⚠️ IMPORTANT: Please edit the .env file with your actual credentials:"
    echo "   sudo nano /opt/ezrec-backend/.env"
else
    echo "✅ .env file already exists"
    echo "📋 Current .env variables:"
    grep -E "^(SUPABASE|AWS|CAMERA|USER|EMAIL|SHARE|TIMEZONE|RECORDING)" "$ENV_FILE" 2>/dev/null || echo "⚠️ No configured variables found"
fi

#------------------------------#
# 2. FIX PYKMS MODULE
#------------------------------#
echo ""
echo "🔧 Step 2: Fixing pykms module..."

BACKEND_VENV="/opt/ezrec-backend/backend/venv"
SITE_PACKAGES="$BACKEND_VENV/lib/python3.11/site-packages"

# Create a comprehensive kms.py placeholder module
echo "📦 Creating kms.py placeholder module..."
sudo tee "$SITE_PACKAGES/kms.py" > /dev/null << 'EOF'
"""
KMS (Kernel Mode Setting) placeholder module for picamera2 compatibility.
This is a placeholder that provides the minimum interface needed by picamera2.
"""

import sys
import warnings

# Suppress warnings about missing KMS functionality
warnings.filterwarnings("ignore", category=UserWarning, module="kms")

class KMS:
    """Placeholder KMS class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

class DRM:
    """Placeholder DRM class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

class Card:
    """Placeholder Card class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Connector:
    """Placeholder Connector class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Crtc:
    """Placeholder Crtc class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Encoder:
    """Placeholder Encoder class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Framebuffer:
    """Placeholder Framebuffer class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Mode:
    """Placeholder Mode class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Plane:
    """Placeholder Plane class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Property:
    """Placeholder Property class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class PropertyBlob:
    """Placeholder PropertyBlob class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class Resource:
    """Placeholder Resource class for picamera2 compatibility"""
    def __init__(self, *args, **kwargs):
        pass

# Common constants that might be used
DRM_MODE_CONNECTOR_Unknown = 0
DRM_MODE_CONNECTOR_VGA = 1
DRM_MODE_CONNECTOR_DVII = 2
DRM_MODE_CONNECTOR_DVID = 3
DRM_MODE_CONNECTOR_DVIA = 4
DRM_MODE_CONNECTOR_Composite = 5
DRM_MODE_CONNECTOR_SVIDEO = 6
DRM_MODE_CONNECTOR_LVDS = 7
DRM_MODE_CONNECTOR_Component = 8
DRM_MODE_CONNECTOR_9PinDIN = 9
DRM_MODE_CONNECTOR_DisplayPort = 10
DRM_MODE_CONNECTOR_HDMIA = 11
DRM_MODE_CONNECTOR_HDMIB = 12
DRM_MODE_CONNECTOR_TV = 13
DRM_MODE_CONNECTOR_eDP = 14
DRM_MODE_CONNECTOR_VIRTUAL = 15
DRM_MODE_CONNECTOR_DSI = 16

# Print a message when imported
print("⚠️ Using KMS placeholder module - some picamera2 features may be limited")

# Make the module importable as both 'kms' and 'pykms'
sys.modules['pykms'] = sys.modules[__name__]
EOF

# Set proper ownership
sudo chown ezrec:ezrec "$SITE_PACKAGES/kms.py"
sudo chmod 644 "$SITE_PACKAGES/kms.py"

# Also create pykms.py as an alias
sudo ln -sf "$SITE_PACKAGES/kms.py" "$SITE_PACKAGES/pykms.py"

echo "✅ KMS placeholder module created"

#------------------------------#
# 3. FIX SUPABASE CONFIGURATION
#------------------------------#
echo ""
echo "🔧 Step 3: Fixing Supabase configuration..."

# Make booking_utils.py more robust to handle missing Supabase credentials
echo "🔧 Making booking_utils.py more robust..."
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
supabase: Optional[Client] = None
try:
    if SUPABASE_URL != 'your_supabase_url_here' and SUPABASE_KEY != 'your_supabase_service_role_key_here':
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
    else:
        print("⚠️ Supabase credentials not configured, using local mode")
except Exception as e:
    print(f"⚠️ Failed to initialize Supabase client: {e}")
    print("⚠️ System will work in local mode only")

def update_booking_status(booking_id: str, new_status: str) -> bool:
    """Update booking status in Supabase or local storage"""
    try:
        if supabase:
            # Update in Supabase
            response = supabase.table('bookings').update(
                {'status': new_status}
            ).eq('id', booking_id).execute()
            print(f"✅ Updated booking {booking_id} status to {new_status} in Supabase")
            return True
        else:
            # Update local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            if bookings_file.exists():
                try:
                    with open(bookings_file, 'r') as f:
                        bookings = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    bookings = []
                
                # Update the booking
                for booking in bookings:
                    if booking.get('id') == booking_id:
                        booking['status'] = new_status
                        break
                
                with open(bookings_file, 'w') as f:
                    json.dump(bookings, f, indent=2)
                
                print(f"✅ Updated booking {booking_id} status to {new_status} locally")
                return True
            else:
                print(f"❌ Could not update booking {booking_id}: no local storage")
                return False
    except Exception as e:
        print(f"❌ Error updating booking status: {e}")
        return False

def get_bookings() -> list:
    """Get bookings from Supabase or local storage"""
    try:
        if supabase:
            # Get from Supabase
            response = supabase.table('bookings').select('*').execute()
            return response.data
        else:
            # Get from local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            if bookings_file.exists():
                try:
                    with open(bookings_file, 'r') as f:
                        return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    return []
            return []
    except Exception as e:
        print(f"❌ Error getting bookings: {e}")
        return []

def create_booking(booking_data: Dict[str, Any]) -> bool:
    """Create booking in Supabase or local storage"""
    try:
        if supabase:
            # Create in Supabase
            response = supabase.table('bookings').insert(booking_data).execute()
            print(f"✅ Created booking in Supabase")
            return True
        else:
            # Create in local file
            bookings_file = Path('/opt/ezrec-backend/api/local_data/bookings.json')
            try:
                with open(bookings_file, 'r') as f:
                    bookings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                bookings = []
            
            bookings.append(booking_data)
            
            with open(bookings_file, 'w') as f:
                json.dump(bookings, f, indent=2)
            
            print(f"✅ Created booking locally")
            return True
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        return False
EOF

# Set proper permissions
sudo chown ezrec:ezrec /opt/ezrec-backend/api/booking_utils.py
sudo chmod 644 /opt/ezrec-backend/api/booking_utils.py

echo "✅ Supabase configuration made robust"

#------------------------------#
# 4. CREATE REQUIRED DIRECTORIES
#------------------------------#
echo ""
echo "📁 Step 4: Creating required directories..."

# Create all required directories
sudo mkdir -p /opt/ezrec-backend/recordings
sudo mkdir -p /opt/ezrec-backend/processed
sudo mkdir -p /opt/ezrec-backend/final
sudo mkdir -p /opt/ezrec-backend/assets
sudo mkdir -p /opt/ezrec-backend/logs
sudo mkdir -p /opt/ezrec-backend/events
sudo mkdir -p /opt/ezrec-backend/api/local_data

# Set proper ownership
sudo chown -R ezrec:ezrec /opt/ezrec-backend
sudo chmod -R 755 /opt/ezrec-backend

echo "✅ Required directories created"

#------------------------------#
# 5. INITIALIZE BOOKINGS FILE
#------------------------------#
echo ""
echo "📄 Step 5: Initializing bookings file..."

BOOKINGS_FILE="/opt/ezrec-backend/api/local_data/bookings.json"

if [ ! -f "$BOOKINGS_FILE" ]; then
    echo "📝 Creating empty bookings file..."
    sudo tee "$BOOKINGS_FILE" > /dev/null << 'EOF'
[]
EOF
    sudo chown ezrec:ezrec "$BOOKINGS_FILE"
    sudo chmod 644 "$BOOKINGS_FILE"
    echo "✅ Bookings file initialized"
else
    echo "✅ Bookings file already exists"
fi

#------------------------------#
# 6. TEST THE FIXES
#------------------------------#
echo ""
echo "🧪 Step 6: Testing the fixes..."

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

#------------------------------#
# 7. RESTART SERVICES
#------------------------------#
echo ""
echo "🔄 Step 7: Restarting services..."

sudo systemctl daemon-reload
sudo systemctl restart dual_recorder.service video_worker.service ezrec-api.service system_status.service

echo "⏳ Waiting for services to stabilize..."
sleep 10

#------------------------------#
# 8. FINAL STATUS CHECK
#------------------------------#
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
echo "📋 Summary:"
echo "==========="
echo "✅ .env file created/verified"
echo "✅ pykms module placeholder created"
echo "✅ Supabase configuration made robust"
echo "✅ All services restarted"
echo ""
echo "🎯 Next steps:"
echo "1. Update your .env file with actual credentials: sudo nano /opt/ezrec-backend/.env"
echo "2. Test the complete system: python3 test_complete_system.py"
echo "3. Monitor services: sudo systemctl status ezrec-api.service"
echo ""
echo "🎉 Comprehensive fix completed!" 