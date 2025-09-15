#!/usr/bin/env python3
"""
EZREC Upload Manager Service
Handles file uploads to S3 and other storage services
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import settings, get_logger, get_s3_client

logger = get_logger(__name__)

class UploadManager:
    """Service for managing file uploads"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.s3_client = get_s3_client()
    
    def upload_to_s3(self, 
                    local_file: Path, 
                    s3_key: str, 
                    progress_callback: Optional[Callable] = None) -> bool:
        """Upload file to S3 with progress tracking"""
        try:
            if not local_file.exists():
                self.logger.error(f"❌ Local file not found: {local_file}")
                return False
            
            file_size = local_file.stat().st_size
            self.logger.info(f"📤 Uploading {local_file.name} to S3 ({file_size:,} bytes)")
            
            # Create progress callback if provided
            if progress_callback:
                def progress_wrapper(bytes_transferred):
                    progress = (bytes_transferred / file_size) * 100
                    progress_callback(progress)
            else:
                progress_wrapper = None
            
            # Upload with progress tracking
            self.s3_client.upload_file(
                str(local_file),
                settings.storage.s3_bucket,
                s3_key,
                Callback=progress_wrapper
            )
            
            self.logger.info(f"✅ Upload completed: s3://{settings.storage.s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ S3 upload failed: {e}")
            return False
    
    def upload_video(self, 
                    video_file: Path, 
                    booking_id: str, 
                    video_type: str = "merged",
                    progress_callback: Optional[Callable] = None) -> Optional[str]:
        """Upload video file with standardized naming"""
        try:
            # Generate S3 key
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"videos/{booking_id}/{video_type}_{timestamp}.mp4"
            
            # Upload file
            success = self.upload_to_s3(video_file, s3_key, progress_callback)
            
            if success:
                # Generate public URL
                s3_url = f"https://{settings.storage.s3_bucket}.s3.{settings.storage.aws_region}.amazonaws.com/{s3_key}"
                self.logger.info(f"✅ Video uploaded: {s3_url}")
                return s3_url
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Video upload failed: {e}")
            return None
    
    def upload_individual_cameras(self, 
                                camera_files: Dict[int, Path], 
                                booking_id: str,
                                progress_callback: Optional[Callable] = None) -> Dict[int, Optional[str]]:
        """Upload individual camera files"""
        results = {}
        
        for camera_index, file_path in camera_files.items():
            try:
                self.logger.info(f"📤 Uploading camera {camera_index} file: {file_path.name}")
                
                # Generate S3 key for individual camera
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"videos/{booking_id}/camera_{camera_index}_{timestamp}.mp4"
                
                # Upload file
                success = self.upload_to_s3(file_path, s3_key, progress_callback)
                
                if success:
                    s3_url = f"https://{settings.storage.s3_bucket}.s3.{settings.storage.aws_region}.amazonaws.com/{s3_key}"
                    results[camera_index] = s3_url
                    self.logger.info(f"✅ Camera {camera_index} uploaded: {s3_url}")
                else:
                    results[camera_index] = None
                    self.logger.error(f"❌ Camera {camera_index} upload failed")
                    
            except Exception as e:
                self.logger.error(f"❌ Camera {camera_index} upload error: {e}")
                results[camera_index] = None
        
        return results
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.storage.s3_bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            self.logger.info(f"✅ Generated presigned URL for {s3_key}")
            return url
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None
    
    def delete_from_s3(self, s3_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=settings.storage.s3_bucket,
                Key=s3_key
            )
            
            self.logger.info(f"✅ Deleted from S3: {s3_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete from S3: {e}")
            return False
    
    def list_booking_videos(self, booking_id: str) -> List[Dict[str, Any]]:
        """List all videos for a booking"""
        try:
            prefix = f"videos/{booking_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=settings.storage.s3_bucket,
                Prefix=prefix
            )
            
            videos = []
            for obj in response.get('Contents', []):
                videos.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'url': f"https://{settings.storage.s3_bucket}.s3.{settings.storage.aws_region}.amazonaws.com/{obj['Key']}"
                })
            
            self.logger.info(f"📋 Found {len(videos)} videos for booking {booking_id}")
            return videos
            
        except Exception as e:
            self.logger.error(f"❌ Failed to list booking videos: {e}")
            return []
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        try:
            # This would typically query a database or S3 metrics
            # For now, return basic info
            return {
                'bucket': settings.storage.s3_bucket,
                'region': settings.storage.aws_region,
                'status': 'active'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get upload stats: {e}")
            return {'status': 'error', 'error': str(e)}
