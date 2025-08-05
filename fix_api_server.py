#!/usr/bin/env python3
"""
Fix API Server Issues
Checks and fixes API server problems preventing camera endpoints from working
"""

import subprocess
import time
import requests
import json
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return results"""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, "", str(e)

def check_api_server():
    """Check if API server is running"""
    print("\n" + "="*60)
    print("🌐 CHECKING API SERVER STATUS")
    print("="*60)
    
    # Check if API server process is running (exclude this script)
    success, output, error = run_command(
        "ps aux | grep 'api_server.py' | grep -v grep | grep -v 'fix_api_server.py'",
        "Check if API server process is running (excluding fix script)"
    )
    
    if success and output:
        print("✅ API server process is running")
        print(f"Process info: {output}")
        return True
    else:
        print("❌ API server process is not running")
        return False

def check_api_server_service():
    """Check API server systemd service"""
    print("\n" + "="*60)
    print("🔧 CHECKING API SERVER SERVICE")
    print("="*60)
    
    # Check if there's a systemd service for the API server
    success, output, error = run_command(
        "sudo systemctl status api_server.service --no-pager 2>/dev/null || echo 'No api_server.service found'",
        "Check API server systemd service"
    )
    
    if success and "active (running)" in output:
        print("✅ API server service is running")
        return True
    elif "No api_server.service found" in output:
        print("⚠️ No API server systemd service found")
        return False
    else:
        print("❌ API server service is not running")
        return False

def check_port_9000():
    """Check if port 9000 is in use"""
    print("\n" + "="*60)
    print("🔌 CHECKING PORT 9000")
    print("="*60)
    
    success, output, error = run_command(
        "netstat -tlnp | grep :9000",
        "Check if port 9000 is in use"
    )
    
    if success and output:
        print("✅ Port 9000 is in use")
        print(f"Port info: {output}")
        return True
    else:
        print("❌ Port 9000 is not in use")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n" + "="*60)
    print("🧪 TESTING API ENDPOINTS")
    print("="*60)
    
    # Test basic connectivity
    try:
        response = requests.get("http://localhost:9000/", timeout=5)
        print(f"Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print("✅ Root endpoint responding")
        else:
            print("⚠️ Root endpoint responding but not 200")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test status endpoint
    try:
        response = requests.get("http://localhost:9000/status", timeout=5)
        print(f"Status endpoint: {response.status_code}")
        if response.status_code == 200:
            print("✅ Status endpoint responding")
        else:
            print("⚠️ Status endpoint responding but not 200")
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
    
    # Test camera status endpoint
    try:
        response = requests.get("http://localhost:9000/camera-status", timeout=5)
        print(f"Camera status endpoint: {response.status_code}")
        if response.status_code == 200:
            print("✅ Camera status endpoint responding")
            try:
                data = response.json()
                print(f"Camera data: {json.dumps(data, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
        else:
            print("⚠️ Camera status endpoint responding but not 200")
    except Exception as e:
        print(f"❌ Camera status endpoint error: {e}")

def start_api_server():
    """Start the API server"""
    print("\n" + "="*60)
    print("🚀 STARTING API SERVER")
    print("="*60)
    
    # Check if API server file exists
    api_server_path = Path("/opt/ezrec-backend/api/api_server.py")
    if not api_server_path.exists():
        print(f"❌ API server file not found at {api_server_path}")
        return False
    
    print(f"✅ API server file found at {api_server_path}")
    
    # Check if virtual environment exists
    venv_path = Path("/opt/ezrec-backend/api/venv")
    if not venv_path.exists():
        print(f"❌ Virtual environment not found at {venv_path}")
        return False
    
    print(f"✅ Virtual environment found at {venv_path}")
    
    # Start API server in background
    print("Starting API server in background...")
    success, output, error = run_command(
        "cd /opt/ezrec-backend/api && nohup /opt/ezrec-backend/api/venv/bin/python3 api_server.py > /tmp/api_server.log 2>&1 &",
        "Start API server in background"
    )
    
    if success:
        print("✅ API server started in background")
        
        # Wait a moment for server to start
        print("Waiting for server to start...")
        time.sleep(5)
        
        # Test if server is responding
        try:
            response = requests.get("http://localhost:9000/", timeout=10)
            if response.status_code == 200:
                print("✅ API server is responding")
                return True
            else:
                print(f"⚠️ API server responding but status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API server not responding: {e}")
            return False
    else:
        print("❌ Failed to start API server")
        return False

def create_api_server_service():
    """Create systemd service for API server"""
    print("\n" + "="*60)
    print("🔧 CREATING API SERVER SERVICE")
    print("="*60)
    
    service_content = '''[Unit]
Description=EZREC API Server
After=network.target

[Service]
Type=simple
User=michomanoly14892
Group=michomanoly14892
WorkingDirectory=/opt/ezrec-backend/api
Environment=PYTHONPATH=/opt/ezrec-backend/api
ExecStart=/opt/ezrec-backend/api/venv/bin/python3 api_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
'''
    
    # Write service file
    service_path = Path("/etc/systemd/system/api_server.service")
    try:
        subprocess.run(["sudo", "tee", str(service_path)], input=service_content, text=True, check=True)
        print("✅ API server service file created")
        
        # Reload systemd
        success, output, error = run_command(
            "sudo systemctl daemon-reload",
            "Reload systemd"
        )
        
        if success:
            print("✅ Systemd reloaded")
            
            # Enable and start service
            success, output, error = run_command(
                "sudo systemctl enable api_server.service",
                "Enable API server service"
            )
            
            if success:
                print("✅ API server service enabled")
                
                success, output, error = run_command(
                    "sudo systemctl start api_server.service",
                    "Start API server service"
                )
                
                if success:
                    print("✅ API server service started")
                    
                    # Wait for service to start
                    time.sleep(3)
                    
                    # Check service status
                    success, output, error = run_command(
                        "sudo systemctl status api_server.service --no-pager",
                        "Check API server service status"
                    )
                    
                    if success and "active (running)" in output:
                        print("✅ API server service is running")
                        return True
                    else:
                        print("❌ API server service failed to start")
                        return False
                else:
                    print("❌ Failed to start API server service")
                    return False
            else:
                print("❌ Failed to enable API server service")
                return False
        else:
            print("❌ Failed to reload systemd")
            return False
    except Exception as e:
        print(f"❌ Failed to create service file: {e}")
        return False

def main():
    """Main function"""
    print("🚀 API SERVER DIAGNOSIS AND FIX")
    print("="*60)
    print("Checking and fixing API server issues...")
    
    # Check current status
    api_running = check_api_server()
    service_running = check_api_server_service()
    port_in_use = check_port_9000()
    
    print(f"\n📊 Current Status:")
    print(f"API Process: {'✅ Running' if api_running else '❌ Not Running'}")
    print(f"API Service: {'✅ Running' if service_running else '❌ Not Running'}")
    print(f"Port 9000: {'✅ In Use' if port_in_use else '❌ Not In Use'}")
    
    # Test endpoints
    test_api_endpoints()
    
    # If API is not running, try to start it
    if not api_running and not service_running:
        print(f"\n🔧 API server is not running. Attempting to start...")
        
        # Try to start API server directly first
        if start_api_server():
            print("✅ API server started successfully")
        else:
            print("⚠️ Direct start failed, trying systemd service...")
            
            # Create and start systemd service
            if create_api_server_service():
                print("✅ API server service created and started")
            else:
                print("❌ Failed to create and start API server service")
    
    # Final test
    print(f"\n🧪 Final API endpoint test:")
    test_api_endpoints()
    
    print(f"\n📋 Summary:")
    if api_running or service_running:
        print("✅ API server is running")
    else:
        print("❌ API server is not running")
    
    if port_in_use:
        print("✅ Port 9000 is in use")
    else:
        print("❌ Port 9000 is not in use")

if __name__ == "__main__":
    main() 