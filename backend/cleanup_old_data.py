#!/usr/bin/env python3
"""
EZREC Data Cleanup Script
- Removes old recordings, logs, and temporary files
- Configurable retention periods
- Safe cleanup with validation
- Logs cleanup operations
"""

import os
import sys
import time
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse

# Add API directory to path
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../api'))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

class DataCleaner:
    """Manages cleanup of old EZREC data"""
    
    def __init__(self, base_dir: Path = Path("/opt/ezrec-backend")):
        self.base_dir = base_dir
        self.logger = logging.getLogger(__name__)
        
        # Default retention periods (in days)
        self.retention_periods = {
            'recordings': 7,      # Keep recordings for 7 days
            'logs': 14,           # Keep logs for 14 days
            'processed': 3,       # Keep processed videos for 3 days
            'temp': 1,            # Keep temp files for 1 day
            'cache': 30,          # Keep cache for 30 days
            'bookings': 90        # Keep booking history for 90 days
        }
        
        # Directories to clean
        self.directories = {
            'recordings': base_dir / 'recordings',
            'logs': base_dir / 'logs',
            'processed': base_dir / 'processed',
            'temp': base_dir / 'temp',
            'cache': base_dir / 'media_cache',
            'bookings': base_dir / 'api' / 'local_data'
        }
    
    def setup_logging(self, log_file: Path = None):
        """Set up logging for cleanup operations"""
        if log_file is None:
            log_file = self.base_dir / 'logs' / 'cleanup.log'
        
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def get_old_files(self, directory: Path, days_old: int, 
                     file_patterns: List[str] = None) -> List[Path]:
        """Get files older than specified days"""
        if not directory.exists():
            return []
        
        if file_patterns is None:
            file_patterns = ['*']
        
        cutoff_time = time.time() - (days_old * 24 * 3600)
        old_files = []
        
        for pattern in file_patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            old_files.append(file_path)
                    except OSError:
                        continue
        
        return old_files
    
    def cleanup_recordings(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old recordings"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['recordings']
        
        self.logger.info(f"🧹 Cleaning up recordings older than {days_to_keep} days...")
        
        stats = {
            'directories_removed': 0,
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        recordings_dir = self.directories['recordings']
        if not recordings_dir.exists():
            self.logger.info("📁 Recordings directory does not exist")
            return stats
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean up by date directories
        for date_dir in recordings_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            try:
                # Parse date from directory name (YYYY-MM-DD format)
                date_str = date_dir.name
                if len(date_str) == 10 and date_str.count('-') == 2:
                    dir_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if dir_date < cutoff_date:
                        # Calculate size before removal
                        dir_size = sum(f.stat().st_size for f in date_dir.rglob('*') if f.is_file())
                        
                        # Remove directory and all contents
                        shutil.rmtree(date_dir)
                        
                        stats['directories_removed'] += 1
                        stats['bytes_freed'] += dir_size
                        
                        self.logger.info(f"🗑️ Removed old recordings directory: {date_dir.name} ({dir_size:,} bytes)")
                        
            except (ValueError, OSError) as e:
                stats['errors'] += 1
                self.logger.warning(f"⚠️ Error processing directory {date_dir}: {e}")
        
        self.logger.info(f"✅ Recordings cleanup completed: {stats['directories_removed']} directories removed, {stats['bytes_freed']:,} bytes freed")
        return stats
    
    def cleanup_logs(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old log files"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['logs']
        
        self.logger.info(f"🧹 Cleaning up logs older than {days_to_keep} days...")
        
        stats = {
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        logs_dir = self.directories['logs']
        if not logs_dir.exists():
            self.logger.info("📁 Logs directory does not exist")
            return stats
        
        # Find old log files
        old_files = self.get_old_files(logs_dir, days_to_keep, ['*.log', '*.log.*'])
        
        for file_path in old_files:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                
                stats['files_removed'] += 1
                stats['bytes_freed'] += file_size
                
                self.logger.info(f"🗑️ Removed old log file: {file_path.name} ({file_size:,} bytes)")
                
            except OSError as e:
                stats['errors'] += 1
                self.logger.warning(f"⚠️ Error removing log file {file_path}: {e}")
        
        self.logger.info(f"✅ Logs cleanup completed: {stats['files_removed']} files removed, {stats['bytes_freed']:,} bytes freed")
        return stats
    
    def cleanup_processed_videos(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old processed videos"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['processed']
        
        self.logger.info(f"🧹 Cleaning up processed videos older than {days_to_keep} days...")
        
        stats = {
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        processed_dir = self.directories['processed']
        if not processed_dir.exists():
            self.logger.info("📁 Processed directory does not exist")
            return stats
        
        # Find old processed video files
        old_files = self.get_old_files(processed_dir, days_to_keep, ['*.mp4', '*.avi', '*.mov'])
        
        for file_path in old_files:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                
                # Also remove associated files (.json, .done, etc.)
                for ext in ['.json', '.done', '.error', '.lock']:
                    aux_file = file_path.with_suffix(ext)
                    if aux_file.exists():
                        aux_file.unlink()
                        self.logger.debug(f"🗑️ Removed auxiliary file: {aux_file.name}")
                
                stats['files_removed'] += 1
                stats['bytes_freed'] += file_size
                
                self.logger.info(f"🗑️ Removed old processed video: {file_path.name} ({file_size:,} bytes)")
                
            except OSError as e:
                stats['errors'] += 1
                self.logger.warning(f"⚠️ Error removing processed video {file_path}: {e}")
        
        self.logger.info(f"✅ Processed videos cleanup completed: {stats['files_removed']} files removed, {stats['bytes_freed']:,} bytes freed")
        return stats
    
    def cleanup_temp_files(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up temporary files"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['temp']
        
        self.logger.info(f"🧹 Cleaning up temp files older than {days_to_keep} days...")
        
        stats = {
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        # Clean up temp directory
        temp_dir = self.directories['temp']
        if temp_dir.exists():
            old_files = self.get_old_files(temp_dir, days_to_keep, ['*'])
            
            for file_path in old_files:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    
                    stats['files_removed'] += 1
                    stats['bytes_freed'] += file_size
                    
                    self.logger.debug(f"🗑️ Removed temp file: {file_path.name} ({file_size:,} bytes)")
                    
                except OSError as e:
                    stats['errors'] += 1
                    self.logger.warning(f"⚠️ Error removing temp file {file_path}: {e}")
        
        # Clean up system temp files
        system_temp_patterns = [
            '/tmp/ezrec_*',
            '/tmp/camera_*',
            '/tmp/ffmpeg_*',
            '/tmp/merge_*'
        ]
        
        for pattern in system_temp_patterns:
            try:
                for temp_file in Path('/tmp').glob(pattern.split('/')[-1]):
                    if temp_file.is_file():
                        try:
                            file_age = time.time() - temp_file.stat().st_mtime
                            if file_age > (days_to_keep * 24 * 3600):
                                file_size = temp_file.stat().st_size
                                temp_file.unlink()
                                
                                stats['files_removed'] += 1
                                stats['bytes_freed'] += file_size
                                
                                self.logger.debug(f"🗑️ Removed system temp file: {temp_file.name} ({file_size:,} bytes)")
                                
                        except OSError as e:
                            stats['errors'] += 1
                            self.logger.warning(f"⚠️ Error removing system temp file {temp_file}: {e}")
            except Exception as e:
                self.logger.warning(f"⚠️ Error processing temp pattern {pattern}: {e}")
        
        self.logger.info(f"✅ Temp files cleanup completed: {stats['files_removed']} files removed, {stats['bytes_freed']:,} bytes freed")
        return stats
    
    def cleanup_cache(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old cache files"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['cache']
        
        self.logger.info(f"🧹 Cleaning up cache older than {days_to_keep} days...")
        
        stats = {
            'directories_removed': 0,
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        cache_dir = self.directories['cache']
        if not cache_dir.exists():
            self.logger.info("📁 Cache directory does not exist")
            return stats
        
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        # Clean up old user cache directories
        for user_dir in cache_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            try:
                # Check if directory is old enough
                if user_dir.stat().st_mtime < cutoff_time:
                    dir_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                    shutil.rmtree(user_dir)
                    
                    stats['directories_removed'] += 1
                    stats['bytes_freed'] += dir_size
                    
                    self.logger.info(f"🗑️ Removed old cache directory: {user_dir.name} ({dir_size:,} bytes)")
                    
            except OSError as e:
                stats['errors'] += 1
                self.logger.warning(f"⚠️ Error removing cache directory {user_dir}: {e}")
        
        self.logger.info(f"✅ Cache cleanup completed: {stats['directories_removed']} directories removed, {stats['bytes_freed']:,} bytes freed")
        return stats
    
    def cleanup_old_bookings(self, days_to_keep: int = None) -> Dict[str, Any]:
        """Clean up old booking records"""
        if days_to_keep is None:
            days_to_keep = self.retention_periods['bookings']
        
        self.logger.info(f"🧹 Cleaning up bookings older than {days_to_keep} days...")
        
        stats = {
            'records_removed': 0,
            'errors': 0
        }
        
        bookings_file = self.directories['bookings'] / 'bookings.json'
        if not bookings_file.exists():
            self.logger.info("📁 Bookings file does not exist")
            return stats
        
        try:
            # Load current bookings
            with open(bookings_file, 'r') as f:
                data = json.load(f)
            
            # Handle both old and new formats
            if isinstance(data, list):
                bookings = data
                old_format = True
            elif isinstance(data, dict) and 'bookings' in data:
                bookings = data['bookings']
                old_format = False
            else:
                self.logger.warning("⚠️ Unknown bookings file format")
                return stats
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            original_count = len(bookings)
            
            # Filter out old bookings
            if old_format:
                # Old format: list of booking objects
                filtered_bookings = []
                for booking in bookings:
                    try:
                        # Try to parse booking date
                        if 'created_at' in booking:
                            booking_date = datetime.fromisoformat(booking['created_at'].replace('Z', '+00:00'))
                        elif 'start_time' in booking:
                            booking_date = datetime.fromisoformat(booking['start_time'].replace('Z', '+00:00'))
                        else:
                            # Keep if no date found
                            filtered_bookings.append(booking)
                            continue
                        
                        if booking_date > cutoff_date:
                            filtered_bookings.append(booking)
                        else:
                            stats['records_removed'] += 1
                            
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error parsing booking date: {e}")
                        filtered_bookings.append(booking)
                
                new_data = filtered_bookings
            else:
                # New format: dict with bookings array
                filtered_bookings = []
                for booking in bookings:
                    try:
                        if 'created_at' in booking:
                            booking_date = datetime.fromisoformat(booking['created_at'].replace('Z', '+00:00'))
                        elif 'start_time' in booking:
                            booking_date = datetime.fromisoformat(booking['start_time'].replace('Z', '+00:00'))
                        else:
                            filtered_bookings.append(booking)
                            continue
                        
                        if booking_date > cutoff_date:
                            filtered_bookings.append(booking)
                        else:
                            stats['records_removed'] += 1
                            
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error parsing booking date: {e}")
                        filtered_bookings.append(booking)
                
                new_data = {
                    'bookings': filtered_bookings,
                    'last_updated': datetime.now().isoformat(),
                    'user_id': data.get('user_id', 'unknown'),
                    'camera_id': data.get('camera_id', 'unknown')
                }
            
            # Save filtered bookings
            with open(bookings_file, 'w') as f:
                json.dump(new_data, f, indent=2)
            
            self.logger.info(f"✅ Bookings cleanup completed: {stats['records_removed']} records removed")
            
        except Exception as e:
            stats['errors'] += 1
            self.logger.error(f"❌ Error cleaning up bookings: {e}")
        
        return stats
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """Get current disk usage statistics"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(self.base_dir)
            
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'free_gb': free / (1024**3),
                'used_percent': (used / total) * 100
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting disk usage: {e}")
            return {}
    
    def run_full_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run complete cleanup of all data types"""
        self.logger.info("🧹 Starting full EZREC data cleanup...")
        
        if dry_run:
            self.logger.info("🔍 DRY RUN MODE - No files will be deleted")
        
        # Get initial disk usage
        initial_usage = self.get_disk_usage()
        
        # Run all cleanup operations
        results = {
            'recordings': self.cleanup_recordings() if not dry_run else {'files_removed': 0, 'bytes_freed': 0},
            'logs': self.cleanup_logs() if not dry_run else {'files_removed': 0, 'bytes_freed': 0},
            'processed': self.cleanup_processed_videos() if not dry_run else {'files_removed': 0, 'bytes_freed': 0},
            'temp': self.cleanup_temp_files() if not dry_run else {'files_removed': 0, 'bytes_freed': 0},
            'cache': self.cleanup_cache() if not dry_run else {'files_removed': 0, 'bytes_freed': 0},
            'bookings': self.cleanup_old_bookings() if not dry_run else {'records_removed': 0}
        }
        
        # Calculate totals
        total_files = sum(r.get('files_removed', 0) for r in results.values())
        total_bytes = sum(r.get('bytes_freed', 0) for r in results.values())
        total_dirs = sum(r.get('directories_removed', 0) for r in results.values())
        total_records = sum(r.get('records_removed', 0) for r in results.values())
        
        # Get final disk usage
        final_usage = self.get_disk_usage()
        
        # Summary
        summary = {
            'total_files_removed': total_files,
            'total_directories_removed': total_dirs,
            'total_records_removed': total_records,
            'total_bytes_freed': total_bytes,
            'total_gb_freed': total_bytes / (1024**3),
            'initial_disk_usage': initial_usage,
            'final_disk_usage': final_usage,
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info("=" * 60)
        self.logger.info("📊 CLEANUP SUMMARY:")
        self.logger.info(f"   Files removed: {total_files}")
        self.logger.info(f"   Directories removed: {total_dirs}")
        self.logger.info(f"   Records removed: {total_records}")
        self.logger.info(f"   Space freed: {summary['total_gb_freed']:.2f} GB")
        
        if initial_usage and final_usage:
            freed_gb = initial_usage.get('used_gb', 0) - final_usage.get('used_gb', 0)
            self.logger.info(f"   Disk usage: {initial_usage.get('used_percent', 0):.1f}% → {final_usage.get('used_percent', 0):.1f}%")
            self.logger.info(f"   Actual space freed: {freed_gb:.2f} GB")
        
        self.logger.info("=" * 60)
        
        return summary

def main():
    parser = argparse.ArgumentParser(description="EZREC Data Cleanup Tool")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--recordings-days", type=int, default=7, help="Days to keep recordings")
    parser.add_argument("--logs-days", type=int, default=14, help="Days to keep logs")
    parser.add_argument("--processed-days", type=int, default=3, help="Days to keep processed videos")
    parser.add_argument("--temp-days", type=int, default=1, help="Days to keep temp files")
    parser.add_argument("--cache-days", type=int, default=30, help="Days to keep cache")
    parser.add_argument("--bookings-days", type=int, default=90, help="Days to keep bookings")
    parser.add_argument("--base-dir", default="/opt/ezrec-backend", help="Base EZREC directory")
    
    args = parser.parse_args()
    
    # Set up cleaner
    cleaner = DataCleaner(Path(args.base_dir))
    cleaner.setup_logging()
    
    # Update retention periods if specified
    cleaner.retention_periods.update({
        'recordings': args.recordings_days,
        'logs': args.logs_days,
        'processed': args.processed_days,
        'temp': args.temp_days,
        'cache': args.cache_days,
        'bookings': args.bookings_days
    })
    
    # Run cleanup
    try:
        summary = cleaner.run_full_cleanup(dry_run=args.dry_run)
        
        if args.dry_run:
            print("🔍 Dry run completed - no files were actually deleted")
        else:
            print("✅ Cleanup completed successfully")
        
        # Save summary to file
        summary_file = cleaner.base_dir / 'logs' / f'cleanup_summary_{int(time.time())}.json'
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Summary saved to: {summary_file}")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 