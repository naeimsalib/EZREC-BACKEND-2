#!/usr/bin/env python3
"""
System Status Service
- Collects system info (CPU, memory, disk, temp, network, etc.) every 1 second
- Updates the system_status table in Supabase
- Designed to run as a standalone process (systemd service)
"""
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import psutil
from zoneinfo import ZoneInfo

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = os.getenv('USER_ID')
CAMERA_ID = os.getenv('CAMERA_ID', '0')
LOG_FILE = os.getenv('SYSTEM_STATUS_LOG', '/opt/ezrec-backend/logs/system_status.log')
UPDATE_INTERVAL = int(os.getenv('SYSTEM_STATUS_INTERVAL', '1'))

LOCAL_TZ = ZoneInfo(os.popen('cat /etc/timezone').read().strip()) if os.path.exists('/etc/timezone') else None

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

def get_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            return float(f.read().strip()) / 1000.0
    except:
        return None

def main():
    logger.info("System Status Service started")
    while True:
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            temp_celsius = get_temp()
            now = datetime.now(LOCAL_TZ)
            update_data = {
                'user_id': USER_ID,
                'camera_id': CAMERA_ID,
                'pi_active': True,
                'last_heartbeat': now.isoformat(),
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': (disk.used / disk.total) * 100,
                'temperature_celsius': temp_celsius,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'updated_at': now.isoformat(),
            }
            # Upsert system_status
            existing = supabase.table('system_status').select('id').eq('camera_id', CAMERA_ID).execute()
            if existing.data:
                supabase.table('system_status').update(update_data).eq('camera_id', CAMERA_ID).execute()
            else:
                update_data['id'] = os.urandom(16).hex()
                supabase.table('system_status').insert(update_data).execute()
        except Exception as e:
            logger.error(f"Failed to update system status: {e}")
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main() 