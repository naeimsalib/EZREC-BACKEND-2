#!/usr/bin/env python3
"""
Test script for video_worker cleanup functions
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_worker import cleanup_orphaned_markers, extract_booking_id_from_filename

def test_extract_booking_id_from_filename():
    """Test the extract_booking_id_from_filename function"""
    print("🧪 Testing extract_booking_id_from_filename...")
    
    test_cases = [
        ("143000_user123_cam456_merged.mp4", "user123_cam456"),
        ("143000_user123_cam456.done", "user123_cam456"),
        ("test_video.mp4", "test_video"),
        ("143000_merged.mp4", "143000_merged"),
        ("", ""),
    ]
    
    for filename, expected in test_cases:
        result = extract_booking_id_from_filename(filename)
        if result == expected:
            print(f"✅ {filename} -> {result}")
        else:
            print(f"❌ {filename} -> {result} (expected: {expected})")
            return False
    
    print("✅ All extract_booking_id_from_filename tests passed!")
    return True

def test_cleanup_orphaned_markers():
    """Test the cleanup_orphaned_markers function with temporary files"""
    print("🧪 Testing cleanup_orphaned_markers...")
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure
        test_date_dir = temp_path / "2024-01-01"
        test_date_dir.mkdir()
        
        # Create test files
        test_files = [
            # Valid case: .mp4 exists with .done
            ("valid_video.mp4", True),
            ("valid_video.done", True),
            ("valid_video.meta", True),
            
            # Orphaned case: .done exists without .mp4
            ("orphaned_video.done", True),
            ("orphaned_video.meta", True),
            ("orphaned_video.lock", True),
            
            # Another orphaned case
            ("another_orphaned.done", True),
            ("another_orphaned.error", True),
        ]
        
        for filename, should_exist in test_files:
            file_path = test_date_dir / filename
            file_path.touch()
            print(f"📝 Created test file: {filename}")
        
        # Verify files were created
        print(f"📁 Test directory contains: {list(test_date_dir.iterdir())}")
        
        # Mock the RECORDINGS_DIR to point to our temp directory
        import video_worker
        original_recordings_dir = video_worker.RECORDINGS_DIR
        video_worker.RECORDINGS_DIR = temp_path
        
        try:
            # Run cleanup
            cleanup_orphaned_markers()
            
            # Check results
            remaining_files = list(test_date_dir.iterdir())
            print(f"📁 Remaining files: {remaining_files}")
            
            # Valid files should still exist
            valid_files = ["valid_video.mp4", "valid_video.done", "valid_video.meta"]
            for filename in valid_files:
                if (test_date_dir / filename).exists():
                    print(f"✅ Valid file still exists: {filename}")
                else:
                    print(f"❌ Valid file missing: {filename}")
                    return False
            
            # Orphaned files should be removed
            orphaned_files = ["orphaned_video.done", "orphaned_video.meta", "orphaned_video.lock", 
                             "another_orphaned.done", "another_orphaned.error"]
            for filename in orphaned_files:
                if not (test_date_dir / filename).exists():
                    print(f"✅ Orphaned file correctly removed: {filename}")
                else:
                    print(f"❌ Orphaned file still exists: {filename}")
                    return False
            
            print("✅ All cleanup_orphaned_markers tests passed!")
            return True
            
        finally:
            # Restore original RECORDINGS_DIR
            video_worker.RECORDINGS_DIR = original_recordings_dir

def main():
    """Run all tests"""
    print("🚀 Starting video_worker cleanup tests...")
    
    success = True
    
    # Test filename extraction
    if not test_extract_booking_id_from_filename():
        success = False
    
    # Test cleanup function
    if not test_cleanup_orphaned_markers():
        success = False
    
    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 