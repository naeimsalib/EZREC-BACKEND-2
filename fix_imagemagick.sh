#!/bin/bash

# Install ImageMagick for logo generation
echo "🎨 Installing ImageMagick for logo generation..."

sudo apt update
sudo apt install -y imagemagick

echo "✅ ImageMagick installation completed"
echo "🔍 Testing ImageMagick..."
convert -version && echo "✅ ImageMagick working" || echo "❌ ImageMagick failed" 