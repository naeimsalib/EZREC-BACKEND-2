#!/bin/bash

echo "🔧 Fixing pykms module for picamera2..."
echo "========================================"

# Install pykms system-wide
echo "📦 Installing pykms system-wide..."
sudo apt update
sudo apt install -y python3-kms

# Check if pykms is available in system Python
echo "🧪 Testing pykms in system Python..."
python3 -c "import kms; print('✅ pykms available in system Python')" 2>/dev/null || {
    echo "❌ pykms not available in system Python, trying alternative..."
    sudo apt install -y python3-pykms
}

# Link pykms to backend venv
echo "🔗 Linking pykms to backend venv..."
BACKEND_VENV="/opt/ezrec-backend/backend/venv"
SITE_PACKAGES="$BACKEND_VENV/lib/python3.11/site-packages"

# Find pykms in system
PYKMS_PATH=$(python3 -c "import kms; print(kms.__file__)" 2>/dev/null)
if [ -n "$PYKMS_PATH" ]; then
    echo "📁 Found pykms at: $PYKMS_PATH"
    sudo ln -sf "$PYKMS_PATH" "$SITE_PACKAGES/kms.py"
    sudo ln -sf "$(dirname "$PYKMS_PATH")/kms" "$SITE_PACKAGES/kms"
    echo "✅ Linked pykms to backend venv"
else
    echo "⚠️ Could not find pykms, trying alternative approach..."
    # Try to install pykms directly in venv
    sudo -u ezrec "$BACKEND_VENV/bin/pip" install pykms 2>/dev/null || {
        echo "⚠️ Could not install pykms, will try to work around it..."
    }
fi

# Test picamera2 import
echo "🧪 Testing picamera2 import in backend venv..."
sudo -u ezrec "$BACKEND_VENV/bin/python" -c "
try:
    import picamera2
    print('✅ picamera2 import successful')
except ImportError as e:
    print(f'❌ picamera2 import failed: {e}')
    # Try to import without preview modules
    import sys
    sys.path.insert(0, '/opt/ezrec-backend/backend/venv/lib/python3.11/site-packages')
    try:
        from picamera2.picamera2 import Picamera2
        print('✅ Picamera2 class import successful (without previews)')
    except Exception as e2:
        print(f'❌ Picamera2 class import also failed: {e2}')
"

echo "✅ pykms fix completed" 