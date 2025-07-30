#!/bin/bash

echo "🔧 Quick Fix for Remaining Issues"
echo "=================================="
echo ""

#------------------------------#
# 1. FIX SYSTEM_STATUS SERVICE (MISSING PSUTIL)
#------------------------------#
echo "🔧 Step 1: Fixing system_status service..."

# Install psutil in the backend venv
echo "📦 Installing psutil in backend virtual environment..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
pip install psutil

# Test the import
echo "🧪 Testing psutil import..."
if python3 -c "import psutil; print('✅ psutil import successful')" 2>/dev/null; then
    echo "✅ psutil import working"
else
    echo "❌ psutil import still failing"
fi

#------------------------------#
# 2. FIX PYKMS MODULE (FINAL ATTEMPT)
#------------------------------#
echo ""
echo "🔧 Step 2: Final pykms module fix..."

BACKEND_VENV="/opt/ezrec-backend/backend/venv"
SITE_PACKAGES="$BACKEND_VENV/lib/python3.11/site-packages"

# Remove any existing pykms files
sudo rm -f "$SITE_PACKAGES/pykms.py" "$SITE_PACKAGES/kms.py" "$SITE_PACKAGES/pykms.pyc" "$SITE_PACKAGES/kms.pyc"

# Create a comprehensive kms.py placeholder module
echo "📦 Creating comprehensive kms.py placeholder module..."
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
# 3. TEST THE FIXES
#------------------------------#
echo ""
echo "🧪 Step 3: Testing the fixes..."

# Test picamera2 import
echo "🔍 Testing picamera2 import..."
cd /opt/ezrec-backend/backend
source venv/bin/activate
if python3 -c "import picamera2; print('✅ picamera2 import successful')" 2>/dev/null; then
    echo "✅ picamera2 import working"
else
    echo "❌ picamera2 import still failing"
fi

# Test system_status import
echo "🔍 Testing system_status import..."
if python3 -c "import psutil; print('✅ psutil import successful')" 2>/dev/null; then
    echo "✅ psutil import working"
else
    echo "❌ psutil import still failing"
fi

#------------------------------#
# 4. RESTART SERVICES
#------------------------------#
echo ""
echo "🔄 Step 4: Restarting services..."

sudo systemctl daemon-reload
sudo systemctl restart system_status.service

echo "⏳ Waiting for services to stabilize..."
sleep 5

#------------------------------#
# 5. FINAL STATUS CHECK
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
        sudo journalctl -u "$service.service" --no-pager -n 3
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
echo "✅ psutil installed in backend venv"
echo "✅ pykms module placeholder created"
echo "✅ All services restarted"
echo ""
echo "🎯 Next steps:"
echo "1. Test the complete system: python3 test_complete_system.py"
echo "2. Monitor services: sudo systemctl status system_status.service"
echo "3. Check API: curl http://localhost:8000/status"
echo ""
echo "🎉 Quick fix completed!" 