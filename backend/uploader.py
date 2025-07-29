#!/usr/bin/env python3
"""
EZREC Uploader Service
Handles video uploads to cloud storage with retry logic and exponential backoff
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
class UploaderConfig:
    """Uploader configuration settings"""
    INPUT_DIR = Path("/opt/ezrec-backend/final")
    LOG_FILE = Path("/opt/ezrec-backend/logs/uploader.log")
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 60  # seconds
    CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks
    MIN_FILE_SIZE = 1024 * 1024  # 1MB minimum file size

# Setup logging
def setup_logging():
    """Setup rotating file logger"""
    from logging.handlers import RotatingFileHandler
    
    # Create log directory
    UploaderConfig.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    rotating_handler = RotatingFileHandler(
        UploaderConfig.LOG_FILE,
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

class VideoUploader:
    """Handles video uploads with retry logic and exponential backoff"""
    
    def __init__(self):
        self.aws_available = self._check_aws_availability()
        self.supabase_available = self._check_supabase_availability()
        logger.info(f"🔧 AWS available: {self.aws_available}")
        logger.info(f"🔧 Supabase available: {self.supabase_available}")
    
    def _check_aws_availability(self) -> bool:
        """Check if AWS credentials are available"""
        try:
            import boto3
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            aws_bucket = os.getenv('AWS_S3_BUCKET')
            
            if aws_access_key and aws_secret_key and aws_bucket:
                # Test AWS connection
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=aws_region
                )
                s3.head_bucket(Bucket=aws_bucket)
                logger.info(f"✅ AWS S3 connection successful (bucket: {aws_bucket})")
                return True
            else:
                logger.warning("⚠️ AWS credentials not configured")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ AWS not available: {e}")
            return False
    
    def _check_supabase_availability(self) -> bool:
        """Check if Supabase is available"""
        try:
            from supabase import create_client
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)
                # Test connection with a simple query
                supabase.table('cameras').select('id').limit(1).execute()
                logger.info("✅ Supabase connection successful")
                return True
            else:
                logger.warning("⚠️ Supabase credentials not configured")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Supabase not available: {e}")
            return False
    
    def validate_input_file(self, video_path: Path) -> bool:
        """Validate input video file"""
        try:
            if not video_path.exists():
                logger.error(f"❌ Video file not found: {video_path}")
                return False
            
            file_size = video_path.stat().st_size
            if file_size < UploaderConfig.MIN_FILE_SIZE:
                logger.error(f"❌ Video file too small: {file_size:,} bytes (min: {UploaderConfig.MIN_FILE_SIZE:,})")
                return False
            
            # Check if it's a valid video file
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name', '-of', 'json',
                str(video_path)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"❌ Invalid video file: {video_path}")
                return False
            
            logger.info(f"✅ Input file validated: {video_path.name} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating input file: {e}")
            return False
    
    def upload_to_s3(self, local_path: Path, s3_key: str) -> Optional[str]:
        """Upload file to S3 with retry logic"""
        try:
            import boto3
            from boto3.s3.transfer import TransferConfig
            
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            aws_bucket = os.getenv('AWS_S3_BUCKET')
            
            if not all([aws_access_key, aws_secret_key, aws_bucket]):
                logger.error("❌ AWS credentials not configured")
                return None
            
            # Configure S3 client
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            # Configure transfer settings
            transfer_config = TransferConfig(
                multipart_threshold=UploaderConfig.CHUNK_SIZE,
                max_concurrency=10,
                multipart_chunksize=UploaderConfig.CHUNK_SIZE,
                use_threads=True
            )
            
            logger.info(f"📤 Uploading to S3: {local_path.name} → {s3_key}")
            
            # Upload with retry logic
            for attempt in range(UploaderConfig.MAX_RETRIES):
                try:
                    s3.upload_file(
                        str(local_path),
                        aws_bucket,
                        s3_key,
                        Config=transfer_config
                    )
                    
                    # Generate URL
                    s3_url = f"https://{aws_bucket}.s3.{aws_region}.amazonaws.com/{s3_key}"
                    logger.info(f"✅ S3 upload successful: {s3_url}")
                    return s3_url
                    
                except Exception as e:
                    logger.error(f"❌ S3 upload attempt {attempt + 1} failed: {e}")
                    
                    if attempt < UploaderConfig.MAX_RETRIES - 1:
                        # Calculate backoff time
                        backoff_time = min(
                            UploaderConfig.INITIAL_BACKOFF * (2 ** attempt),
                            UploaderConfig.MAX_BACKOFF
                        )
                        logger.info(f"⏳ Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"❌ S3 upload failed after {UploaderConfig.MAX_RETRIES} attempts")
                        return None
            
        except Exception as e:
            logger.error(f"❌ Error uploading to S3: {e}")
            return None
    
    def upload_to_supabase_storage(self, local_path: Path, storage_path: str) -> Optional[str]:
        """Upload file to Supabase Storage with retry logic"""
        try:
            from supabase import create_client
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            storage_bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'videos')
            
            if not all([supabase_url, supabase_key]):
                logger.error("❌ Supabase credentials not configured")
                return None
            
            supabase = create_client(supabase_url, supabase_key)
            
            logger.info(f"📤 Uploading to Supabase Storage: {local_path.name} → {storage_path}")
            
            # Upload with retry logic
            for attempt in range(UploaderConfig.MAX_RETRIES):
                try:
                    with open(local_path, 'rb') as f:
                        result = supabase.storage.from_(storage_bucket).upload(
                            path=storage_path,
                            file=f,
                            file_options={"content-type": "video/mp4"}
                        )
                    
                    # Generate URL
                    storage_url = f"{supabase_url}/storage/v1/object/public/{storage_bucket}/{storage_path}"
                    logger.info(f"✅ Supabase Storage upload successful: {storage_url}")
                    return storage_url
                    
                except Exception as e:
                    logger.error(f"❌ Supabase Storage upload attempt {attempt + 1} failed: {e}")
                    
                    if attempt < UploaderConfig.MAX_RETRIES - 1:
                        # Calculate backoff time
                        backoff_time = min(
                            UploaderConfig.INITIAL_BACKOFF * (2 ** attempt),
                            UploaderConfig.MAX_BACKOFF
                        )
                        logger.info(f"⏳ Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"❌ Supabase Storage upload failed after {UploaderConfig.MAX_RETRIES} attempts")
                        return None
            
        except Exception as e:
            logger.error(f"❌ Error uploading to Supabase Storage: {e}")
            return None
    
    def update_database_metadata(self, video_path: Path, upload_url: str, storage_path: str) -> bool:
        """Update database with video metadata"""
        try:
            from supabase import create_client
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not all([supabase_url, supabase_key]):
                logger.error("❌ Supabase credentials not configured")
                return False
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Extract metadata from filename
            filename = video_path.stem
            parts = filename.split('_')
            
            # Parse booking information from filename
            booking_id = None
            user_id = None
            camera_id = None
            
            if len(parts) >= 3:
                # Expected format: timestamp_userid_cameraid_final
                if len(parts) >= 4:
                    user_id = parts[1]
                    camera_id = parts[2]
                else:
                    # Fallback format
                    user_id = parts[1] if len(parts) > 1 else None
                    camera_id = parts[2] if len(parts) > 2 else None
            
            # Get video information
            video_info = self.get_video_info(video_path)
            duration = 0
            if video_info.get('format'):
                duration = float(video_info['format'].get('duration', 0))
            
            # Prepare metadata
            metadata = {
                "filename": video_path.name,
                "file_size": video_path.stat().st_size,
                "duration": duration,
                "upload_url": upload_url,
                "storage_path": storage_path,
                "uploaded_at": datetime.now().isoformat(),
                "user_id": user_id,
                "camera_id": camera_id,
                "booking_id": booking_id
            }
            
            # Insert into videos table
            result = supabase.table('videos').insert(metadata).execute()
            
            if result.data:
                logger.info(f"✅ Database metadata updated for: {video_path.name}")
                return True
            else:
                logger.error(f"❌ Failed to update database metadata")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating database metadata: {e}")
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
    
    def upload_video(self, video_path: Path) -> bool:
        """Complete video upload process"""
        try:
            logger.info(f"📤 Starting upload process: {video_path.name}")
            
            # Validate input file
            if not self.validate_input_file(video_path):
                return False
            
            # Generate storage paths
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = video_path.name
            user_id = "unknown"
            
            # Extract user_id from filename if possible
            parts = filename.split('_')
            if len(parts) >= 2:
                user_id = parts[1]
            
            # S3 upload
            s3_url = None
            if self.aws_available:
                s3_key = f"{user_id}/{date_str}/{filename}"
                s3_url = self.upload_to_s3(video_path, s3_key)
            
            # Supabase Storage upload
            storage_url = None
            if self.supabase_available:
                storage_path = f"{user_id}/{date_str}/{filename}"
                storage_url = self.upload_to_supabase_storage(video_path, storage_path)
            
            # Use the first successful upload
            upload_url = s3_url or storage_url
            storage_path = s3_key if s3_url else storage_path if storage_url else None
            
            if upload_url:
                logger.info(f"✅ Upload successful: {upload_url}")
                
                # Update database metadata
                if self.supabase_available:
                    self.update_database_metadata(video_path, upload_url, storage_path or "")
                
                # Log success
                logger.info(f"✅ Successfully uploaded: {video_path.name}")
                return True
            else:
                logger.error(f"❌ All upload methods failed for: {video_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in video upload: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def process_pending_uploads(self):
        """Process pending uploads from the input directory"""
        try:
            if not UploaderConfig.INPUT_DIR.exists():
                logger.warning(f"⚠️ Input directory not found: {UploaderConfig.INPUT_DIR}")
                return
            
            # Look for final video files
            video_files = list(UploaderConfig.INPUT_DIR.glob("*_final.mp4"))
            
            for video_file in video_files:
                try:
                    # Check if already uploaded (look for .uploaded marker)
                    uploaded_marker = video_file.with_suffix('.uploaded')
                    if uploaded_marker.exists():
                        logger.info(f"⏭️ Already uploaded: {video_file.name}")
                        continue
                    
                    logger.info(f"📤 Processing upload: {video_file.name}")
                    
                    # Upload video
                    if self.upload_video(video_file):
                        # Create uploaded marker
                        uploaded_marker.touch()
                        logger.info(f"✅ Successfully uploaded: {video_file.name}")
                        
                        # Optional: Move to archive or delete after successful upload
                        # video_file.unlink(missing_ok=True)
                    else:
                        logger.error(f"❌ Failed to upload: {video_file.name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {video_file.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Error processing pending uploads: {e}")

def handle_exit(sig, frame):
    """Handle graceful shutdown"""
    logger.info("🛑 Received termination signal. Exiting gracefully.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    """Main application entry point"""
    logger.info("🚀 EZREC Uploader Service started")
    logger.info(f"📁 Input directory: {UploaderConfig.INPUT_DIR}")
    logger.info(f"🔄 Max retries: {UploaderConfig.MAX_RETRIES}")
    logger.info(f"⏱️ Initial backoff: {UploaderConfig.INITIAL_BACKOFF}s")
    logger.info(f"⏱️ Max backoff: {UploaderConfig.MAX_BACKOFF}s")
    
    # Create uploader
    uploader = VideoUploader()
    
    try:
        while True:
            try:
                # Process pending uploads
                uploader.process_pending_uploads()
                
                # Wait before next check
                time.sleep(20)  # Check every 20 seconds
                
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
        logger.info("🛑 Uploader shutdown complete")

if __name__ == "__main__":
    main() 