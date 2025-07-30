#!/bin/bash

# Fix libcamera Python binding installation
echo "🔧 Installing libcamera Python binding..."

sudo apt update
sudo apt install -y python3-libcamera libcamera-apps

echo "✅ libcamera installation completed"
echo "🔍 Testing libcamera import..."
python3 -c "import libcamera; print('✅ libcamera import successful')" || echo "❌ libcamera import failed" 