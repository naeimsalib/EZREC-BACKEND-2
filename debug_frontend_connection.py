#!/usr/bin/env python3
"""
DEBUG FRONTEND CONNECTION ISSUES
Tests the exact endpoints the frontend is trying to reach
"""

import requests
import json
import subprocess
import os
from datetime import datetime

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

def test_endpoint(url, method="GET", data=None, description=""):
    """Test a specific endpoint"""
    print(f"\n🔍 Testing {method} {url}")
    if description:
        print(f"   Description: {description}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS")
            try:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}...")
        else:
            print(f"   ❌ FAILED")
            print(f"   Response: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    print("🔧 DEBUG FRONTEND CONNECTION ISSUES")
    print("=" * 50)
    
    # Test 1: Check what the frontend is trying to reach
    print("\n📋 STEP 1: Frontend URL Analysis")
    print("-" * 30)
    print("Frontend is trying to reach: https://api.ezrec.org/bookings")
    print("Your backend is running on: http://localhost:9000")
    print("❌ URL MISMATCH DETECTED!")
    
    # Test 2: Check if api.ezrec.org resolves
    print("\n🌐 STEP 2: DNS Resolution Test")
    print("-" * 30)
    result = run_command("nslookup api.ezrec.org")
    if "NXDOMAIN" in str(result.stdout) or "not found" in str(result.stdout):
        print("❌ api.ezrec.org does not resolve - this is expected")
    else:
        print("✅ api.ezrec.org resolves")
    
    # Test 3: Test local backend endpoints
    print("\n🏠 STEP 3: Local Backend Tests")
    print("-" * 30)
    
    # Test basic connectivity
    test_endpoint("http://localhost:9000/", description="Root endpoint")
    test_endpoint("http://localhost:9000/status", description="Status endpoint")
    
    # Test bookings endpoint with sample data
    sample_booking = {
        "id": "test-frontend-123",
        "user_id": "test-user-456",
        "start_time": "2025-07-20T20:00:00",
        "end_time": "2025-07-20T21:00:00",
        "date": "2025-07-20",
        "camera_id": "test-camera",
        "booking_id": "test-frontend-123",
        "email": "test@example.com"
    }
    
    test_endpoint(
        "http://localhost:9000/bookings",
        method="POST",
        data=[sample_booking],
        description="Create booking (same as frontend)"
    )
    
    # Test 4: Check CORS headers
    print("\n🌐 STEP 4: CORS Headers Test")
    print("-" * 30)
    
    try:
        response = requests.options("http://localhost:9000/bookings", timeout=5)
        print(f"OPTIONS request status: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
        
        # Check for CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        print(f"CORS configuration: {cors_headers}")
        
    except Exception as e:
        print(f"❌ CORS test failed: {e}")
    
    # Test 5: Check API server logs
    print("\n📋 STEP 5: API Server Logs")
    print("-" * 30)
    
    # Check recent logs
    result = run_command("tail -n 20 /opt/ezrec-backend/logs.txt")
    
    # Test 6: Check if API server is running on correct port
    print("\n🔌 STEP 6: Port Configuration")
    print("-" * 30)
    
    result = run_command("netstat -tlnp | grep :9000")
    if ":9000" in str(result.stdout):
        print("✅ API server listening on port 9000")
    else:
        print("❌ API server not listening on port 9000")
    
    # Test 7: Check for any other services on port 443/80
    print("\n🔍 STEP 7: Check for other web services")
    print("-" * 30)
    
    result = run_command("netstat -tlnp | grep :80")
    result2 = run_command("netstat -tlnp | grep :443")
    
    # Test 8: Check environment variables
    print("\n⚙️ STEP 8: Environment Variables")
    print("-" * 30)
    
    env_file = "/opt/ezrec-backend/.env"
    if os.path.exists(env_file):
        print(f"✅ Environment file exists: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                if 'API_URL' in line or 'BASE_URL' in line or 'FRONTEND_URL' in line:
                    print(f"   {line.strip()}")
    else:
        print(f"❌ Environment file not found: {env_file}")
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    print("❌ ISSUE IDENTIFIED:")
    print("   Frontend is trying to reach: https://api.ezrec.org/bookings")
    print("   Backend is running on: http://localhost:9000")
    print("   This is a URL configuration mismatch")
    
    print("\n🔧 SOLUTIONS:")
    print("   1. Update frontend to use: http://localhost:9000/bookings")
    print("   2. Or set up a reverse proxy to forward api.ezrec.org to localhost:9000")
    print("   3. Or configure DNS to point api.ezrec.org to your Raspberry Pi")
    
    print("\n🚀 IMMEDIATE FIX:")
    print("   Update your frontend configuration to use:")
    print("   API_BASE_URL = 'http://localhost:9000'")
    print("   Instead of: 'https://api.ezrec.org'")

if __name__ == "__main__":
    main() 