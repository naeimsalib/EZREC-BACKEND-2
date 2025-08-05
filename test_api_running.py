#!/usr/bin/env python3
"""
Test if API server is running and accessible
"""

import requests
import subprocess
import time
import sys

def main():
    print("🔍 TESTING API SERVER STATUS")
    print("="*40)
    
    # Check if port 9000 is in use
    print("🔍 Checking if port 9000 is in use...")
    try:
        result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
        if "9000" in result.stdout:
            print("✅ Port 9000 is in use")
            for line in result.stdout.split('\n'):
                if "9000" in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ Port 9000 is not in use")
    except Exception as e:
        print(f"⚠️ Could not check port usage: {e}")
    
    # Check for API server processes
    print("\n🔍 Checking for API server processes...")
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        api_processes = []
        for line in result.stdout.split('\n'):
            if "api_server" in line or "uvicorn" in line:
                api_processes.append(line.strip())
        
        if api_processes:
            print("✅ Found API server processes:")
            for proc in api_processes:
                print(f"   {proc}")
        else:
            print("❌ No API server processes found")
    except Exception as e:
        print(f"⚠️ Could not check processes: {e}")
    
    # Try to connect to the API server
    print("\n🔍 Testing API server connection...")
    try:
        response = requests.get("http://localhost:9000/status", timeout=5)
        print(f"✅ API server responded with status {response.status_code}")
        print(f"   Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server on port 9000")
    except requests.exceptions.Timeout:
        print("❌ API server connection timed out")
    except Exception as e:
        print(f"❌ Error connecting to API server: {e}")
    
    # Try to connect to camera status endpoint
    print("\n🔍 Testing camera status endpoint...")
    try:
        response = requests.get("http://localhost:9000/camera-status", timeout=5)
        print(f"✅ Camera status endpoint responded with status {response.status_code}")
        print(f"   Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to camera status endpoint")
    except requests.exceptions.Timeout:
        print("❌ Camera status endpoint timed out")
    except Exception as e:
        print(f"❌ Error connecting to camera status endpoint: {e}")
    
    # Check if we can start the API server manually
    print("\n🔍 Testing manual API server start...")
    try:
        # Start API server in background
        process = subprocess.Popen([
            "/opt/ezrec-backend/api/venv/bin/python3",
            "/opt/ezrec-backend/api/api_server.py"
        ], 
        cwd="/opt/ezrec-backend/api",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ API server started successfully")
            
            # Try to connect
            try:
                response = requests.get("http://localhost:9000/status", timeout=5)
                print(f"✅ API server is responding: {response.status_code}")
                print(f"   Response: {response.json()}")
            except Exception as e:
                print(f"❌ API server not responding: {e}")
            
            # Kill the process
            process.terminate()
            process.wait()
            print("✅ API server stopped")
        else:
            stdout, stderr = process.communicate()
            print(f"❌ API server failed to start")
            print(f"   Exit code: {process.returncode}")
            if stdout:
                print(f"   Stdout: {stdout.decode()}")
            if stderr:
                print(f"   Stderr: {stderr.decode()}")
                
    except Exception as e:
        print(f"❌ Error testing API server start: {e}")

if __name__ == "__main__":
    main() 