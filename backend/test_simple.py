#!/usr/bin/env python3
"""
Simple test script that doesn't require log file access
"""

import os
import sys
import tempfile
from pathlib import Path

def test_extract_booking_id():
    """Test the extract_booking_id_from_filename function"""
    print("🧪 Testing extract_booking_id_from_filename...")
    
    # Import the function
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from video_worker import extract_booking_id_from_filename
        
        test_cases = [
            ("143000_user123_cam456_merged.mp4", "user123_cam456"),
            ("143000_user123_cam456.done", "user123_cam456"),
            ("test_video.mp4", "test_video"),
            ("143000_merged.mp4", "143000_merged"),
            ("", ""),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_booking_id_from_filename(filename)
            if result == expected:
                print(f"✅ {filename} -> {result}")
            else:
                print(f"❌ {filename} -> {result} (expected: {expected})")
                all_passed = False
        
        if all_passed:
            print("✅ All extract_booking_id_from_filename tests passed!")
        else:
            print("❌ Some tests failed!")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error testing extract_booking_id_from_filename: {e}")
        return False

def test_system_status_import():
    """Test that system_status.py can be imported"""
    print("🧪 Testing system_status import...")
    
    try:
        # Temporarily modify the log file path to avoid permission issues
        original_log_file = "/opt/ezrec-backend/logs/system_status.log"
        temp_log_file = "/tmp/test_system_status.log"
        
        # Create a temporary version of system_status.py
        with open("system_status.py", "r") as f:
            content = f.read()
        
        # Replace the log file path
        content = content.replace(original_log_file, temp_log_file)
        
        # Write to temporary file
        with open("/tmp/test_system_status.py", "w") as f:
            f.write(content)
        
        # Import the modified version
        sys.path.insert(0, "/tmp")
        from test_system_status import SystemStatusMonitor
        
        print("✅ system_status.py can be imported successfully")
        
        # Clean up
        os.unlink("/tmp/test_system_status.py")
        if os.path.exists("/tmp/test_system_status.log"):
            os.unlink("/tmp/test_system_status.log")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing system_status import: {e}")
        return False

def test_basic_imports():
    """Test basic imports"""
    print("🧪 Testing basic imports...")
    
    try:
        import psutil
        print("✅ psutil imported successfully")
        
        import pytz
        print("✅ pytz imported successfully")
        
        import requests
        print("✅ requests imported successfully")
        
        import boto3
        print("✅ boto3 imported successfully")
        
        import supabase
        print("✅ supabase imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing imports: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting simple tests...")
    
    success = True
    
    # Test basic imports
    if not test_basic_imports():
        success = False
    
    # Test extract_booking_id function
    if not test_extract_booking_id():
        success = False
    
    # Test system_status import
    if not test_system_status_import():
        success = False
    
    if success:
        print("🎉 All simple tests passed!")
        return 0
    else:
        print("❌ Some simple tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 