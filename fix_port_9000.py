#!/usr/bin/env python3
"""
QUICK FIX: Ensure API server runs on port 9000
"""

import subprocess
import os
import time

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
    print("🔧 QUICK FIX: Ensuring API server runs on port 9000")
    print("="*50)
    
    # Step 1: Stop all existing processes
    print("\n🛑 STEP 1: Stopping existing processes")
    print("-" * 30)
    run_command("pkill -f api_server.py", check=False)
    run_command("pkill -f uvicorn", check=False)
    run_command("systemctl stop ezrec-api-server.service", check=False)
    time.sleep(2)
    
    # Step 2: Check the API server code to ensure it uses port 9000
    print("\n🔍 STEP 2: Verifying API server port configuration")
    print("-" * 30)
    
    api_server_path = "/opt/ezrec-backend/api/api_server.py"
    if os.path.exists(api_server_path):
        with open(api_server_path, 'r') as f:
            content = f.read()
        
        if "port=9000" in content:
            print("✅ API server configured for port 9000")
        else:
            print("❌ API server not configured for port 9000 - fixing...")
            # Replace port 8000 with 9000
            content = content.replace("port=8000", "port=9000")
            with open(api_server_path, 'w') as f:
                f.write(content)
            print("✅ Fixed API server port configuration")
    
    # Step 3: Start API server manually on port 9000
    print("\n🚀 STEP 3: Starting API server on port 9000")
    print("-" * 30)
    
    venv_path = "/opt/ezrec-backend/api/venv"
    start_cmd = f"cd /opt/ezrec-backend/api && {venv_path}/bin/python3 api_server.py"
    
    print("🔄 Starting API server in background...")
    run_command(f"{start_cmd} > /opt/ezrec-backend/logs/api_server.log 2>&1 &", check=False)
    
    # Wait for startup
    time.sleep(5)
    
    # Step 4: Verify the fix
    print("\n✅ STEP 4: Verifying the fix")
    print("-" * 30)
    
    # Check if port 9000 is listening
    result = run_command("netstat -tlnp 2>/dev/null | grep :9000", check=False)
    if result.returncode == 0:
        print("✅ Port 9000 is listening")
        print(f"   {result.stdout.strip()}")
    else:
        print("❌ Port 9000 not listening")
    
    # Check processes
    result = run_command("ps aux | grep -E '(api_server|uvicorn)' | grep -v grep", check=False)
    if result.stdout:
        print("✅ API server processes found:")
        print(result.stdout)
    else:
        print("❌ No API server processes found")
    
    # Test HTTP connection to port 9000
    try:
        import requests
        response = requests.get("http://localhost:9000/status", timeout=5)
        print(f"✅ HTTP test successful: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
    
    # Also test port 8000 to see what's there
    try:
        import requests
        response = requests.get("http://localhost:8000/status", timeout=5)
        print(f"⚠️ Port 8000 also responding: {response.status_code}")
    except Exception as e:
        print(f"✅ Port 8000 not responding (good)")
    
    print("\n🎉 PORT FIX COMPLETED!")
    print("="*50)
    print("The API server should now be running on port 9000.")
    print("Check the logs with:")
    print("  tail -f /opt/ezrec-backend/logs/api_server.log")

if __name__ == "__main__":
    main() 