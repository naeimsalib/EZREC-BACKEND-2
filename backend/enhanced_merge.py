#!/usr/bin/env python3
"""
Enhanced Video Merge with Retry Logic
- Robust FFmpeg merging with retry capabilities
- Better error handling and validation
- Progress tracking and logging
- Automatic cleanup on failure
- OpenCV-based panoramic stitching support
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
from datetime import datetime

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
    
    def __init__(self, max_retries: int = 3, timeout: int = 300, feather_width: int = 100, edge_trim: int = 5, target_bitrate: str = "8000k", output_resolution: tuple = None, enable_distortion_correction: bool = False, input_rotate_degrees: float = 0.0, use_opencv_stitching: bool = True):
        self.max_retries = max_retries
        self.timeout = timeout
        self.feather_width = feather_width
        self.edge_trim = edge_trim
        self.logger = logging.getLogger(__name__)
        self.target_bitrate = target_bitrate
        self.output_resolution = output_resolution
        self.enable_distortion_correction = enable_distortion_correction
        self.input_rotate_degrees = input_rotate_degrees
        self.use_opencv_stitching = use_opencv_stitching
        
        # Validate FFmpeg availability (still needed for validation)
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        # Try to import OpenCV stitching if enabled
        if self.use_opencv_stitching:
            try:
                from stitch import PanoramicStitcher
                self.logger.info("✅ OpenCV stitching available")
            except ImportError as e:
                self.logger.warning(f"⚠️ OpenCV stitching not available: {e}")
                self.logger.info("Falling back to FFmpeg stitching")
                self.use_opencv_stitching = False
    
    def _input_prefilter(self) -> str:
        """Rotate (any angle), normalize pixel aspect & height before stitching."""
        angle = self.input_rotate_degrees
        if angle:
            # radians for ffmpeg rotate filter
            rad = f"({angle}*PI/180)"
            return f"rotate={rad}:ow=rotw({rad}):oh=roth({rad}):c=black@0,scale=-2:1080,setsar=1"
        # no rotation: still normalize height and SAR
        return "scale=-2:1080,setsar=1"
    
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
                if b'ftyp' not in header:
                    return False, "Invalid MP4 header (missing ftyp)"

            
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
        try:
            self.logger.info(f"🔧 Attempting to repair MP4 file: {video_path}")
            backup_path = video_path.with_suffix('.backup.mp4')
            import shutil
            shutil.copy2(video_path, backup_path)

            repair_cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-movflags', '+faststart',
                str(video_path.with_suffix('.repaired.mp4'))
            ]

            result = subprocess.run(
                repair_cmd, check=True, timeout=self.timeout,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            self.logger.info(f"🧪 Repair FFmpeg stderr:\n{result.stderr}")

            if result.returncode == 0:
                video_path.unlink()
                video_path.with_suffix('.repaired.mp4').rename(video_path)
                backup_path.unlink()
                self.logger.info(f"✅ MP4 repair successful: {video_path}")
                return True
            else:
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
                self.logger.warning(f"⚠️ MP4 validation failed, attempting repair: {file_path}")
                if self._attempt_mp4_repair(file_path):
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
            
            # Check file sizes (minimum 10KB each for testing)
            min_size = 10 * 1024
            size1 = video1_path.stat().st_size
            size2 = video2_path.stat().st_size
            
            if size1 < 2 * min_size:
                self.logger.warning(f"⚠️ Video 1 size is low: {size1} bytes")
            if size1 < min_size:
                raise ValueError(f"Video 1 too small: {size1} bytes")

            if size2 < 2 * min_size:
                self.logger.warning(f"⚠️ Video 2 size is low: {size2} bytes")
            if size2 < min_size:
                raise ValueError(f"Video 2 too small: {size2} bytes")

            
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
        """Create FFmpeg merge command with FIXED crop width calculations"""
        
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
        
        # FIXED: Work only with per-source dimensions
        output_height = max(height1, height2)
        feather_width = self.feather_width
        edge_trim = self.edge_trim
        
        # Calculate visible (non-feather) areas for each source
        left_visible = width1 - feather_width
        right_visible = width2 - feather_width
        
        # Validate crop dimensions to prevent FFmpeg errors
        for name, w, max_w in [("left_visible", left_visible, width1),
                              ("right_visible", right_visible, width2)]:
            if w <= 0 or w > max_w:
                raise ValueError(f"{name} width={w} invalid for source dimensions (max: {max_w})")
        
        # Calculate bitrate (higher for dual camera)
        target_bitrate = self.target_bitrate
        
        # Get optimal lens correction parameters
        lens_correction = ""
        if self.enable_distortion_correction:
            lens_correction = self._get_optimal_lens_correction(video1_path, video2_path)
            self.logger.info(f"🔧 Using lens correction: {lens_correction}")
        
        # Get the prefilter for rotation and normalization
        pref = self._input_prefilter()
        
        self.logger.info(f"🎨 Using seamless panoramic merge with {self.input_rotate_degrees}° rotation:")
        self.logger.info(f"   - Source dimensions: {width1}x{height1}, {width2}x{height2}")
        self.logger.info(f"   - Input rotation: {self.input_rotate_degrees}°")
        self.logger.info(f"   - Feather width: {feather_width}px")
        self.logger.info(f"   - Edge trim: {edge_trim}px")
        self.logger.info(f"   - Method: {method}")
        self.logger.info(f"   - Distortion correction: {'enabled' if self.enable_distortion_correction else 'disabled'}")
        
        if method == 'advanced_stitch':
            # ULTRA-ADVANCED: Professional stitching with rotation support
            blend_width = self.feather_width
            
            if self.enable_distortion_correction:
                filter_complex = (
                    f"[0:v]{pref}[left];"
                    f"[1:v]{pref}[right];"
                    f"[left]crop=iw-{blend_width}:ih:0:0[left_main];"
                    f"[left]crop={blend_width}:ih:iw-{blend_width}:0[left_overlap];"
                    f"[right]crop={blend_width}:ih:0:0[right_overlap];"
                    f"[right]crop=iw-{blend_width}:ih:{blend_width}:0[right_main];"
                    f"[left_overlap][right_overlap]blend=all_expr='A*(1-X/W)+B*(X/W)'[blended];"
                    f"[left_main][blended][right_main]hstack=inputs=3[merged];"
                    f"[merged]lenscorrection={lens_correction}[v]"
                )
            else:
                filter_complex = (
                    f"[0:v]{pref}[left];"
                    f"[1:v]{pref}[right];"
                    f"[left]crop=iw-{blend_width}:ih:0:0[left_main];"
                    f"[left]crop={blend_width}:ih:iw-{blend_width}:0[left_overlap];"
                    f"[right]crop={blend_width}:ih:0:0[right_overlap];"
                    f"[right]crop=iw-{blend_width}:ih:{blend_width}:0[right_main];"
                    f"[left_overlap][right_overlap]blend=all_expr='A*(1-X/W)+B*(X/W)'[blended];"
                    f"[left_main][blended][right_main]hstack=inputs=3[out];"
                    f"[out]format=yuv420p[v]"
                )
            final_width = (width1 - blend_width) + blend_width + (width2 - blend_width)
        elif method == 'side_by_side':
            # SEAMLESS PANORAMIC: Rotation + normalization + geometric alignment + seamless blend
            blend_width = self.feather_width  # Use the configured feather width (default 100px)
            
            if self.enable_distortion_correction:
                # Professional method: Rotation + normalization + geometric alignment + seamless blend
                filter_complex = (
                    f"[0:v]{pref}[left];"
                    f"[1:v]{pref}[right];"
                    f"[left]crop=iw-{blend_width}:ih:0:0[left_main];"
                    f"[left]crop={blend_width}:ih:iw-{blend_width}:0[left_overlap];"
                    f"[right]crop={blend_width}:ih:0:0[right_overlap];"
                    f"[right]crop=iw-{blend_width}:ih:{blend_width}:0[right_main];"
                    f"[left_overlap][right_overlap]blend=all_expr='A*(1-X/W)+B*(X/W)'[blended];"
                    f"[left_main][blended][right_main]hstack=inputs=3[merged];"
                    f"[merged]lenscorrection={lens_correction}[v]"
                )
            else:
                # Standard method: Rotation + normalization with seamless blend
                filter_complex = (
                    f"[0:v]{pref}[left];"
                    f"[1:v]{pref}[right];"
                    f"[left]crop=iw-{blend_width}:ih:0:0[left_main];"
                    f"[left]crop={blend_width}:ih:iw-{blend_width}:0[left_overlap];"
                    f"[right]crop={blend_width}:ih:0:0[right_overlap];"
                    f"[right]crop=iw-{blend_width}:ih:{blend_width}:0[right_main];"
                    f"[left_overlap][right_overlap]blend=all_expr='A*(1-X/W)+B*(X/W)'[blended];"
                    f"[left_main][blended][right_main]hstack=inputs=3[out];"
                    f"[out]format=yuv420p[v]"
                )
            # Calculate final output width for seamless panoramic
            final_width = (width1 - blend_width) + blend_width + (width2 - blend_width)
        elif method == 'stacked':
            # FIXED: Simple top-bottom merge with rotation support
            overlap_height = min(50, feather_width // 2)  # Moderate overlap
            
            if self.enable_distortion_correction:
                filter_complex = (
                    f'[0:v]{pref}[top_prep]; '
                    f'[1:v]{pref}[bottom_prep]; '
                    f'[top_prep]crop=w=iw:h=ih-{overlap_height}:x=0:y=0[top]; '
                    f'[bottom_prep]crop=w=iw:h=ih-{overlap_height}:x=0:y={overlap_height}[bottom]; '
                    f'[top][bottom]vstack=inputs=2,format=yuv420p[merged]; '
                    f'[merged]lenscorrection={lens_correction}[v]'
                )
            else:
                filter_complex = (
                    f'[0:v]{pref}[top_prep]; '
                    f'[1:v]{pref}[bottom_prep]; '
                    f'[top_prep]crop=w=iw:h=ih-{overlap_height}:x=0:y=0[top]; '
                    f'[bottom_prep]crop=w=iw:h=ih-{overlap_height}:x=0:y={overlap_height}[bottom]; '
                    f'[top][bottom]vstack=inputs=2,format=yuv420p[v]'
                )
            # Calculate final output height correctly
            final_height = (height1 - overlap_height) + (height2 - overlap_height)
        else:
            # Default to side-by-side with simple blend and rotation support
            overlap_width = min(50, feather_width // 2)
            
            if self.enable_distortion_correction:
                filter_complex = (
                    f'[0:v]{pref}[left_prep]; '
                    f'[1:v]{pref}[right_prep]; '
                    f'[left_prep]crop=w=iw-{overlap_width}:h=ih:x=0:y=0[left]; '
                    f'[right_prep]crop=w=iw-{overlap_width}:h=ih:x={overlap_width}:y=0[right]; '
                    f'[left][right]hstack=inputs=2,format=yuv420p[merged]; '
                    f'[merged]lenscorrection={lens_correction}[v]'
                )
            else:
                filter_complex = (
                    f'[0:v]{pref}[left_prep]; '
                    f'[1:v]{pref}[right_prep]; '
                    f'[left_prep]crop=w=iw-{overlap_width}:h=ih:x=0:y=0[left]; '
                    f'[right_prep]crop=w=iw-{overlap_width}:h=ih:x={overlap_width}:y=0[right]; '
                    f'[left][right]hstack=inputs=2,format=yuv420p[v]'
                )
            final_width = (width1 - overlap_width) + (width2 - overlap_width)
        
        # Log the complete filter for debugging
        self.logger.debug(f"🔧 Complete filter_complex: {filter_complex}")
        
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-i', str(video1_path),
            '-i', str(video2_path),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-an',  # No audio to avoid errors
            '-c:v', 'libx264',
            '-preset', 'veryfast',  # Fast encoding
            '-crf', '20',  # Good quality
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
        
        # Try OpenCV stitching first if enabled and available
        if self.use_opencv_stitching and method == 'side_by_side':
            try:
                self.logger.info("🎬 Attempting OpenCV panoramic stitching...")
                opencv_result = self._opencv_panoramic_stitch(video1_path, video2_path, output_path, method)
                if opencv_result.success:
                    return opencv_result
                else:
                    self.logger.warning("⚠️ OpenCV stitching failed, falling back to FFmpeg")
            except Exception as e:
                self.logger.warning(f"⚠️ OpenCV stitching not available: {e}")
                self.logger.info("Falling back to FFmpeg stitching")
        
        # Retry loop for FFmpeg merging
        for attempt in range(self.max_retries):
            try:
                result.retry_count = attempt
                result.status = MergeStatus.IN_PROGRESS
                
                self.logger.info(f"🎬 Starting FFmpeg merge attempt {attempt + 1}/{self.max_retries}")
                self.logger.info(f"📹 Input 1: {video1_path.name} ({video1_path.stat().st_size:,} bytes)")
                self.logger.info(f"📹 Input 2: {video2_path.name} ({video2_path.stat().st_size:,} bytes)")
                self.logger.info(f"🎯 Output: {output_path}")
                self.logger.info(f"🔧 Method: {method}")
                
                # Create merge command
                cmd = self._create_merge_command(video1_path, video2_path, output_path, method)
                self.logger.debug(f"🔧 FFmpeg command: {' '.join(cmd)}")
                
                # Log the complete command for debugging
                self.logger.info(f"🎬 Starting FFmpeg merge with {len(cmd)} arguments")
                self.logger.info(f"📹 Input files: {video1_path.name}, {video2_path.name}")
                self.logger.info(f"🎯 Output file: {output_path}")
                self.logger.info(f"🔧 Method: {method}")
                
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
                        
                        self.logger.info(f"✅ FFmpeg merge completed successfully!")
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
        
        if output_path.suffix != '.mp4':
            output_path = output_path.with_suffix('.mp4')

        # All attempts failed - write the exact FFmpeg command for debugging
        result.status = MergeStatus.FAILED
        self.logger.error(f"❌ All merge attempts failed after {self.max_retries} retries")
        
        # Write the exact FFmpeg command to a file for debugging
        try:
            error_file = output_path.with_suffix('.error')
            with open(error_file, 'w') as f:
                f.write(f"# Failed FFmpeg command for debugging\n")
                f.write(f"# Input files: {video1_path}, {video2_path}\n")
                f.write(f"# Output file: {output_path}\n")
                f.write(f"# Method: {method}\n")
                f.write(f"# Timestamp: {datetime.now().isoformat()}\n\n")
                
                # Get the last command that was attempted
                cmd = self._create_merge_command(video1_path, video2_path, output_path, method)
                f.write(f"# Full FFmpeg command:\n")
                f.write(f"{' '.join(cmd)}\n\n")
                
                f.write(f"# To reproduce this error, run:\n")
                f.write(f"# {' '.join(cmd)}\n")
            
            self.logger.error(f"🔧 Debug info written to: {error_file}")
        except Exception as e:
            self.logger.error(f"❌ Failed to write debug info: {e}")
        
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
        """Clean up failed merge output files"""
        try:
            if output_path.exists():
                output_path.unlink()
                self.logger.info(f"🗑️ Cleaned up failed output: {output_path}")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to clean up {output_path}: {e}")

    def _get_optimal_lens_correction(self, video1_path: Path, video2_path: Path) -> str:
        """Get optimal lens correction parameters based on video characteristics"""
        try:
            # Get video info to determine optimal correction
            info1 = self._get_video_info(video1_path)
            info2 = self._get_video_info(video2_path)
            
            # Default correction for Raspberry Pi cameras (slight barrel distortion)
            # cx, cy: center of distortion (0.5 = center of frame)
            # k1, k2: distortion coefficients (positive = barrel, negative = pincushion)
            # For Pi cameras, typically slight barrel distortion
            correction_params = "cx=0.5:cy=0.5:k1=0.1:k2=0.05"
            
            # Check if we can detect camera type from metadata
            if info1.get('format', {}).get('tags', {}).get('device', '').lower().find('pi') != -1:
                # Raspberry Pi camera - apply stronger correction
                correction_params = "cx=0.5:cy=0.5:k1=0.15:k2=0.08"
                self.logger.info("🎥 Detected Raspberry Pi camera - applying enhanced distortion correction")
            elif info1.get('format', {}).get('tags', {}).get('device', '').lower().find('usb') != -1:
                # USB camera - apply moderate correction
                correction_params = "cx=0.5:cy=0.5:k1=0.08:k2=0.03"
                self.logger.info("🎥 Detected USB camera - applying moderate distortion correction")
            else:
                # Generic camera - apply light correction
                correction_params = "cx=0.5:cy=0.5:k1=0.05:k2=0.02"
                self.logger.info("🎥 Generic camera - applying light distortion correction")
            
            return correction_params
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not determine optimal lens correction: {e}")
            # Return safe default
            return "cx=0.5:cy=0.5:k1=0.1:k2=0.05"

    def _opencv_panoramic_stitch(self, video1_path: Path, video2_path: Path, 
                                output_path: Path, method: str = 'side_by_side') -> MergeResult:
        """OpenCV-based panoramic stitching using homography"""
        try:
            self.logger.info("🎬 Using OpenCV panoramic stitching...")
            
            # Check for homography file
            homography_path = Path("stitch/calibration/homography_right_to_left.json")
            if not homography_path.exists():
                self.logger.error(f"Homography file not found: {homography_path}")
                self.logger.info("Run calibration first: python3 stitch/calibrate_homography.py")
                raise FileNotFoundError(f"Homography file not found: {homography_path}")
            
            # Import OpenCV stitcher
            try:
                from stitch import PanoramicStitcher
            except ImportError:
                raise ImportError("OpenCV stitching not available. Install opencv-python")
            
            # Create stitcher
            stitcher = PanoramicStitcher(str(homography_path))
            
            # Perform stitching
            start_time = time.time()
            stitcher.stitch_streams(
                str(video1_path), 
                str(video2_path), 
                str(output_path)
            )
            
            # Validate output
            if not output_path.exists():
                raise RuntimeError("Stitching completed but output file not found")
            
            # Get file info
            file_size = output_path.stat().st_size
            duration = self._get_video_duration(output_path)
            
            result = MergeResult(
                success=True,
                status=MergeStatus.COMPLETED,
                output_path=output_path,
                file_size=file_size,
                duration=duration,
                merge_time=time.time() - start_time
            )
            
            self.logger.info(f"✅ OpenCV panoramic stitching completed successfully!")
            self.logger.info(f"📊 Output size: {file_size:,} bytes")
            self.logger.info(f"⏱️ Stitching time: {result.merge_time:.2f} seconds")
            if duration:
                self.logger.info(f"🎬 Duration: {duration:.2f} seconds")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ OpenCV stitching failed: {e}")
            return MergeResult(
                success=False,
                status=MergeStatus.FAILED,
                error_message=f"OpenCV stitching failed: {e}"
            )
    
    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration using ffprobe"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            return None
        except Exception:
            return None

def merge_videos_with_retry(video1_path: Path, video2_path: Path, 
                          output_path: Path, method: str = 'side_by_side',
                          max_retries: int = 3) -> MergeResult:
    """Convenience function for merging videos with retry logic"""
    merger = EnhancedVideoMerger(max_retries=max_retries)
    return merger.merge_videos(video1_path, video2_path, output_path, method)

if __name__ == "__main__":
    # Test the enhanced merger
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("input1", help="Left camera video")
    parser.add_argument("input2", help="Right camera video")
    parser.add_argument("output", help="Output merged video path")
    parser.add_argument("--method", default="side_by_side", choices=["side_by_side", "stacked", "advanced_stitch"])
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--bitrate", type=str, default="8000k")
    parser.add_argument("--resolution", help="e.g. 1920x1080")
    parser.add_argument("--rotate", type=float, default=0.0, help="Rotate inputs by N degrees before stitching")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    res = tuple(map(int, args.resolution.lower().split("x"))) if args.resolution else None
    merger = EnhancedVideoMerger(
        max_retries=args.retries, 
        timeout=args.timeout, 
        target_bitrate=args.bitrate, 
        output_resolution=res,
        input_rotate_degrees=args.rotate,
        enable_distortion_correction=False,  # default off
    )

    if args.dry_run:
        cmd = merger._create_merge_command(Path(args.input1), Path(args.input2), Path(args.output), method=args.method)
        print("Dry Run FFmpeg Command:\n", " ".join(cmd))
        exit(0)

    try:
        result = merger.merge_videos(Path(args.input1), Path(args.input2), Path(args.output), method=args.method)
        print("✅ Merge completed:", result)
    except Exception as e:
        print("❌ Merge failed:", e)
