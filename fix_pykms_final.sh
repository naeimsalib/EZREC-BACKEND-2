#!/bin/bash

echo "🔧 Final fix for pykms module..."
echo "================================="

# Create a proper kms.py placeholder module
echo "📦 Creating kms.py placeholder module..."
BACKEND_VENV="/opt/ezrec-backend/backend/venv"
SITE_PACKAGES="$BACKEND_VENV/lib/python3.11/site-packages"

# Create a comprehensive kms.py placeholder
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

# Test the import
echo "🧪 Testing picamera2 import..."
cd /opt/ezrec-backend/backend
source venv/bin/activate

python3 -c "
try:
    import picamera2
    print('✅ picamera2 import successful')
    
    # Test basic functionality
    from picamera2 import Picamera2
    print('✅ Picamera2 class import successful')
    
except Exception as e:
    print(f'❌ picamera2 import failed: {e}')
    import traceback
    traceback.print_exc()
"

echo "✅ pykms final fix completed" 