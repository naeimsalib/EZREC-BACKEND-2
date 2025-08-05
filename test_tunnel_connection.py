#!/usr/bin/env python3
"""
TEST CLOUDFLARE TUNNEL CONNECTION
Tests if the tunnel is properly forwarding requests from api.ezrec.org to localhost:9000
"""

import requests
import subprocess
import time
import os

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

def test_endpoint(url, description=""):
    """Test an endpoint and return status"""
    print(f"\n🔍 Testing {description}")
    print(f"   URL: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ SUCCESS: {response.json()}")
            return True
        else:
            print(f"   ❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    print("🌐 TESTING CLOUDFLARE TUNNEL CONNECTION")
    print("=" * 50)
    
    # Step 1: Check if tunnel is running
    print("\n📋 STEP 1: Checking tunnel status...")
    result = run_command("ps aux | grep cloudflared | grep -v grep", check=False)
    if result.returncode == 0:
        print("✅ Cloudflare tunnel is running")
    else:
        print("❌ Cloudflare tunnel is NOT running")
        print("\n🚀 Starting tunnel...")
        run_command("cloudflared tunnel run ezrec-tunnel", check=False)
        time.sleep(3)  # Wait for tunnel to start
    
    # Step 2: Test local backend
    print("\n📋 STEP 2: Testing local backend...")
    local_success = test_endpoint("http://localhost:9000/", "Local backend root")
    test_endpoint("http://localhost:9000/status", "Local backend status")
    
    # Step 3: Test tunnel endpoint
    print("\n📋 STEP 3: Testing tunnel endpoint...")
    tunnel_success = test_endpoint("https://api.ezrec.org/", "Tunnel backend root")
    test_endpoint("https://api.ezrec.org/status", "Tunnel backend status")
    
    # Step 4: Test booking endpoint
    print("\n📋 STEP 4: Testing booking endpoint...")
    test_endpoint("https://api.ezrec.org/bookings", "Tunnel booking endpoint")
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 50)
    if local_success and tunnel_success:
        print("🎉 SUCCESS: Both local and tunnel endpoints are working!")
        print("✅ Frontend should now be able to connect to your backend")
        print("🌐 Frontend URL: https://api.ezrec.org")
        print("🔄 Backend URL: http://localhost:9000")
    elif local_success and not tunnel_success:
        print("⚠️  PARTIAL: Local backend works, but tunnel is not forwarding")
        print("🔧 Try restarting the tunnel: cloudflared tunnel run ezrec-tunnel")
    elif not local_success:
        print("❌ FAILED: Local backend is not responding")
        print("🔧 Check if your API server is running on port 9000")
    else:
        print("❌ FAILED: Neither local nor tunnel endpoints are working")

if __name__ == "__main__":
    main() 