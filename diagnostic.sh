#!/bin/bash

# EZREC Diagnostic Script
# Checks current system state and identifies issues

echo "🔍 EZREC System Diagnostic"
echo "=========================="

#------------------------------#
# 1. CHECK SYSTEM REQUIREMENTS
#------------------------------#
echo "🔧 System Requirements Check:"
echo "-----------------------------"

# Check Python
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1)
    echo "✅ Python: $python_version"
else
    echo "❌ Python3 not found"
fi

# Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    ffmpeg_version=$(ffmpeg -version | head -1)
    echo "✅ FFmpeg: $ffmpeg_version"
else
    echo "❌ FFmpeg not found"
fi

# Check v4l2-ctl
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ v4l2-ctl: available"
else
    echo "❌ v4l2-ctl not found"
fi

#------------------------------#
# 2. CHECK DIRECTORY STRUCTURE
#------------------------------#
echo ""
echo "📁 Directory Structure Check:"
echo "----------------------------"

REQUIRED_DIRS=(
    "/opt/ezrec-backend"
    "/opt/ezrec-backend/backend"
    "/opt/ezrec-backend/api"
    "/opt/ezrec-backend/recordings"
    "/opt/ezrec-backend/processed"
    "/opt/ezrec-backend/final"
    "/opt/ezrec-backend/assets"
    "/opt/ezrec-backend/logs"
    "/opt/ezrec-backend/events"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir"
    else
        echo "❌ $dir missing"
    fi
done

#------------------------------#
# 3. CHECK VIRTUAL ENVIRONMENTS
#------------------------------#
echo ""
echo "🐍 Virtual Environment Check:"
echo "----------------------------"

# Check API venv
if [ -d "/opt/ezrec-backend/api/venv" ]; then
    echo "✅ API virtual environment exists"
    if [ -f "/opt/ezrec-backend/api/venv/bin/python3" ]; then
        echo "✅ API Python executable exists"
        
        # Test API imports
        if /opt/ezrec-backend/api/venv/bin/python3 -c "import fastapi, uvicorn" 2>/dev/null; then
            echo "✅ API imports working"
        else
            echo "❌ API imports failing"
        fi
    else
        echo "❌ API Python executable missing"
    fi
else
    echo "❌ API virtual environment missing"
fi

# Check backend venv
if [ -d "/opt/ezrec-backend/backend/venv" ]; then
    echo "✅ Backend virtual environment exists"
    if [ -f "/opt/ezrec-backend/backend/venv/bin/python3" ]; then
        echo "✅ Backend Python executable exists"
        
        # Test backend imports
        if /opt/ezrec-backend/backend/venv/bin/python3 -c "import psutil, boto3" 2>/dev/null; then
            echo "✅ Backend imports working"
        else
            echo "❌ Backend imports failing"
        fi
    else
        echo "❌ Backend Python executable missing"
    fi
else
    echo "❌ Backend virtual environment missing"
fi

#------------------------------#
# 4. CHECK OWNERSHIP
#------------------------------#
echo ""
echo "🔐 Ownership Check:"
echo "------------------"

# Check API venv ownership
if [ -d "/opt/ezrec-backend/api/venv" ]; then
    owner=$(stat -c '%U:%G' /opt/ezrec-backend/api/venv)
    echo "API venv ownership: $owner"
    if [ "$owner" = "ezrec:ezrec" ]; then
        echo "✅ API venv ownership correct"
    else
        echo "❌ API venv ownership incorrect (should be ezrec:ezrec)"
    fi
fi

# Check backend venv ownership
if [ -d "/opt/ezrec-backend/backend/venv" ]; then
    owner=$(stat -c '%U:%G' /opt/ezrec-backend/backend/venv)
    echo "Backend venv ownership: $owner"
    if [ "$owner" = "ezrec:ezrec" ]; then
        echo "✅ Backend venv ownership correct"
    else
        echo "❌ Backend venv ownership incorrect (should be ezrec:ezrec)"
    fi
fi

#------------------------------#
# 5. CHECK SERVICES
#------------------------------#
echo ""
echo "🚀 Service Status Check:"
echo "----------------------"

SERVICES=("dual_recorder.service" "video_worker.service" "ezrec-api.service")

for service in "${SERVICES[@]}"; do
    if systemctl is-enabled "$service" &>/dev/null; then
        echo "✅ $service is enabled"
    else
        echo "❌ $service is not enabled"
    fi
    
    if systemctl is-active "$service" &>/dev/null; then
        echo "✅ $service is active"
    else
        echo "❌ $service is not active"
    fi
done

#------------------------------#
# 6. CHECK SERVICE FILES
#------------------------------#
echo ""
echo "⚙️ Service File Check:"
echo "-------------------"

SERVICE_FILES=(
    "/etc/systemd/system/dual_recorder.service"
    "/etc/systemd/system/video_worker.service"
    "/etc/systemd/system/ezrec-api.service"
)

for file in "${SERVICE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
        
        # Check ExecStart path
        exec_start=$(grep "ExecStart=" "$file" | cut -d'=' -f2)
        if [ -n "$exec_start" ]; then
            if [ -f "$exec_start" ]; then
                echo "✅ ExecStart path exists: $exec_start"
            else
                echo "❌ ExecStart path missing: $exec_start"
            fi
        fi
    else
        echo "❌ $file missing"
    fi
done

#------------------------------#
# 7. CHECK API RESPONSE
#------------------------------#
echo ""
echo "🌐 API Response Check:"
echo "-------------------"

if curl -s http://localhost:8000/status >/dev/null 2>&1; then
    echo "✅ API server is responding"
    response=$(curl -s http://localhost:8000/status)
    echo "   Response: $response"
else
    echo "❌ API server not responding"
    
    # Check if port 8000 is in use
    if netstat -tlnp 2>/dev/null | grep ":8000" >/dev/null; then
        echo "⚠️ Port 8000 is in use but API not responding"
    else
        echo "⚠️ Port 8000 is not in use"
    fi
fi

#------------------------------#
# 8. CHECK LOGS
#------------------------------#
echo ""
echo "📝 Recent Logs Check:"
echo "-------------------"

# Check API logs
echo "API Service Logs (last 5 lines):"
sudo journalctl -u ezrec-api.service -n 5 --no-pager || echo "No API logs found"

echo ""
echo "Dual Recorder Logs (last 5 lines):"
sudo journalctl -u dual_recorder.service -n 5 --no-pager || echo "No dual_recorder logs found"

#------------------------------#
# 9. CHECK ASSETS
#------------------------------#
echo ""
echo "🎨 Assets Check:"
echo "-------------"

ASSETS=(
    "/opt/ezrec-backend/assets/sponsor.png"
    "/opt/ezrec-backend/assets/company.png"
    "/opt/ezrec-backend/assets/intro.mp4"
)

for asset in "${ASSETS[@]}"; do
    if [ -f "$asset" ]; then
        size=$(stat -c '%s' "$asset")
        echo "✅ $asset ($size bytes)"
    else
        echo "❌ $asset missing"
    fi
done

#------------------------------#
# 10. SUMMARY
#------------------------------#
echo ""
echo "📊 Diagnostic Summary:"
echo "====================="

echo "🔧 System Requirements: $(command -v python3 && command -v ffmpeg && command -v v4l2-ctl && echo "✅" || echo "❌")"
echo "📁 Directory Structure: $(for dir in "${REQUIRED_DIRS[@]}"; do [ -d "$dir" ] || exit 1; done && echo "✅" || echo "❌")"
echo "🐍 Virtual Environments: $([ -d "/opt/ezrec-backend/api/venv" ] && [ -d "/opt/ezrec-backend/backend/venv" ] && echo "✅" || echo "❌")"
echo "🚀 Services: $(systemctl is-active dual_recorder.service video_worker.service ezrec-api.service >/dev/null 2>&1 && echo "✅" || echo "❌")"
echo "🌐 API Response: $(curl -s http://localhost:8000/status >/dev/null 2>&1 && echo "✅" || echo "❌")"

echo ""
echo "🎯 Next Steps:"
echo "1. If any ❌ found above, run: sudo ./comprehensive_fix.sh"
echo "2. Test API: curl http://localhost:8000/status"
echo "3. Run complete test: python3 test_complete_system.py"
echo "4. Check logs: sudo journalctl -u ezrec-api.service -f" 