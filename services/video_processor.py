#!/usr/bin/env python3
"""
EZREC Video Processing Service
Handles video processing operations
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings, get_logger

logger = get_logger(__name__)

class VideoProcessor:
    """Service for video processing operations"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def merge_videos(self, input_files: List[Path], output_file: Path, method: str = "side_by_side") -> bool:
        """Merge multiple video files"""
        try:
            self.logger.info(f"🎬 Merging {len(input_files)} videos to {output_file}")
            
            if method == "side_by_side":
                return self._merge_side_by_side(input_files, output_file)
            elif method == "panoramic":
                return self._merge_panoramic(input_files, output_file)
            else:
                self.logger.error(f"❌ Unknown merge method: {method}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Video merge failed: {e}")
            return False
    
    def _merge_side_by_side(self, input_files: List[Path], output_file: Path) -> bool:
        """Merge videos side by side using FFmpeg"""
        try:
            if len(input_files) != 2:
                self.logger.error("❌ Side-by-side merge requires exactly 2 input files")
                return False
            
            # Create FFmpeg command for side-by-side merge
            cmd = [
                'ffmpeg',
                '-i', str(input_files[0]),
                '-i', str(input_files[1]),
                '-filter_complex', '[0:v][1:v]hstack=inputs=2[v]',
                '-map', '[v]',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-y',  # Overwrite output file
                str(output_file)
            ]
            
            self.logger.info(f"🎬 Running FFmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"✅ Video merge completed: {output_file}")
                return True
            else:
                self.logger.error(f"❌ FFmpeg failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Video merge timed out")
            return False
        except Exception as e:
            self.logger.error(f"❌ Video merge error: {e}")
            return False
    
    def _merge_panoramic(self, input_files: List[Path], output_file: Path) -> bool:
        """Merge videos using panoramic stitching"""
        try:
            # Import stitching functionality
            sys.path.append(str(Path(__file__).parent.parent / "backend" / "stitch"))
            from stitch_videos import PanoramicStitcher
            
            # Check for homography file
            homography_file = Path(__file__).parent.parent / "backend" / "stitch" / "homography.json"
            if not homography_file.exists():
                self.logger.warning("⚠️ No homography file found, falling back to side-by-side")
                return self._merge_side_by_side(input_files, output_file)
            
            # Use panoramic stitcher
            stitcher = PanoramicStitcher(str(homography_file))
            success = stitcher.stitch_videos([str(f) for f in input_files], str(output_file))
            
            if success:
                self.logger.info(f"✅ Panoramic merge completed: {output_file}")
                return True
            else:
                self.logger.error("❌ Panoramic merge failed")
                return False
                
        except ImportError:
            self.logger.warning("⚠️ Panoramic stitching not available, falling back to side-by-side")
            return self._merge_side_by_side(input_files, output_file)
        except Exception as e:
            self.logger.error(f"❌ Panoramic merge error: {e}")
            return False
    
    def validate_video(self, video_file: Path) -> Dict[str, Any]:
        """Validate video file and get metadata"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                metadata = json.loads(result.stdout)
                
                # Extract useful information
                video_info = {
                    'valid': True,
                    'duration': float(metadata['format'].get('duration', 0)),
                    'size': int(metadata['format'].get('size', 0)),
                    'bitrate': int(metadata['format'].get('bit_rate', 0)),
                    'width': 0,
                    'height': 0,
                    'fps': 0
                }
                
                # Get video stream info
                for stream in metadata.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_info['width'] = int(stream.get('width', 0))
                        video_info['height'] = int(stream.get('height', 0))
                        fps_str = stream.get('r_frame_rate', '0/1')
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            video_info['fps'] = float(num) / float(den) if float(den) != 0 else 0
                        break
                
                self.logger.info(f"✅ Video validated: {video_file.name} ({video_info['width']}x{video_info['height']}, {video_info['duration']:.1f}s)")
                return video_info
            else:
                self.logger.error(f"❌ Video validation failed: {result.stderr}")
                return {'valid': False, 'error': result.stderr}
                
        except Exception as e:
            self.logger.error(f"❌ Video validation error: {e}")
            return {'valid': False, 'error': str(e)}
    
    def compress_video(self, input_file: Path, output_file: Path, quality: str = "medium") -> bool:
        """Compress video file"""
        try:
            # Quality presets
            quality_settings = {
                'low': ['-crf', '28', '-preset', 'fast'],
                'medium': ['-crf', '23', '-preset', 'medium'],
                'high': ['-crf', '18', '-preset', 'slow']
            }
            
            if quality not in quality_settings:
                quality = 'medium'
            
            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-c:v', 'libx264',
                *quality_settings[quality],
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',  # Overwrite output file
                str(output_file)
            ]
            
            self.logger.info(f"🗜️ Compressing video: {input_file.name} -> {output_file.name}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Check file sizes
                input_size = input_file.stat().st_size
                output_size = output_file.stat().st_size
                compression_ratio = (1 - output_size / input_size) * 100
                
                self.logger.info(f"✅ Video compressed: {compression_ratio:.1f}% size reduction")
                return True
            else:
                self.logger.error(f"❌ Video compression failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Video compression timed out")
            return False
        except Exception as e:
            self.logger.error(f"❌ Video compression error: {e}")
            return False
