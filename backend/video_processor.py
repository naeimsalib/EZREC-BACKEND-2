#!/usr/bin/env python3
"""
EZREC Video Processor Service
Handles overlay logos, intro concatenation, and video post-processing
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
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
class VideoProcessorConfig:
    """Video processor configuration settings"""
    INPUT_DIR = Path("/opt/ezrec-backend/processed")
    OUTPUT_DIR = Path("/opt/ezrec-backend/final")
    ASSETS_DIR = Path("/opt/ezrec-backend/assets")
    LOG_FILE = Path("/opt/ezrec-backend/logs/video_processor.log")
    INTRO_VIDEO = "intro.mp4"
    SPONSOR_LOGO = "sponsor.png"
    COMPANY_LOGO = "company.png"
    MIN_FILE_SIZE = 1024 * 1024  # 1MB minimum file size

# Setup logging
def setup_logging():
    """Setup rotating file logger"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory
    VideoProcessorConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        VideoProcessorConfig.LOG_FILE,
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

class VideoProcessor:
    """Handles video post-processing including overlays and concatenation"""
    
    def __init__(self):
        self.assets_available = self._check_assets_availability()
        logger.info(f"🔧 Assets available: {self.assets_available}")
    
    def _check_assets_availability(self) -> Dict[str, bool]:
        """Check availability of required assets"""
        assets = {}
        
        # Check intro video
        intro_path = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.INTRO_VIDEO
        assets['intro_video'] = intro_path.exists()
        
        # Check sponsor logo
        sponsor_path = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.SPONSOR_LOGO
        assets['sponsor_logo'] = sponsor_path.exists()
        
        # Check company logo
        company_path = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.COMPANY_LOGO
        assets['company_logo'] = company_path.exists()
        
        logger.info(f"📁 Asset availability:")
        logger.info(f"   Intro video: {assets['intro_video']}")
        logger.info(f"   Sponsor logo: {assets['sponsor_logo']}")
        logger.info(f"   Company logo: {assets['company_logo']}")
        
        return assets
    
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
    
    def validate_input_file(self, video_path: Path) -> bool:
        """Validate input video file"""
        try:
            if not video_path.exists():
                logger.error(f"❌ Video file not found: {video_path}")
                return False
            
            file_size = video_path.stat().st_size
            if file_size < VideoProcessorConfig.MIN_FILE_SIZE:
                logger.error(f"❌ Video file too small: {file_size:,} bytes (min: {VideoProcessorConfig.MIN_FILE_SIZE:,})")
                return False
            
            # Check if it's a valid video file
            video_info = self.get_video_info(video_path)
            if not video_info.get('streams'):
                logger.error(f"❌ Invalid video file: {video_path}")
                return False
            
            logger.info(f"✅ Input file validated: {video_path.name} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating input file: {e}")
            return False
    
    def add_logo_overlays(self, input_path: Path, output_path: Path) -> bool:
        """Add logo overlays to video using FFmpeg"""
        try:
            logger.info(f"🎨 Adding logo overlays to: {input_path.name}")
            
            # Check if logos are available
            sponsor_logo = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.SPONSOR_LOGO
            company_logo = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.COMPANY_LOGO
            
            if not sponsor_logo.exists() and not company_logo.exists():
                logger.warning("⚠️ No logo files found, skipping overlay")
                # Copy input to output without overlays
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-y', '-i', str(input_path)]
            
            # Add logo inputs
            filter_complex_parts = []
            input_count = 1  # Start with 1 (main video)
            
            if sponsor_logo.exists():
                cmd.extend(['-i', str(sponsor_logo)])
                filter_complex_parts.append(f'[{input_count}:v]scale=200:-1[sponsor]')
                input_count += 1
            
            if company_logo.exists():
                cmd.extend(['-i', str(company_logo)])
                filter_complex_parts.append(f'[{input_count}:v]scale=200:-1[company]')
                input_count += 1
            
            # Build overlay chain
            current_video = '[0:v]'
            for i, logo_type in enumerate(['sponsor', 'company']):
                if (logo_type == 'sponsor' and sponsor_logo.exists()) or (logo_type == 'company' and company_logo.exists()):
                    if logo_type == 'sponsor':
                        overlay = f'{current_video}[sponsor]overlay=10:10[tmp{i+1}]'
                    else:
                        overlay = f'{current_video}[company]overlay=W-w-10:10[tmp{i+1}]'
                    filter_complex_parts.append(overlay)
                    current_video = f'[tmp{i+1}]'
            
            # Final output
            filter_complex_parts.append(f'{current_video}[v]')
            
            # Complete command
            cmd.extend([
                '-filter_complex', ';'.join(filter_complex_parts),
                '-map', '[v]',
                '-c:a', 'copy',  # Copy audio if present
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-movflags', '+faststart',
                str(output_path)
            ])
            
            logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and output_path.exists():
                output_size = output_path.stat().st_size
                logger.info(f"✅ Logo overlays added successfully: {output_path.name} ({output_size:,} bytes)")
                return True
            else:
                logger.error(f"❌ Logo overlay failed (exit code {result.returncode})")
                logger.error(f"🔧 FFmpeg stderr:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Logo overlay timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"❌ Error adding logo overlays: {e}")
            return False
    
    def create_concat_file(self, intro_path: Path, main_video_path: Path, concat_file_path: Path) -> bool:
        """Create concat.txt file for FFmpeg concatenation"""
        try:
            concat_content = f"""file '{intro_path.absolute()}'
file '{main_video_path.absolute()}'"""
            
            with open(concat_file_path, 'w') as f:
                f.write(concat_content)
            
            logger.info(f"📝 Created concat file: {concat_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating concat file: {e}")
            return False
    
    def concatenate_with_intro(self, main_video_path: Path, output_path: Path) -> bool:
        """Concatenate intro video with main video"""
        try:
            intro_path = VideoProcessorConfig.ASSETS_DIR / VideoProcessorConfig.INTRO_VIDEO
            
            if not intro_path.exists():
                logger.warning("⚠️ Intro video not found, skipping concatenation")
                # Copy main video to output
                import shutil
                shutil.copy2(main_video_path, output_path)
                return True
            
            logger.info(f"🎬 Concatenating intro with main video...")
            logger.info(f"   Intro: {intro_path.name}")
            logger.info(f"   Main: {main_video_path.name}")
            logger.info(f"   Output: {output_path.name}")
            
            # Create concat file
            concat_file = output_path.parent / "concat.txt"
            if not self.create_concat_file(intro_path, main_video_path, concat_file):
                return False
            
            # FFmpeg concatenation command
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            logger.info(f"🔧 FFmpeg concat command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            # Clean up concat file
            concat_file.unlink(missing_ok=True)
            
            if result.returncode == 0 and output_path.exists():
                output_size = output_path.stat().st_size
                logger.info(f"✅ Video concatenation completed: {output_path.name} ({output_size:,} bytes)")
                return True
            else:
                logger.error(f"❌ Video concatenation failed (exit code {result.returncode})")
                logger.error(f"🔧 FFmpeg stderr:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Video concatenation timed out after 10 minutes")
            return False
        except Exception as e:
            logger.error(f"❌ Error concatenating videos: {e}")
            return False
    
    def process_video(self, input_path: Path) -> Optional[Path]:
        """Complete video processing pipeline"""
        try:
            logger.info(f"🎬 Starting video processing: {input_path.name}")
            
            # Validate input file
            if not self.validate_input_file(input_path):
                return None
            
            # Create output directory
            VideoProcessorConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename
            base_name = input_path.stem
            if base_name.endswith('_stitched'):
                base_name = base_name[:-9]  # Remove _stitched suffix
            
            # Step 1: Add logo overlays
            with_logos_path = VideoProcessorConfig.OUTPUT_DIR / f"{base_name}_with_logos.mp4"
            if not self.add_logo_overlays(input_path, with_logos_path):
                logger.error("❌ Failed to add logo overlays")
                return None
            
            # Step 2: Concatenate with intro
            final_path = VideoProcessorConfig.OUTPUT_DIR / f"{base_name}_final.mp4"
            if not self.concatenate_with_intro(with_logos_path, final_path):
                logger.error("❌ Failed to concatenate with intro")
                return None
            
            # Clean up intermediate file
            with_logos_path.unlink(missing_ok=True)
            
            # Validate final output
            if final_path.exists():
                final_size = final_path.stat().st_size
                logger.info(f"✅ Video processing completed: {final_path.name} ({final_size:,} bytes)")
                return final_path
            else:
                logger.error("❌ Final output file not created")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error in video processing: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
    
    def process_pending_videos(self):
        """Process pending videos from the input directory"""
        try:
            if not VideoProcessorConfig.INPUT_DIR.exists():
                logger.warning(f"⚠️ Input directory not found: {VideoProcessorConfig.INPUT_DIR}")
                return
            
            # Look for stitched video files
            video_files = list(VideoProcessorConfig.INPUT_DIR.glob("*_stitched.mp4"))
            
            for video_file in video_files:
                try:
                    # Check if already processed
                    base_name = video_file.stem[:-9]  # Remove _stitched suffix
                    final_path = VideoProcessorConfig.OUTPUT_DIR / f"{base_name}_final.mp4"
                    
                    if final_path.exists():
                        logger.info(f"⏭️ Already processed: {video_file.name}")
                        continue
                    
                    logger.info(f"🎬 Processing video: {video_file.name}")
                    
                    # Process video
                    result_path = self.process_video(video_file)
                    
                    if result_path:
                        logger.info(f"✅ Successfully processed: {result_path.name}")
                        
                        # Optional: Clean up input file after successful processing
                        # video_file.unlink(missing_ok=True)
                    else:
                        logger.error(f"❌ Failed to process: {video_file.name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {video_file.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error processing pending videos: {e}")

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
    logger.info("🚀 EZREC Video Processor Service started")
    logger.info(f"📁 Input directory: {VideoProcessorConfig.INPUT_DIR}")
    logger.info(f"📁 Output directory: {VideoProcessorConfig.OUTPUT_DIR}")
    logger.info(f"📁 Assets directory: {VideoProcessorConfig.ASSETS_DIR}")
    
    # Create processor
    processor = VideoProcessor()
    
    try:
        while True:
            try:
                # Process pending videos
                processor.process_pending_videos()
                
                # Wait before next check
                time.sleep(15)  # Check every 15 seconds
                
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
        logger.info("🛑 Video processor shutdown complete")

if __name__ == "__main__":
    main() 