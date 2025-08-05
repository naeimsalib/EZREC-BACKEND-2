#!/usr/bin/env python3
"""
SETUP CLOUDFLARE TUNNEL
Installs and configures cloudflared to forward api.ezrec.org to localhost:9000
"""

import subprocess
import os
import sys
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
    print("🚀 SETTING UP CLOUDFLARE TUNNEL")
    print("=" * 50)
    
    # Step 1: Install cloudflared
    print("\n📦 STEP 1: Installing cloudflared...")
    if sys.platform == "darwin":  # macOS
        run_command("brew install cloudflared")
    else:  # Linux
        run_command("curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared")
        run_command("chmod +x /usr/local/bin/cloudflared")
    
    # Step 2: Login to Cloudflare
    print("\n🔐 STEP 2: Logging into Cloudflare...")
    print("Please follow the browser prompt to authenticate with Cloudflare...")
    run_command("cloudflared tunnel login")
    
    # Step 3: Create tunnel
    print("\n🌐 STEP 3: Creating tunnel...")
    tunnel_name = "ezrec-tunnel"
    run_command(f"cloudflared tunnel create {tunnel_name}")
    
    # Step 4: Get tunnel ID
    print("\n🆔 STEP 4: Getting tunnel ID...")
    result = run_command("cloudflared tunnel list", check=False)
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        tunnel_id = None
        for line in lines:
            if tunnel_name in line:
                parts = line.split()
                if len(parts) >= 1:
                    tunnel_id = parts[0]
                    break
        
        if tunnel_id:
            print(f"✅ Found tunnel ID: {tunnel_id}")
        else:
            print("❌ Could not find tunnel ID")
            return
    else:
        print("❌ Could not list tunnels")
        return
    
    # Step 5: Create config file
    print("\n⚙️ STEP 5: Creating tunnel configuration...")
    config = {
        "tunnel": tunnel_id,
        "credentials-file": f"~/.cloudflared/{tunnel_id}.json",
        "ingress": [
            {
                "hostname": "api.ezrec.org",
                "service": "http://localhost:9000"
            },
            {
                "service": "http_status:404"
            }
        ]
    }
    
    config_dir = Path.home() / ".cloudflared"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.yml"
    
    with open(config_file, 'w') as f:
        f.write(f"tunnel: {tunnel_id}\n")
        f.write(f"credentials-file: {config_dir}/{tunnel_id}.json\n")
        f.write("ingress:\n")
        f.write("  - hostname: api.ezrec.org\n")
        f.write("    service: http://localhost:9000\n")
        f.write("  - service: http_status:404\n")
    
    print(f"✅ Config created at: {config_file}")
    
    # Step 6: Create DNS record
    print("\n🌍 STEP 6: Creating DNS record...")
    run_command(f"cloudflared tunnel route dns {tunnel_name} api.ezrec.org")
    
    # Step 7: Start tunnel
    print("\n🚀 STEP 7: Starting tunnel...")
    print("Starting cloudflared tunnel in background...")
    run_command("cloudflared tunnel run ezrec-tunnel", check=False)
    
    print("\n✅ CLOUDFLARE TUNNEL SETUP COMPLETE!")
    print("=" * 50)
    print("🌐 Your API is now accessible at: https://api.ezrec.org")
    print("🔄 Tunnel is forwarding requests to: http://localhost:9000")
    print("📋 To start the tunnel manually: cloudflared tunnel run ezrec-tunnel")
    print("📋 To stop the tunnel: pkill cloudflared")

if __name__ == "__main__":
    main() 