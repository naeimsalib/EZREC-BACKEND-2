#!/usr/bin/env python3
"""
Test script for enhanced merge with 45-degree rotation
Demonstrates the dry run functionality to show the exact FFmpeg command
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from enhanced_merge import EnhancedVideoMerger

def test_dry_run():
    """Test the enhanced merge with 45-degree rotation using dry run"""
    
    # Create test file paths (these don't need to exist for dry run)
    video1_path = Path("test_left.mp4")
    video2_path = Path("test_right.mp4")
    output_path = Path("test_merged.mp4")
    
    print("🎬 Testing Enhanced Merge with 45° Rotation")
    print("=" * 50)
    
    # Test 1: 45-degree rotation with side_by_side method
    print("\n📹 Test 1: 45° rotation, side_by_side method")
    print("-" * 40)
    
    merger = EnhancedVideoMerger(
        max_retries=3,
        timeout=300,
        feather_width=100,
        edge_trim=5,
        target_bitrate="8000k",
        enable_distortion_correction=False,
        input_rotate_degrees=45.0
    )
    
    cmd = merger._create_merge_command(video1_path, video2_path, output_path, method='side_by_side')
    print("FFmpeg Command:")
    print(" ".join(cmd))
    
    # Test 2: 45-degree rotation with advanced_stitch method
    print("\n📹 Test 2: 45° rotation, advanced_stitch method")
    print("-" * 40)
    
    cmd = merger._create_merge_command(video1_path, video2_path, output_path, method='advanced_stitch')
    print("FFmpeg Command:")
    print(" ".join(cmd))
    
    # Test 3: No rotation for comparison
    print("\n📹 Test 3: No rotation, side_by_side method")
    print("-" * 40)
    
    merger_no_rotation = EnhancedVideoMerger(
        max_retries=3,
        timeout=300,
        feather_width=100,
        edge_trim=5,
        target_bitrate="8000k",
        enable_distortion_correction=False,
        input_rotate_degrees=0.0
    )
    
    cmd = merger_no_rotation._create_merge_command(video1_path, video2_path, output_path, method='side_by_side')
    print("FFmpeg Command:")
    print(" ".join(cmd))
    
    # Test 4: 45-degree rotation with distortion correction
    print("\n📹 Test 4: 45° rotation with distortion correction")
    print("-" * 40)
    
    merger_with_correction = EnhancedVideoMerger(
        max_retries=3,
        timeout=300,
        feather_width=100,
        edge_trim=5,
        target_bitrate="8000k",
        enable_distortion_correction=True,
        input_rotate_degrees=45.0
    )
    
    cmd = merger_with_correction._create_merge_command(video1_path, video2_path, output_path, method='side_by_side')
    print("FFmpeg Command:")
    print(" ".join(cmd))

if __name__ == "__main__":
    test_dry_run()
