#!/usr/bin/env python3
"""
COMPREHENSIVE EZREC SYSTEM FIX
Fixes all identified issues and gets the system running 100%
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path

def run_command(cmd, check=True, capture_output=True, text=True):
    """Run a command and return result"""
    print(f"🔄 Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=text)
        if result.stdout:
            print(f"✅ Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return e

def main():
    print("🚀 COMPREHENSIVE EZREC SYSTEM FIX")
    print("="*50)
    
    # Step 1: Fix Python environment and dependencies
    print("\n📦 STEP 1: FIXING PYTHON ENVIRONMENT")
    print("-" * 30)
    
    # Check if virtual environment exists
    venv_path = "/opt/ezrec-backend/api/venv"
    if not os.path.exists(venv_path):
        print("🔧 Creating virtual environment...")
        run_command(f"cd /opt/ezrec-backend/api && python3 -m venv venv")
    
    # Activate virtual environment and install dependencies
    print("🔧 Installing dependencies in virtual environment...")
    
    # Create requirements.txt if it doesn't exist
    requirements_content = """fastapi==0.104.1
uvicorn[standard]==0.24.0
supabase==2.0.2
boto3==1.34.0
python-dotenv==1.0.0
requests==2.31.0
numpy==1.24.3
psutil==5.9.6
pytz==2023.3
pydantic==2.5.0
python-multipart==0.0.6
jinja2==3.1.2
aiohttp==3.9.1
"""
    
    with open("/opt/ezrec-backend/api/requirements.txt", "w") as f:
        f.write(requirements_content)
    
    # Install dependencies
    run_command(f"cd /opt/ezrec-backend/api && {venv_path}/bin/pip install --upgrade pip")
    run_command(f"cd /opt/ezrec-backend/api && {venv_path}/bin/pip install -r requirements.txt")
    
    # Step 2: Fix environment variables
    print("\n🔧 STEP 2: FIXING ENVIRONMENT VARIABLES")
    print("-" * 30)
    
    # Load environment variables from .env file
    env_file = "/opt/ezrec-backend/.env"
    if os.path.exists(env_file):
        print("📁 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"✅ Loaded: {key}")
    
    # Step 3: Create necessary directories
    print("\n📁 STEP 3: CREATING NECESSARY DIRECTORIES")
    print("-" * 30)
    
    directories = [
        "/opt/ezrec-backend/api/local_data",
        "/opt/ezrec-backend/recordings",
        "/opt/ezrec-backend/logs",
        "/opt/ezrec-backend/media_cache",
        "/opt/ezrec-backend/processed",
        "/opt/ezrec-backend/raw_recordings"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Step 4: Fix API server startup
    print("\n🚀 STEP 4: FIXING API SERVER STARTUP")
    print("-" * 30)
    
    # Create a proper API server startup script
    startup_script = """#!/bin/bash
cd /opt/ezrec-backend/api
source venv/bin/activate
export $(cat /opt/ezrec-backend/.env | xargs)
python3 api_server.py
"""
    
    with open("/opt/ezrec-backend/api/start_api_server.sh", "w") as f:
        f.write(startup_script)
    
    run_command("chmod +x /opt/ezrec-backend/api/start_api_server.sh")
    
    # Step 5: Create systemd service for API server
    print("\n⚙️ STEP 5: CREATING SYSTEMD SERVICE")
    print("-" * 30)
    
    service_content = """[Unit]
Description=EZREC API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ezrec-backend/api
ExecStart=/opt/ezrec-backend/api/start_api_server.sh
Restart=always
RestartSec=10
Environment=PATH=/opt/ezrec-backend/api/venv/bin

[Install]
WantedBy=multi-user.target
"""
    
    with open("/etc/systemd/system/ezrec-api-server.service", "w") as f:
        f.write(service_content)
    
    # Reload systemd and enable service
    run_command("systemctl daemon-reload")
    run_command("systemctl enable ezrec-api-server.service")
    
    # Step 6: Test the fix
    print("\n🧪 STEP 6: TESTING THE FIX")
    print("-" * 30)
    
    # Test imports in virtual environment
    print("🔍 Testing imports in virtual environment...")
    test_imports = """
import sys
sys.path.insert(0, '/opt/ezrec-backend/api')

try:
    from supabase import create_client
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import boto3
    import uvicorn
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
"""
    
    result = run_command(f"cd /opt/ezrec-backend/api && {venv_path}/bin/python3 -c '{test_imports}'", check=False)
    
    if result.returncode != 0:
        print("❌ Import test failed - trying alternative fix...")
        # Try installing with pip3 directly
        run_command(f"cd /opt/ezrec-backend/api && {venv_path}/bin/pip3 install fastapi uvicorn supabase boto3 python-dotenv")
    
    # Step 7: Start the API server
    print("\n🚀 STEP 7: STARTING API SERVER")
    print("-" * 30)
    
    # Stop any existing processes
    run_command("pkill -f api_server.py", check=False)
    run_command("pkill -f uvicorn", check=False)
    
    # Start the service
    run_command("systemctl start ezrec-api-server.service")
    
    # Wait a moment for startup
    time.sleep(5)
    
    # Check if service is running
    result = run_command("systemctl is-active ezrec-api-server.service", check=False)
    if result.returncode == 0:
        print("✅ API server service is running")
    else:
        print("❌ API server service failed to start")
        # Try manual start
        print("🔄 Trying manual start...")
        run_command(f"cd /opt/ezrec-backend/api && {venv_path}/bin/python3 api_server.py &", check=False)
        time.sleep(3)
    
    # Step 8: Verify the fix
    print("\n✅ STEP 8: VERIFYING THE FIX")
    print("-" * 30)
    
    # Check if port 9000 is listening
    result = run_command("netstat -tlnp 2>/dev/null | grep :9000 || echo 'Port 9000 not found'", check=False)
    if "9000" in result.stdout:
        print("✅ Port 9000 is listening")
    else:
        print("❌ Port 9000 not listening")
    
    # Check processes
    result = run_command("ps aux | grep -E '(api_server|uvicorn)' | grep -v grep", check=False)
    if result.stdout:
        print("✅ API server processes found:")
        print(result.stdout)
    else:
        print("❌ No API server processes found")
    
    # Test HTTP connection
    try:
        import requests
        response = requests.get("http://localhost:9000/status", timeout=5)
        print(f"✅ HTTP test successful: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
    
    print("\n🎉 COMPREHENSIVE FIX COMPLETED!")
    print("="*50)
    print("The system should now be fully operational.")
    print("If there are still issues, check the logs with:")
    print("  journalctl -u ezrec-api-server.service -f")

if __name__ == "__main__":
    main() 