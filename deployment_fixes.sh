#!/bin/bash

# Comprehensive fixes for deployment.sh to resolve all identified issues

# Fix port conflicts aggressively with comprehensive cleanup
fix_port_conflicts_comprehensive() {
    echo "🔧 Fixing port conflicts with comprehensive cleanup..."
    
    # Stop all EZREC services first
    echo "🛑 Stopping all EZREC services..."
    sudo systemctl stop ezrec-api.service 2>/dev/null || true
    sudo systemctl stop video_worker.service 2>/dev/null || true
    sudo systemctl stop dual_recorder.service 2>/dev/null || true
    sudo systemctl stop system_status.service 2>/dev/null || true
    
    # Kill any processes using our ports with multiple strategies
    echo "🧹 Comprehensive port cleanup..."
    
    # Strategy 1: Kill by port
    if lsof -i :8000 >/dev/null 2>&1; then
        echo "🔍 Found processes on port 8000, killing them..."
        sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    if lsof -i :9000 >/dev/null 2>&1; then
        echo "🔍 Found processes on port 9000, killing them..."
        sudo lsof -ti :9000 | xargs -r sudo kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Strategy 2: Kill by process name
    echo "🧹 Killing processes by name..."
    sudo pkill -f "uvicorn" 2>/dev/null || true
    sudo pkill -f "api_server" 2>/dev/null || true
    sudo pkill -f "python.*8000" 2>/dev/null || true
    sudo pkill -f "python.*9000" 2>/dev/null || true
    sudo pkill -f "python.*api_server" 2>/dev/null || true
    
    # Wait for processes to fully terminate
    sleep 3
    
    # Verify ports are free
    for port in 8000 9000; do
        if ! lsof -i :$port >/dev/null 2>&1; then
            echo "✅ Port $port is now free"
        else
            echo "❌ Port $port is still in use after cleanup"
            echo "📋 Processes still using port $port:"
            sudo lsof -i :$port 2>/dev/null || true
        fi
    done
    
    echo "✅ Comprehensive port conflict resolution completed"
}

# Install psutil in all virtual environments
install_psutil_everywhere() {
    echo "🔧 Installing psutil in all virtual environments..."
    
    DEPLOY_PATH="/opt/ezrec-backend"
    DEPLOY_USER="michomanoly14892"
    
    # Install in backend venv
    if [[ -d "$DEPLOY_PATH/backend/venv" ]]; then
        echo "📦 Installing psutil in backend virtual environment..."
        if sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/pip" install --no-cache-dir psutil; then
            echo "✅ psutil installed successfully in backend venv"
        else
            echo "❌ psutil installation failed in backend venv"
            return 1
        fi
    fi
    
    # Install in API venv
    if [[ -d "$DEPLOY_PATH/api/venv" ]]; then
        echo "📦 Installing psutil in API virtual environment..."
        if sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/pip" install --no-cache-dir psutil; then
            echo "✅ psutil installed successfully in API venv"
        else
            echo "❌ psutil installation failed in API venv"
            return 1
        fi
    fi
    
    echo "✅ psutil installed successfully in all environments"
}

# Ensure all services are properly enabled
ensure_services_enabled() {
    echo "🔧 Ensuring all services are properly enabled..."
    
    SERVICES=("dual_recorder" "video_worker" "ezrec-api" "system_status")
    TIMER_SERVICES=("system_status")
    
    # Enable all EZREC services
    for service in "${SERVICES[@]}"; do
        echo "🔧 Enabling $service.service for auto-start..."
        if sudo systemctl enable ${service}.service; then
            echo "✅ $service.service enabled successfully"
        else
            echo "❌ Failed to enable $service.service"
            return 1
        fi
    done
    
    # Enable timers
    for timer in "${TIMER_SERVICES[@]}"; do
        echo "🔧 Enabling $timer.timer for auto-start..."
        if sudo systemctl enable ${timer}.timer; then
            echo "✅ $timer.timer enabled successfully"
        else
            echo "❌ Failed to enable $timer.timer"
            return 1
        fi
    done
    
    echo "✅ All services properly enabled for auto-start"
}

# Start all services safely
start_all_services_safely() {
    echo "🔧 Starting all services safely with port conflict prevention..."
    
    # First, ensure ports are free
    fix_port_conflicts_comprehensive
    
    SERVICES=("ezrec-api" "dual_recorder" "video_worker" "system_status")
    
    # Start services in correct order with delays
    for service in "${SERVICES[@]}"; do
        echo "🚀 Starting $service.service..."
        
        # Special handling for API service
        if [[ "$service" == "ezrec-api" ]]; then
            echo "🔧 Special handling for API service..."
            
            # Double-check port 8000 is free
            if lsof -i :8000 >/dev/null 2>&1; then
                echo "⚠️ Port 8000 still in use, forcing cleanup..."
                sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null || true
                sleep 3
            fi
            
            # Start the service
            if sudo systemctl start ${service}.service; then
                echo "✅ $service.service started successfully"
            else
                echo "❌ Failed to start $service.service"
                sudo systemctl status ${service}.service --no-pager -l
                return 1
            fi
            
            # Wait for API to be ready
            echo "⏳ Waiting for API service to be ready..."
            sleep 10
            
            # Test API endpoint
            if curl -s http://localhost:8000/test-alive >/dev/null 2>&1; then
                echo "✅ API service is responding"
            else
                echo "⚠️ API service not responding yet, but continuing..."
            fi
        else
            # Start other services
            if sudo systemctl start ${service}.service; then
                echo "✅ $service.service started successfully"
            else
                echo "❌ Failed to start $service.service"
                sudo systemctl status ${service}.service --no-pager -l
                return 1
            fi
        fi
        
        # Wait between service starts
        sleep 3
    done
    
    echo "✅ All services started safely"
}

# Comprehensive system verification
verify_system_completely() {
    echo "🔍 Performing comprehensive system verification..."
    
    all_checks_passed=true
    SERVICES=("dual_recorder" "video_worker" "ezrec-api" "system_status")
    DEPLOY_PATH="/opt/ezrec-backend"
    DEPLOY_USER="michomanoly14892"
    
    # Check 1: All services are running
    echo "🧪 Checking all services are running..."
    for service in "${SERVICES[@]}"; do
        if sudo systemctl is-active --quiet ${service}.service; then
            echo "✅ $service.service is running"
        else
            echo "❌ $service.service is not running"
            all_checks_passed=false
        fi
    done
    
    # Check 2: API endpoints are responding
    echo "🧪 Testing API endpoints..."
    if curl -s http://localhost:8000/test-alive >/dev/null 2>&1; then
        echo "✅ API /test-alive endpoint is responding"
    else
        echo "❌ API /test-alive endpoint is not responding"
        all_checks_passed=false
    fi
    
    if curl -s http://localhost:8000/status >/dev/null 2>&1; then
        echo "✅ API /status endpoint is responding"
    else
        echo "❌ API /status endpoint is not responding"
        all_checks_passed=false
    fi
    
    # Check 3: Python imports are working
    echo "🧪 Testing Python imports..."
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/backend/venv/bin/python3" -c "import psutil, picamera2, cv2; print('✅ Backend imports working')" 2>/dev/null; then
        echo "✅ Backend Python imports are working"
    else
        echo "❌ Backend Python imports failed"
        all_checks_passed=false
    fi
    
    if sudo -u $DEPLOY_USER "$DEPLOY_PATH/api/venv/bin/python3" -c "import psutil, fastapi; print('✅ API imports working')" 2>/dev/null; then
        echo "✅ API Python imports are working"
    else
        echo "❌ API Python imports failed"
        all_checks_passed=false
    fi
    
    # Check 4: Cloudflare tunnel is running
    echo "🧪 Testing Cloudflare tunnel..."
    if sudo systemctl is-active --quiet cloudflared.service; then
        echo "✅ Cloudflare tunnel is running"
    else
        echo "❌ Cloudflare tunnel is not running"
        all_checks_passed=false
    fi
    
    # Final result
    if [[ "$all_checks_passed" == true ]]; then
        echo "🎉 All system verification checks passed!"
        return 0
    else
        echo "❌ Some system verification checks failed"
        return 1
    fi
}

# Main execution function
main() {
    echo "🚀 Starting comprehensive system fixes..."
    
    # Step 1: Fix port conflicts
    echo "=== STEP 1: Fixing Port Conflicts ==="
    fix_port_conflicts_comprehensive
    
    # Step 2: Install psutil
    echo "=== STEP 2: Installing psutil ==="
    install_psutil_everywhere
    
    # Step 3: Enable services
    echo "=== STEP 3: Enabling Services ==="
    ensure_services_enabled
    
    # Step 4: Start services safely
    echo "=== STEP 4: Starting Services Safely ==="
    start_all_services_safely
    
    # Step 5: Verify system
    echo "=== STEP 5: Verifying System ==="
    verify_system_completely
    
    echo "🎉 All fixes completed!"
}

# Run main function
main "$@"
