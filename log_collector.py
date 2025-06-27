#!/usr/bin/env python3
"""
EZREC Log Collector Service
- Collects logs from all backend services and systemd journal
- Compresses and uploads logs to Supabase Storage ('logs' bucket)
- Stores logs under /<camera_id>/YYYYMMDD_HHMMSS_logs.zip for each camera
- Runs as a standalone process (systemd service)
"""
import os
import time
import logging
import zipfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import subprocess
from shutil import which

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
CAMERA_ID = os.getenv('CAMERA_ID', '0')
LOGS_DIR = Path(os.getenv('LOGS_DIR', '/opt/ezrec-backend/logs'))
UPLOAD_INTERVAL = int(os.getenv('LOG_UPLOAD_INTERVAL', '900'))  # 15 min default
LOG_BUCKET = os.getenv('LOG_BUCKET', 'logs')
LOG_FILE = Path(os.getenv('LOG_COLLECTOR_LOG', '/opt/ezrec-backend/logs/log_collector.log'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def has_journalctl():
    return which('journalctl') is not None

def collect_logs(archive_path):
    """Collect all .log files and systemd journal into a zip archive."""
    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all .log files
            for log_file in LOGS_DIR.glob('*.log'):
                zipf.write(log_file, arcname=log_file.name)
            # Add systemd journal for each service
            services = ['booking_sync', 'recorder', 'video_worker', 'system_status', 'log_collector']
            if has_journalctl():
                for svc in services:
                    try:
                        out = subprocess.check_output([
                            'journalctl', '-u', f'{svc}.service', '--since', '1 hour ago', '--no-pager'
                        ], text=True, timeout=10)
                        journal_name = f'journal_{svc}.log'
                        zipf.writestr(journal_name, out)
                    except Exception as e:
                        logger.warning(f"Failed to collect journal for {svc}: {e}")
            else:
                logger.warning("journalctl not available; skipping systemd journal logs.")
    except Exception as e:
        logger.error(f"Failed to create log archive: {e}")
        return False
    return True

def upload_log_archive(archive_path):
    """Upload the log archive to Supabase Storage under /<camera_id>/"""
    # Exclude .zip files older than 1 day
    if archive_path.stat().st_mtime < time.time() - 86400:
        logger.info(f"Skipping old archive: {archive_path}")
        return False
    try:
        remote_path = f"{CAMERA_ID}/{archive_path.name}"
        with open(archive_path, 'rb') as f:
            supabase.storage.from_(LOG_BUCKET).upload(remote_path, f)
        logger.info(f"Uploaded log archive to {LOG_BUCKET}/{remote_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload log archive: {e}")
        return False

def ensure_log_bucket():
    try:
        buckets = supabase.storage.list_buckets()
        if not any(b['name'] == LOG_BUCKET for b in buckets):
            supabase.storage.create_bucket(LOG_BUCKET)
            logger.info(f"Created log bucket: {LOG_BUCKET}")
    except Exception as e:
        logger.error(f"Failed to ensure log bucket: {e}")

def main():
    logger.info("Log Collector Service started")
    ensure_log_bucket()
    while True:
        try:
            now = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"{now}_logs.zip"
            archive_path = LOGS_DIR / archive_name
            if collect_logs(archive_path):
                upload_log_archive(archive_path)
                archive_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Log collection/upload failed: {e}")
        time.sleep(UPLOAD_INTERVAL)

if __name__ == "__main__":
    main() 