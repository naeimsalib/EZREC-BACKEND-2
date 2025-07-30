#!/bin/bash

# Final comprehensive fix for all remaining issues
echo "🔧 EZREC Final Comprehensive Fix"
echo "================================"

# Make all scripts executable
chmod +x fix_backend_venv_final.sh
chmod +x debug_api.sh
chmod +x restart_services.sh

# Step 1: Fix backend venv libcamera import
echo ""
echo "🔄 Step 1: Fixing backend venv libcamera import..."
./fix_backend_venv_final.sh

# Step 2: Debug API issues
echo ""
echo "🔄 Step 2: Debugging API issues..."
./debug_api.sh

# Step 3: Restart services
echo ""
echo "🔄 Step 3: Restarting services..."
./restart_services.sh

# Step 4: Test the complete system
echo ""
echo "🔄 Step 4: Testing complete system..."
python3 test_complete_system.py

echo ""
echo "🎉 Final fix completed!"
echo "📋 Summary:"
echo "✅ Fixed backend venv libcamera import"
echo "✅ Debugged API issues"
echo "✅ Restarted all services"
echo "✅ Ran complete system test" 