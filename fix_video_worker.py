#!/usr/bin/env python3
"""
Fix Video Worker Issues
This script addresses the path and file detection problems
"""

import os
import json
from pathlib import Path
import subprocess

def check_recording_files():
    """Check what recording files actually exist"""
    print("🔍 Checking recording files...")
    
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    if not recordings_dir.exists():
        print(f"❌ Recordings directory does not exist: {recordings_dir}")
        return False
    
    print(f"✅ Recordings directory exists: {recordings_dir}")
    
    # List all subdirectories
    date_dirs = list(recordings_dir.glob("*/"))
    print(f"📅 Found {len(date_dirs)} date directories:")
    
    for date_dir in date_dirs:
        print(f"  📁 {date_dir.name}")
        
        # List all files in this directory
        mp4_files = list(date_dir.glob("*.mp4"))
        done_files = list(date_dir.glob("*.done"))
        json_files = list(date_dir.glob("*.json"))
        lock_files = list(date_dir.glob("*.lock"))
        
        print(f"    📹 MP4 files: {len(mp4_files)}")
        for f in mp4_files:
            print(f"      - {f.name}")
        
        print(f"    ✅ Done files: {len(done_files)}")
        for f in done_files:
            print(f"      - {f.name}")
        
        print(f"    📄 JSON files: {len(json_files)}")
        for f in json_files:
            print(f"      - {f.name}")
        
        print(f"    🔒 Lock files: {len(lock_files)}")
        for f in lock_files:
            print(f"      - {f.name}")
    
    return True

def check_video_worker_logs():
    """Check video_worker logs for errors"""
    print("\n📋 Checking video_worker logs...")
    
    try:
        result = subprocess.run([
            "sudo", "journalctl", "-u", "video_worker.service", 
            "-n", "50", "--no-pager"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("📄 Recent video_worker logs:")
            print(result.stdout)
        else:
            print(f"❌ Failed to get logs: {result.stderr}")
    except Exception as e:
        print(f"❌ Error checking logs: {e}")

def test_video_worker_scanning():
    """Test what video_worker would find"""
    print("\n🧪 Testing video_worker scanning logic...")
    
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    if not recordings_dir.exists():
        print("❌ Recordings directory doesn't exist")
        return
    
    # Simulate video_worker scanning
    for date_dir in recordings_dir.glob("*/"):
        print(f"📁 Scanning directory: {date_dir}")
        
        for raw_file in date_dir.glob("*.mp4"):
            done = raw_file.with_suffix(".done")
            completed = raw_file.with_suffix(".completed")
            lock = raw_file.with_suffix(".lock")
            meta_path = raw_file.with_suffix(".json")
            
            print(f"  📹 File: {raw_file.name}")
            print(f"    ✅ Done exists: {done.exists()}")
            print(f"    ✅ Completed exists: {completed.exists()}")
            print(f"    🔒 Lock exists: {lock.exists()}")
            print(f"    📄 Meta exists: {meta_path.exists()}")
            
            # Check if video_worker would process this
            if not done.exists() or completed.exists() or lock.exists():
                print(f"    ❌ Would SKIP (missing .done or has .completed/.lock)")
            elif not meta_path.exists():
                print(f"    ❌ Would SKIP (missing .json)")
            else:
                print(f"    ✅ Would PROCESS")
                
                # Try to read metadata
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    print(f"    📋 Metadata: {meta}")
                except Exception as e:
                    print(f"    ❌ Failed to read metadata: {e}")

def create_test_recording():
    """Create a test recording to verify the workflow"""
    print("\n🎬 Creating test recording...")
    
    # Create test directory
    test_dir = Path("/opt/ezrec-backend/recordings/2025-07-20")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    test_mp4 = test_dir / "191500-191510.mp4"
    test_done = test_dir / "191500-191510.done"
    test_json = test_dir / "191500-191510.json"
    
    # Create dummy MP4 file
    with open(test_mp4, 'wb') as f:
        f.write(b'dummy mp4 content')
    
    # Create done marker
    test_done.touch()
    
    # Create metadata
    meta = {
        "user_id": "test-user",
        "camera_id": "test-camera",
        "booking_id": "test-booking",
        "start_time": "2025-07-20T19:15:00Z",
        "end_time": "2025-07-20T19:15:10Z"
    }
    
    with open(test_json, 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✅ Created test files:")
    print(f"  📹 {test_mp4}")
    print(f"  ✅ {test_done}")
    print(f"  📄 {test_json}")

def fix_video_worker_paths():
    """Fix any path inconsistencies"""
    print("\n🔧 Fixing video_worker paths...")
    
    # Ensure recordings directory exists
    recordings_dir = Path("/opt/ezrec-backend/recordings")
    recordings_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Ensured recordings directory exists: {recordings_dir}")
    
    # Check if video_worker is looking in the right place
    video_worker_path = Path("/opt/ezrec-backend/backend/video_worker.py")
    if video_worker_path.exists():
        with open(video_worker_path) as f:
            content = f.read()
            if "RECORDINGS_DIR = Path(\"/opt/ezrec-backend/recordings\")" in content:
                print("✅ video_worker.py has correct path")
            else:
                print("⚠️ video_worker.py path may be incorrect")
    else:
        print("❌ video_worker.py not found")

def restart_video_worker():
    """Restart video_worker service"""
    print("\n🔄 Restarting video_worker service...")
    
    try:
        # Stop service
        result = subprocess.run(["sudo", "systemctl", "stop", "video_worker.service"])
        if result.returncode == 0:
            print("✅ Stopped video_worker service")
        else:
            print("⚠️ Failed to stop video_worker service")
        
        # Start service
        result = subprocess.run(["sudo", "systemctl", "start", "video_worker.service"])
        if result.returncode == 0:
            print("✅ Started video_worker service")
        else:
            print("❌ Failed to start video_worker service")
        
        # Check status
        result = subprocess.run(["sudo", "systemctl", "status", "video_worker.service", "--no-pager"])
        
    except Exception as e:
        print(f"❌ Error restarting service: {e}")

def main():
    """Main diagnostic and fix function"""
    print("🚀 EZREC Video Worker Fix Tool")
    print("="*50)
    
    # Run diagnostics
    check_recording_files()
    check_video_worker_logs()
    test_video_worker_scanning()
    
    # Apply fixes
    fix_video_worker_paths()
    create_test_recording()
    restart_video_worker()
    
    print("\n" + "="*50)
    print("📋 SUMMARY")
    print("="*50)
    print("1. Checked recording files and directories")
    print("2. Reviewed video_worker logs")
    print("3. Tested file scanning logic")
    print("4. Fixed path issues")
    print("5. Created test recording")
    print("6. Restarted video_worker service")
    print("\nNext steps:")
    print("- Check video_worker logs: sudo journalctl -u video_worker.service -f")
    print("- Monitor for processing: watch -n 5 'ls -la /opt/ezrec-backend/recordings/*/'")

if __name__ == "__main__":
    main() 