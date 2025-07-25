#!/usr/bin/env python3
"""
Enhanced Video Merge with Retry Logic
- Robust FFmpeg merging with retry capabilities
- Better error handling and validation
- Progress tracking and logging
- Automatic cleanup on failure
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

class MergeStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"

@dataclass
class MergeResult:
    success: bool
    status: MergeStatus
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    file_size: int = 0
    duration: Optional[float] = None
    retry_count: int = 0
    merge_time: Optional[float] = None

class EnhancedVideoMerger:
    """Enhanced video merger with retry logic and validation"""
    
    def __init__(self, max_retries: int = 3, timeout: int = 300):
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Validate FFmpeg availability
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def _validate_input_files(self, video1_path: Path, video2_path: Path) -> Tuple[bool, str]:
        """Validate input video files"""
        try:
            # Check if files exist
            if not video1_path.exists():
                return False, f"Video 1 not found: {video1_path}"
            if not video2_path.exists():
                return False, f"Video 2 not found: {video2_path}"
            
            # Check file sizes (minimum 500KB each)
            min_size = 500 * 1024
            size1 = video1_path.stat().st_size
            size2 = video2_path.stat().st_size
            
            if size1 < min_size:
                return False, f"Video 1 too small: {size1} bytes (min: {min_size})"
            if size2 < min_size:
                return False, f"Video 2 too small: {size2} bytes (min: {min_size})"
            
            # Validate video files with ffprobe
            for i, video_path in enumerate([video1_path, video2_path], 1):
                try:
                    result = subprocess.run([
                        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=codec_name,width,height', '-of', 'json',
                        str(video_path)
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode != 0:
                        return False, f"Video {i} validation failed: {result.stderr}"
                    
                    # Parse JSON response
                    probe_data = json.loads(result.stdout)
                    if 'streams' not in probe_data or not probe_data['streams']:
                        return False, f"Video {i} has no video streams"
                        
                except Exception as e:
                    return False, f"Video {i} validation error: {e}"
            
            return True, "Validation passed"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def _get_video_info(self, video_path: Path) -> Dict[str, Any]:
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
            self.logger.warning(f"Failed to get video info for {video_path}: {e}")
            return {}
    
    def _create_merge_command(self, video1_path: Path, video2_path: Path, 
                            output_path: Path, method: str = 'side_by_side') -> list:
        """Create FFmpeg merge command"""
        
        # Get video info for optimal settings
        info1 = self._get_video_info(video1_path)
        info2 = self._get_video_info(video2_path)
        
        # Determine optimal resolution and bitrate
        width1 = height1 = width2 = height2 = 1920
        if info1.get('streams'):
            stream1 = info1['streams'][0]
            width1 = int(stream1.get('width', 1920))
            height1 = int(stream1.get('height', 1080))
        
        if info2.get('streams'):
            stream2 = info2['streams'][0]
            width2 = int(stream2.get('width', 1920))
            height2 = int(stream2.get('height', 1080))
        
        # Use the larger dimensions for output
        output_width = max(width1, width2)
        output_height = max(height1, height2)
        
        # Calculate bitrate (higher for dual camera)
        target_bitrate = "8000k"  # 8 Mbps for dual camera
        
        if method == 'side_by_side':
            # Side-by-side merge (horizontal stack)
            filter_complex = f'[0:v][1:v]hstack=inputs=2:shortest=1[v]'
            output_width *= 2  # Double width for side-by-side
        elif method == 'stacked':
            # Top-bottom merge (vertical stack)
            filter_complex = f'[0:v][1:v]vstack=inputs=2:shortest=1[v]'
            output_height *= 2  # Double height for stacked
        else:
            # Default to side-by-side
            filter_complex = f'[0:v][1:v]hstack=inputs=2:shortest=1[v]'
            output_width *= 2
        
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-i', str(video1_path),
            '-i', str(video2_path),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-an',  # No audio to avoid errors
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Fast encoding
            '-crf', '23',  # Good quality
            '-b:v', target_bitrate,
            '-maxrate', target_bitrate,
            '-bufsize', '16000k',
            '-pix_fmt', 'yuv420p',  # Ensure compatibility
            '-movflags', '+faststart',  # Optimize for streaming
            '-metadata', f'merge_method={method}',
            '-metadata', f'camera1={video1_path.name}',
            '-metadata', f'camera2={video2_path.name}',
            str(output_path)
        ]
        
        return cmd
    
    def merge_videos(self, video1_path: Path, video2_path: Path, 
                    output_path: Path, method: str = 'side_by_side') -> MergeResult:
        """Merge two videos with retry logic and validation"""
        
        start_time = time.time()
        result = MergeResult(
            success=False,
            status=MergeStatus.PENDING,
            output_path=output_path
        )
        
        # Validate input files
        valid, error_msg = self._validate_input_files(video1_path, video2_path)
        if not valid:
            result.status = MergeStatus.FAILED
            result.error_message = error_msg
            self.logger.error(f"❌ Input validation failed: {error_msg}")
            return result
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing output file if it exists
        if output_path.exists():
            output_path.unlink()
        
        # Retry loop
        for attempt in range(self.max_retries):
            try:
                result.retry_count = attempt
                result.status = MergeStatus.IN_PROGRESS
                
                self.logger.info(f"🎬 Starting merge attempt {attempt + 1}/{self.max_retries}")
                self.logger.info(f"📹 Input 1: {video1_path.name} ({video1_path.stat().st_size:,} bytes)")
                self.logger.info(f"📹 Input 2: {video2_path.name} ({video2_path.stat().st_size:,} bytes)")
                self.logger.info(f"🎯 Output: {output_path}")
                self.logger.info(f"🔧 Method: {method}")
                
                # Create merge command
                cmd = self._create_merge_command(video1_path, video2_path, output_path, method)
                self.logger.debug(f"🔧 FFmpeg command: {' '.join(cmd)}")
                
                # Run FFmpeg
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                # Check result
                if process.returncode == 0 and output_path.exists():
                    # Validate output file
                    if self._validate_output_file(output_path):
                        result.success = True
                        result.status = MergeStatus.COMPLETED
                        result.file_size = output_path.stat().st_size
                        result.merge_time = time.time() - start_time
                        
                        # Get video duration
                        info = self._get_video_info(output_path)
                        if info.get('format', {}).get('duration'):
                            result.duration = float(info['format']['duration'])
                        
                        self.logger.info(f"✅ Merge completed successfully!")
                        self.logger.info(f"📊 Output size: {result.file_size:,} bytes")
                        self.logger.info(f"⏱️ Merge time: {result.merge_time:.2f} seconds")
                        if result.duration:
                            self.logger.info(f"🎬 Duration: {result.duration:.2f} seconds")
                        
                        return result
                    else:
                        result.error_message = "Output file validation failed"
                        self.logger.error(f"❌ Output validation failed on attempt {attempt + 1}")
                else:
                    result.error_message = f"FFmpeg failed (exit code: {process.returncode})"
                    self.logger.error(f"❌ FFmpeg failed on attempt {attempt + 1}")
                    self.logger.error(f"🔧 FFmpeg stderr:\n{process.stderr}")
                    self.logger.error(f"🔧 FFmpeg stdout:\n{process.stdout}")
                
                # Clean up failed output
                if output_path.exists():
                    output_path.unlink()
                
                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                
            except subprocess.TimeoutExpired:
                result.error_message = f"Merge timed out after {self.timeout}s"
                self.logger.error(f"❌ Merge timed out on attempt {attempt + 1}")
                
                # Kill any hanging FFmpeg processes
                try:
                    subprocess.run(['pkill', '-f', 'ffmpeg'], timeout=10)
                except:
                    pass
                
            except Exception as e:
                result.error_message = f"Unexpected error: {e}"
                self.logger.error(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
        
        # All attempts failed
        result.status = MergeStatus.FAILED
        self.logger.error(f"❌ All merge attempts failed after {self.max_retries} retries")
        return result
    
    def _validate_output_file(self, output_path: Path) -> bool:
        """Validate the merged output file"""
        try:
            if not output_path.exists():
                return False
            
            # Check minimum file size (1MB)
            min_size = 1024 * 1024
            file_size = output_path.stat().st_size
            if file_size < min_size:
                self.logger.warning(f"⚠️ Output file too small: {file_size:,} bytes (min: {min_size:,})")
                return False
            
            # Validate with ffprobe
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,width,height', '-of', 'json',
                str(output_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"❌ Output file validation failed: {result.stderr}")
                return False
            
            # Parse and validate video stream info
            probe_data = json.loads(result.stdout)
            if 'streams' not in probe_data or not probe_data['streams']:
                self.logger.error("❌ Output file has no video streams")
                return False
            
            stream = probe_data['streams'][0]
            if stream.get('codec_name') != 'h264':
                self.logger.warning(f"⚠️ Unexpected codec: {stream.get('codec_name')}")
            
            self.logger.info(f"✅ Output file validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Output validation error: {e}")
            return False
    
    def cleanup_failed_merge(self, output_path: Path):
        """Clean up files from failed merge"""
        try:
            # Remove output file
            if output_path.exists():
                output_path.unlink()
                self.logger.info(f"🗑️ Cleaned up failed output: {output_path}")
            
            # Remove any temporary files
            temp_patterns = ['.tmp', '.temp', '.part']
            for pattern in temp_patterns:
                temp_file = output_path.with_suffix(pattern)
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.info(f"🗑️ Cleaned up temp file: {temp_file}")
                    
        except Exception as e:
            self.logger.warning(f"⚠️ Cleanup error: {e}")

def merge_videos_with_retry(video1_path: Path, video2_path: Path, 
                          output_path: Path, method: str = 'side_by_side',
                          max_retries: int = 3) -> MergeResult:
    """Convenience function for merging videos with retry logic"""
    merger = EnhancedVideoMerger(max_retries=max_retries)
    return merger.merge_videos(video1_path, video2_path, output_path, method)

if __name__ == "__main__":
    # Test the enhanced merger
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Video Merger")
    parser.add_argument("video1", help="First video file")
    parser.add_argument("video2", help="Second video file")
    parser.add_argument("output", help="Output video file")
    parser.add_argument("--method", choices=["side_by_side", "stacked"], 
                       default="side_by_side", help="Merge method")
    parser.add_argument("--retries", type=int, default=3, help="Maximum retries")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run merge
    result = merge_videos_with_retry(
        Path(args.video1),
        Path(args.video2),
        Path(args.output),
        args.method,
        args.retries
    )
    
    if result.success:
        print(f"✅ Merge successful: {args.output}")
        print(f"📊 File size: {result.file_size:,} bytes")
        print(f"⏱️ Duration: {result.duration:.2f}s" if result.duration else "⏱️ Duration: unknown")
    else:
        print(f"❌ Merge failed: {result.error_message}")
        sys.exit(1) 