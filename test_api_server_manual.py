#!/usr/bin/env python3
"""
Manual API Server Test
Run the API server manually to capture any error messages
"""

import subprocess
import sys
import time

def main():
    print("🔍 MANUAL API SERVER TEST")
    print("="*50)
    print("Running API server manually to capture error messages...")
    
    # Test 1: Check if we can import the API server
    print("\n📥 Test 1: Import API server")
    try:
        result = subprocess.run([
            "/opt/ezrec-backend/api/venv/bin/python3", 
            "-c", 
            "import api_server; print('✅ Import successful')"
        ], 
        cwd="/opt/ezrec-backend/api",
        capture_output=True,
        text=True,
        timeout=10
        )
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Import test failed: {e}")
    
    # Test 2: Run API server with error capture
    print("\n🚀 Test 2: Run API server with error capture")
    try:
        result = subprocess.run([
            "/opt/ezrec-backend/api/venv/bin/python3", 
            "api_server.py"
        ], 
        cwd="/opt/ezrec-backend/api",
        capture_output=True,
        text=True,
        timeout=15
        )
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
            
        if result.returncode == 0:
            print("✅ API server started and exited normally")
        else:
            print(f"❌ API server exited with error code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("✅ API server is running (timeout reached)")
    except Exception as e:
        print(f"❌ Error running API server: {e}")
    
    # Test 3: Check specific imports
    print("\n📦 Test 3: Check specific imports")
    imports_to_test = [
        "uvicorn",
        "fastapi", 
        "supabase",
        "boto3",
        "requests"
    ]
    
    for module in imports_to_test:
        try:
            result = subprocess.run([
                "/opt/ezrec-backend/api/venv/bin/python3", 
                "-c", 
                f"import {module}; print(f'✅ {module} imported successfully')"
            ], 
            cwd="/opt/ezrec-backend/api",
            capture_output=True,
            text=True,
            timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {module}: {result.stdout.strip()}")
            else:
                print(f"❌ {module}: {result.stderr.strip()}")
        except Exception as e:
            print(f"❌ {module}: {e}")

if __name__ == "__main__":
    main() 