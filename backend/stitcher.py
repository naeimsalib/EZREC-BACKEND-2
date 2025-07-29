#!/usr/bin/env python3
"""
EZREC Video Stitcher Service
Handles post-record stitching with feathered blend and fallback options
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Add API directory to path for imports
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

# Load environment
load_dotenv("/opt/ezrec-backend/.env")

# Configuration
@dataclass
class StitcherConfig:
    """Stitcher configuration settings"""
    INPUT_DIR = Path("/opt/ezrec-backend/recordings")
    OUTPUT_DIR = Path("/opt/ezrec-backend/processed")
    LOG_FILE = Path("/opt/ezrec-backend/logs/stitcher.log")
    FRAMERATE = 30
    OVERLAP_WIDTH = 50  # Width of feathered blend region
    MIN_FILE_SIZE = 100 * 1024  # 100KB minimum file size

# Setup logging
def setup_logging():
    """Setup rotating file logger"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory
    StitcherConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        StitcherConfig.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_handler.setFormatter(formatter)
    
    # Setup logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[rotating_handler, logging.StreamHandler()]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

class VideoStitcher:
    """Handles video stitching with feathered blend and fallback options"""
    
    def __init__(self):
        self.opencv_available = self._check_opencv_availability()
        logger.info(f"🔧 OpenCV available: {self.opencv_available}")
    
    def _check_opencv_availability(self) -> bool:
        """Check if OpenCV is available for advanced stitching"""
        try:
            import cv2
            import numpy as np
            return True
        except ImportError:
            logger.warning("⚠️ OpenCV not available, will use FFmpeg fallback")
            return False
    
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video information using ffprobe"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(video_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
        except Exception as e:
            logger.warning(f"⚠️ Error getting video info for {video_path}: {e}")
            return {}
    
    def validate_input_files(self, video1_path: Path, video2_path: Path) -> bool:
        """Validate input video files"""
        try:
            # Check if files exist
            if not video1_path.exists():
                logger.error(f"❌ Video 1 not found: {video1_path}")
                return False
            
            if not video2_path.exists():
                logger.error(f"❌ Video 2 not found: {video2_path}")
                return False
            
            # Check file sizes
            size1 = video1_path.stat().st_size
            size2 = video2_path.stat().st_size
            
            if size1 < StitcherConfig.MIN_FILE_SIZE:
                logger.error(f"❌ Video 1 too small: {size1:,} bytes (min: {StitcherConfig.MIN_FILE_SIZE:,})")
                return False
            
            if size2 < StitcherConfig.MIN_FILE_SIZE:
                logger.error(f"❌ Video 2 too small: {size2:,} bytes (min: {StitcherConfig.MIN_FILE_SIZE:,})")
                return False
            
            logger.info(f"✅ Input files validated:")
            logger.info(f"   Video 1: {video1_path.name} ({size1:,} bytes)")
            logger.info(f"   Video 2: {video2_path.name} ({size2:,} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating input files: {e}")
            return False
    
    def stitch_with_opencv(self, video1_path: Path, video2_path: Path, output_path: Path) -> bool:
        """Stitch videos using OpenCV with feathered blend"""
        try:
            import cv2
            import numpy as np
            
            logger.info("🎬 Starting OpenCV stitching with feathered blend...")
            
            # Open video captures
            cap1 = cv2.VideoCapture(str(video1_path))
            cap2 = cv2.VideoCapture(str(video2_path))
            
            if not cap1.isOpened():
                logger.error(f"❌ Cannot open video 1: {video1_path}")
                return False
            
            if not cap2.isOpened():
                logger.error(f"❌ Cannot open video 2: {video2_path}")
                return False
            
            # Get video properties
            width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
            height1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps1 = cap1.get(cv2.CAP_PROP_FPS)
            
            width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
            height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps2 = cap2.get(cv2.CAP_PROP_FPS)
            
            # Use the larger dimensions
            output_width = max(width1, width2)
            output_height = max(height1, height2)
            output_fps = max(fps1, fps2, StitcherConfig.FRAMERATE)
            
            logger.info(f"📊 Video properties:")
            logger.info(f"   Video 1: {width1}x{height1} @ {fps1:.2f} fps")
            logger.info(f"   Video 2: {width2}x{height2} @ {fps2:.2f} fps")
            logger.info(f"   Output: {output_width*2}x{output_height} @ {output_fps:.2f} fps")
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(
                str(output_path), 
                fourcc, 
                output_fps, 
                (output_width * 2 - StitcherConfig.OVERLAP_WIDTH, output_height)
            )
            
            if not out.isOpened():
                logger.error(f"❌ Cannot create output video: {output_path}")
                return False
            
            frame_count = 0
            start_time = time.time()
            
            while True:
                # Read frames from both videos
                ret1, frame1 = cap1.read()
                ret2, frame2 = cap2.read()
                
                # Check if either video ended
                if not ret1 or not ret2:
                    logger.info(f"📹 End of video reached at frame {frame_count}")
                    break
                
                # Resize frames to match output dimensions
                frame1 = cv2.resize(frame1, (output_width, output_height))
                frame2 = cv2.resize(frame2, (output_width, output_height))
                
                # Create output frame
                output_frame = np.zeros((output_height, output_width * 2 - StitcherConfig.OVERLAP_WIDTH, 3), dtype=np.uint8)
                
                # Copy non-blend regions
                # Left side from video 1
                output_frame[:, :output_width - StitcherConfig.OVERLAP_WIDTH] = frame1[:, :output_width - StitcherConfig.OVERLAP_WIDTH]
                
                # Right side from video 2
                output_frame[:, output_width:] = frame2[:, StitcherConfig.OVERLAP_WIDTH:]
                
                # Feathered blend in overlap region
                for i in range(StitcherConfig.OVERLAP_WIDTH):
                    alpha = i / StitcherConfig.OVERLAP_WIDTH
                    col1 = frame1[:, output_width - StitcherConfig.OVERLAP_WIDTH + i]
                    col2 = frame2[:, i]
                    blended_col = ((1 - alpha) * col1 + alpha * col2).astype(np.uint8)
                    output_frame[:, output_width - StitcherConfig.OVERLAP_WIDTH + i] = blended_col
                
                # Write frame
                out.write(output_frame)
                frame_count += 1
                
                # Log progress every 100 frames
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    logger.info(f"📹 Processed {frame_count} frames ({fps:.1f} fps)")
            
            # Release resources
            cap1.release()
            cap2.release()
            out.release()
            
            # Validate output
            if output_path.exists():
                output_size = output_path.stat().st_size
                logger.info(f"✅ OpenCV stitching completed: {output_path.name} ({output_size:,} bytes)")
                logger.info(f"📊 Processed {frame_count} frames in {time.time() - start_time:.1f} seconds")
                return True
            else:
                logger.error("❌ Output file not created")
                return False
                
        except Exception as e:
            logger.error(f"❌ OpenCV stitching failed: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def stitch_with_ffmpeg(self, video1_path: Path, video2_path: Path, output_path: Path) -> bool:
        """Stitch videos using FFmpeg with hstack (fallback method)"""
        try:
            logger.info("🎬 Starting FFmpeg stitching with hstack...")
            
            # Create FFmpeg command for side-by-side merge
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video1_path),
                '-i', str(video2_path),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-an',  # No audio
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-movflags', '+faststart',
                str(output_path)
            ]
            
            logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and output_path.exists():
                output_size = output_path.stat().st_size
                logger.info(f"✅ FFmpeg stitching completed: {output_path.name} ({output_size:,} bytes)")
                return True
            else:
                logger.error(f"❌ FFmpeg stitching failed (exit code {result.returncode})")
                logger.error(f"🔧 FFmpeg stderr:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg stitching timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"❌ FFmpeg stitching error: {e}")
            return False
    
    def stitch_videos(self, video1_path: Path, video2_path: Path, output_path: Path) -> bool:
        """Main stitching method with fallback logic"""
        try:
            logger.info(f"🎬 Starting video stitching...")
            logger.info(f"   Input 1: {video1_path.name}")
            logger.info(f"   Input 2: {video2_path.name}")
            logger.info(f"   Output: {output_path.name}")
            
            # Validate input files
            if not self.validate_input_files(video1_path, video2_path):
                return False
            
            # Try OpenCV stitching first (if available)
            if self.opencv_available:
                logger.info("🎬 Attempting OpenCV stitching with feathered blend...")
                if self.stitch_with_opencv(video1_path, video2_path, output_path):
                    logger.info("✅ OpenCV stitching successful")
                    return True
                else:
                    logger.warning("⚠️ OpenCV stitching failed, falling back to FFmpeg")
            
            # Fallback to FFmpeg stitching
            logger.info("🎬 Using FFmpeg stitching (fallback method)...")
            if self.stitch_with_ffmpeg(video1_path, video2_path, output_path):
                logger.info("✅ FFmpeg stitching successful")
                return True
            else:
                logger.error("❌ Both OpenCV and FFmpeg stitching failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in video stitching: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def process_pending_stitches(self):
        """Process pending stitch jobs from the input directory"""
        try:
            if not StitcherConfig.INPUT_DIR.exists():
                logger.warning(f"⚠️ Input directory not found: {StitcherConfig.INPUT_DIR}")
                return
            
            # Look for pairs of video files to stitch
            video_files = list(StitcherConfig.INPUT_DIR.glob("*.mp4"))
            video_files.extend(list(StitcherConfig.INPUT_DIR.glob("*.h264")))
            
            # Group files by base name (assuming naming convention)
            file_groups = {}
            for video_file in video_files:
                # Extract base name (e.g., "143000_booking123_cam0" from "143000_booking123_cam0.mp4")
                base_name = video_file.stem
                if base_name.endswith('_cam0') or base_name.endswith('_cam1'):
                    group_key = base_name[:-5]  # Remove _cam0 or _cam1
                    if group_key not in file_groups:
                        file_groups[group_key] = {}
                    file_groups[group_key][base_name] = video_file
            
            # Process each group
            for group_key, files in file_groups.items():
                try:
                    # Look for cam0 and cam1 files
                    cam0_file = None
                    cam1_file = None
                    
                    for base_name, file_path in files.items():
                        if base_name.endswith('_cam0'):
                            cam0_file = file_path
                        elif base_name.endswith('_cam1'):
                            cam1_file = file_path
                    
                    if cam0_file and cam1_file:
                        # Create output path
                        output_path = StitcherConfig.OUTPUT_DIR / f"{group_key}_stitched.mp4"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Check if output already exists
                        if output_path.exists():
                            logger.info(f"⏭️ Output already exists: {output_path.name}")
                            continue
                        
                        logger.info(f"🎬 Processing stitch job: {group_key}")
                        logger.info(f"   Cam0: {cam0_file.name}")
                        logger.info(f"   Cam1: {cam1_file.name}")
                        logger.info(f"   Output: {output_path.name}")
                        
                        # Perform stitching
                        if self.stitch_videos(cam0_file, cam1_file, output_path):
                            logger.info(f"✅ Successfully stitched: {output_path.name}")
                            
                            # Clean up input files (optional)
                            # cam0_file.unlink(missing_ok=True)
                            # cam1_file.unlink(missing_ok=True)
                        else:
                            logger.error(f"❌ Failed to stitch: {group_key}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing group {group_key}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error processing pending stitches: {e}")

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    sys.exit(0)

# Register signal handlers
import signal
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    """Main application entry point"""
    logger.info("🚀 EZREC Video Stitcher Service started")
    logger.info(f"📁 Input directory: {StitcherConfig.INPUT_DIR}")
    logger.info(f"📁 Output directory: {StitcherConfig.OUTPUT_DIR}")
    logger.info(f"🎬 Framerate: {StitcherConfig.FRAMERATE}")
    logger.info(f"🔗 Overlap width: {StitcherConfig.OVERLAP_WIDTH} pixels")
    
    # Create stitcher
    stitcher = VideoStitcher()
    
    try:
        while True:
            try:
                # Process pending stitches
                stitcher.process_pending_stitches()
                
                # Wait before next check
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                import traceback
                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                time.sleep(30)  # Wait longer on error
                
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
    finally:
        logger.info("🛑 Video stitcher shutdown complete")

if __name__ == "__main__":
    main() 