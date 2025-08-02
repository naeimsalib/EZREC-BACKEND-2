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
    
    def _comprehensive_mp4_validation(self, file_path: Path) -> Tuple[bool, str]:
        """Comprehensive MP4 validation with detailed error reporting"""
        try:
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size < 1024:  # Less than 1KB
                return False, f"File too small: {file_size} bytes"
            
            # Check file header (MP4 files should start with 'ftyp')
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'\x00\x00\x00'):
                    return False, "Invalid MP4 header"
            
            # Use ffprobe for detailed validation
            result = subprocess.run([
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,width,height,duration',
                '-show_entries', 'format=duration,size',
                '-of', 'json',
                str(file_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return False, f"FFprobe validation failed: {result.stderr}"
            
            # Parse JSON response
            try:
                probe_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return False, "Invalid JSON response from ffprobe"
            
            # Check for video streams
            if 'streams' not in probe_data or not probe_data['streams']:
                return False, "No video streams found"
            
            # Check for format information
            if 'format' not in probe_data:
                return False, "No format information found"
            
            # Check duration
            format_info = probe_data['format']
            if 'duration' in format_info:
                duration = float(format_info['duration'])
                if duration < 0.1:  # Less than 0.1 seconds
                    return False, f"Video too short: {duration:.2f} seconds"
            
            return True, "Validation passed"
            
        except Exception as e:
            return False, f"Validation error: {e}"

    def _attempt_mp4_repair(self, video_path: Path) -> bool:
        """Attempt to repair a potentially corrupted MP4 file"""
        try:
            self.logger.info(f"🔧 Attempting to repair MP4 file: {video_path}")
            
            # Create backup of original file
            backup_path = video_path.with_suffix('.backup.mp4')
            import shutil
            shutil.copy2(video_path, backup_path)
            
            # Try to repair using FFmpeg
            repair_cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-c', 'copy',  # Copy streams without re-encoding
                '-movflags', '+faststart',  # Optimize for streaming
                str(video_path.with_suffix('.repaired.mp4'))
            ]
            
            result = subprocess.run(repair_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Replace original with repaired version
                video_path.unlink()
                video_path.with_suffix('.repaired.mp4').rename(video_path)
                backup_path.unlink()  # Remove backup
                self.logger.info(f"✅ MP4 repair successful: {video_path}")
                return True
            else:
                # Restore original file
                backup_path.rename(video_path)
                self.logger.error(f"❌ MP4 repair failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ MP4 repair error: {e}")
            return False

    def is_valid_mp4(self, file_path: Path) -> bool:
        """Check if input file is a valid MP4 before FFmpeg processing"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode == 0:
                return True
            else:
                # Try to repair the file if validation fails
                self.logger.warning(f"⚠️ MP4 validation failed, attempting repair: {file_path}")
                if self._attempt_mp4_repair(file_path):
                    # Re-validate after repair
                    result = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                         "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30
                    )
                    return result.returncode == 0
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating mp4 {file_path}: {e}")
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
            
            # Validate video files with comprehensive validation
            for i, video_path in enumerate([video1_path, video2_path], 1):
                valid, error_msg = self._comprehensive_mp4_validation(video_path)
                if not valid:
                    # Try to repair the file if validation fails
                    self.logger.warning(f"⚠️ Video {i} validation failed: {error_msg}")
                    if self._attempt_mp4_repair(video_path):
                        # Re-validate after repair
                        valid, error_msg = self._comprehensive_mp4_validation(video_path)
                        if not valid:
                            return False, f"Video {i} repair failed: {error_msg}"
                        else:
                            self.logger.info(f"✅ Video {i} repaired successfully")
                    else:
                        return False, f"Video {i} is not a valid MP4 file and repair failed: {video_path}"
            
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
        
        # Dynamic feather width with edge trimming for lens distortion
        feather_width = 100  # Can be made configurable
        edge_trim = 5  # Crop 5px from edges to mask lens distortion
        
        self.logger.info(f"🎨 Using feathered blend merge:")
        self.logger.info(f"   - Feather width: {feather_width}px")
        self.logger.info(f"   - Edge trim: {edge_trim}px")
        self.logger.info(f"   - Method: {method}")
        self.logger.info(f"   - Output dimensions: {output_width}x{output_height}")
        
        if method == 'side_by_side':
            # Advanced feathered blend merge for seamless wide-angle effect
            # Creates dynamic feathered overlap with linear alpha gradient
            crop_width = output_width - feather_width
            filter_complex = (
                f'[0:v]crop=w={crop_width - edge_trim}:h={output_height}:x=0:y=0[left]; '
                f'[0:v]crop=w={feather_width}:h={output_height}:x={crop_width - edge_trim}:y=0[overlapL]; '
                f'[1:v]crop=w={feather_width}:h={output_height}:x=0:y=0[overlapR]; '
                f'[1:v]crop=w={crop_width - edge_trim}:h={output_height}:x={feather_width + edge_trim}:y=0[right]; '
                f'[overlapL][overlapR]blend=all_expr=A*(1-x/w)+B*(x/w)[blended]; '
                f'[left][blended][right]hstack=inputs=3,format=yuv420p[v]'
            )
            output_width = (output_width * 2) - feather_width  # Account for overlap
        elif method == 'stacked':
            # Top-bottom merge with dynamic feathered blend
            crop_height = output_height - feather_width
            filter_complex = (
                f'[0:v]crop=w={output_width}:h={crop_height - edge_trim}:x=0:y=0[top]; '
                f'[0:v]crop=w={output_width}:h={feather_width}:x=0:y={crop_height - edge_trim}[overlapT]; '
                f'[1:v]crop=w={output_width}:h={feather_width}:x=0:y=0[overlapB]; '
                f'[1:v]crop=w={output_width}:h={crop_height - edge_trim}:x=0:y={feather_width + edge_trim}[bottom]; '
                f'[overlapT][overlapB]blend=all_expr=A*(1-y/h)+B*(y/h)[blended]; '
                f'[top][blended][bottom]vstack=inputs=3,format=yuv420p[v]'
            )
            output_height = (output_height * 2) - feather_width  # Account for overlap
        else:
            # Default to side-by-side with dynamic feathered blend
            crop_width = output_width - feather_width
            filter_complex = (
                f'[0:v]crop=w={crop_width - edge_trim}:h={output_height}:x=0:y=0[left]; '
                f'[0:v]crop=w={feather_width}:h={output_height}:x={crop_width - edge_trim}:y=0[overlapL]; '
                f'[1:v]crop=w={feather_width}:h={output_height}:x=0:y=0[overlapR]; '
                f'[1:v]crop=w={crop_width - edge_trim}:h={output_height}:x={feather_width + edge_trim}:y=0[right]; '
                f'[overlapL][overlapR]blend=all_expr=A*(1-x/w)+B*(x/w)[blended]; '
                f'[left][blended][right]hstack=inputs=3,format=yuv420p[v]'
            )
            output_width = (output_width * 2) - feather_width  # Account for overlap
        
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