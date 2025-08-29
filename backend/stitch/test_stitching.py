#!/usr/bin/env python3
"""
EZREC Stitching System Test Script
Test the complete stitching pipeline with existing videos
"""

import sys
import time
from pathlib import Path
from stitch_config import get_config, get_logger

def test_imports():
    """Test if all required modules can be imported"""
    logger = get_logger()
    
    try:
        import cv2
        logger.info(f"✅ OpenCV version: {cv2.__version__}")
    except ImportError as e:
        logger.error(f"❌ OpenCV import failed: {e}")
        return False
    
    try:
        import numpy as np
        logger.info(f"✅ NumPy version: {np.__version__}")
    except ImportError as e:
        logger.error(f"❌ NumPy import failed: {e}")
        return False
    
    try:
        from stitch import PanoramicStitcher
        logger.info("✅ PanoramicStitcher import successful")
    except ImportError as e:
        logger.error(f"❌ PanoramicStitcher import failed: {e}")
        return False
    
    return True

def test_calibration():
    """Test if calibration file exists and is valid"""
    logger = get_logger()
    config = get_config()
    
    homography_path = config.get_homography_path()
    
    if not homography_path.exists():
        logger.warning(f"⚠️ Homography file not found: {homography_path}")
        logger.info("Run calibration first:")
        logger.info("1. Extract frames: python3 calibrate_from_videos.py <left_video> <right_video>")
        logger.info("2. Calibrate: python3 calibrate_homography.py calibration/left_frame.jpg calibration/right_frame.jpg")
        return False
    
    try:
        import json
        with open(homography_path, 'r') as f:
            data = json.load(f)
        
        if 'H' not in data:
            logger.error("❌ Invalid homography file: missing H matrix")
            return False
        
        H = data['H']
        if len(H) != 3 or len(H[0]) != 3:
            logger.error("❌ Invalid homography matrix dimensions")
            return False
        
        logger.info("✅ Homography file validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Homography file validation failed: {e}")
        return False

def test_stitching(left_video: str, right_video: str, output_video: str):
    """Test the complete stitching pipeline"""
    logger = get_logger()
    
    try:
        from stitch import PanoramicStitcher
        
        # Check if videos exist
        for video_path in [left_video, right_video]:
            if not Path(video_path).exists():
                logger.error(f"❌ Video file not found: {video_path}")
                return False
        
        # Get homography path
        config = get_config()
        homography_path = config.get_homography_path()
        
        if not homography_path.exists():
            logger.error(f"❌ Homography file not found: {homography_path}")
            return False
        
        logger.info("🎬 Starting stitching test...")
        logger.info(f"Left video: {left_video}")
        logger.info(f"Right video: {right_video}")
        logger.info(f"Output: {output_video}")
        logger.info(f"Homography: {homography_path}")
        
        # Create stitcher
        stitcher = PanoramicStitcher(str(homography_path))
        
        # Perform stitching
        start_time = time.time()
        stitcher.stitch_streams(left_video, right_video, output_video)
        total_time = time.time() - start_time
        
        # Verify output
        if Path(output_video).exists():
            file_size = Path(output_video).stat().st_size
            logger.info(f"✅ Stitching test completed successfully!")
            logger.info(f"📊 Output size: {file_size:,} bytes")
            logger.info(f"⏱️ Total time: {total_time:.1f} seconds")
            return True
        else:
            logger.error("❌ Stitching test failed: output file not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ Stitching test failed: {e}")
        return False

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test EZREC stitching system")
    parser.add_argument("--left-video", help="Left camera video for testing")
    parser.add_argument("--right-video", help="Right camera video for testing")
    parser.add_argument("--output-video", default="test_stitched.mp4", 
                       help="Output video for testing")
    parser.add_argument("--full-test", action="store_true", 
                       help="Run full stitching test with videos")
    
    args = parser.parse_args()
    
    logger = get_logger()
    logger.info("🧪 Starting EZREC stitching system test...")
    
    # Test 1: Module imports
    logger.info("\n--- Test 1: Module Imports ---")
    if not test_imports():
        logger.error("❌ Module import test failed")
        sys.exit(1)
    
    # Test 2: Calibration validation
    logger.info("\n--- Test 2: Calibration Validation ---")
    if not test_calibration():
        logger.warning("⚠️ Calibration test failed - run calibration first")
        if not args.full_test:
            logger.info("Basic tests completed. Run with --full-test to test stitching.")
            sys.exit(0)
    
    # Test 3: Full stitching (if videos provided)
    if args.full_test and args.left_video and args.right_video:
        logger.info("\n--- Test 3: Full Stitching Test ---")
        if test_stitching(args.left_video, args.right_video, args.output_video):
            logger.info("🎉 All tests passed! Stitching system is working correctly.")
        else:
            logger.error("❌ Stitching test failed")
            sys.exit(1)
    elif args.full_test:
        logger.error("❌ Full test requires --left-video and --right-video")
        sys.exit(1)
    else:
        logger.info("\n✅ Basic tests completed successfully!")
        logger.info("💡 To test full stitching, run:")
        logger.info("   python3 test_stitching.py --full-test --left-video <left.mp4> --right-video <right.mp4>")

if __name__ == "__main__":
    main() 