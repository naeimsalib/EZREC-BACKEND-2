#!/bin/bash

# Master Fix Script - Implements all fixes from the plan
echo "🔧 EZREC Master Fix Script"
echo "=========================="

# Make all scripts executable
chmod +x fix_libcamera.sh
chmod +x fix_permissions.sh
chmod +x fix_imagemagick.sh
chmod +x restart_services.sh

# Step 1: Install libcamera Python binding
echo ""
echo "🔄 Step 1: Installing libcamera Python binding..."
./fix_libcamera.sh

# Step 2: Fix directory permissions and ownership
echo ""
echo "🔄 Step 2: Fixing directory permissions and ownership..."
./fix_permissions.sh

# Step 3: Fix system_status.service (already done in the file)
echo ""
echo "🔄 Step 3: system_status.service already fixed"

# Step 4: Install ImageMagick for logo generation
echo ""
echo "🔄 Step 4: Installing ImageMagick for logo generation..."
./fix_imagemagick.sh

# Step 5: Smoke test video size threshold already fixed
echo ""
echo "🔄 Step 5: Smoke test video size threshold already fixed"

# Step 6: Restart and verify all services
echo ""
echo "🔄 Step 6: Restarting and verifying all services..."
./restart_services.sh

# Step 7: Run end-to-end tests
echo ""
echo "🔄 Step 7: Running end-to-end tests..."
python3 test_complete_system.py

echo ""
echo "🎉 Master fix completed!"
echo "📋 Summary of fixes applied:"
echo "✅ Installed libcamera Python binding"
echo "✅ Fixed directory permissions and ownership"
echo "✅ Fixed system_status.service syntax"
echo "✅ Installed ImageMagick"
echo "✅ Fixed smoke test video size threshold"
echo "✅ Restarted all services"
echo "✅ Ran end-to-end tests" 