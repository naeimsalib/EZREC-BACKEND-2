import os
import time
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/opt/ezrec-backend/logs/status_updater.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("status_updater")

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    mem = psutil.virtual_memory()
    return {'percent': mem.percent, 'used': mem.used, 'total': mem.total}

def get_storage():
    disk = psutil.disk_usage('/')
    return {'percent': disk.percent, 'used': disk.used, 'total': disk.total, 'free': disk.free}

def get_temperature():
    try:
        out = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        return float(out.replace('temp=', '').replace("'C\n", ''))
    except Exception:
        return None

def get_uptime():
    return int(time.time() - psutil.boot_time())

def get_errors(log_path='/opt/ezrec-backend/logs/ezrec.log', n=10):
    if not os.path.exists(log_path):
        return []
    with open(log_path) as f:
        lines = f.readlines()
    return [l.strip() for l in lines if 'error' in l.lower()][-n:]

def get_recent_recordings(recordings_dir='/opt/ezrec-backend/recordings', n=5):
    recs = []
    for root, dirs, files in os.walk(recordings_dir):
        for file in files:
            if file.endswith('.mp4'):
                path = os.path.join(root, file)
                recs.append({'file': file, 'mtime': os.path.getmtime(path)})
    recs.sort(key=lambda x: x['mtime'], reverse=True)
    return [r['file'] for r in recs[:n]]

def is_recording(lock_dir='/opt/ezrec-backend/recordings'):
    # If any .lock file exists, assume recording
    for root, dirs, files in os.walk(lock_dir):
        for file in files:
            if file.endswith('.lock'):
                return True
    return False

def get_network_status():
    # Check wifi connection and signal strength
    try:
        out = subprocess.check_output(['iwgetid'], stderr=subprocess.DEVNULL).decode()
        wifi_connected = 'ESSID' in out
    except Exception:
        wifi_connected = False
    signal = None
    try:
        out = subprocess.check_output(['iwconfig'], stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            if 'Signal level' in line:
                parts = line.split('Signal level=')
                if len(parts) > 1:
                    signal = parts[1].split(' ')[0]
                    break
    except Exception:
        signal = None
    # Get upload/download speed (dummy, real test would use speedtest-cli)
    upload_speed = None
    download_speed = None
    return {
        'wifi_connected': wifi_connected,
        'signal_strength': signal,
        'upload_speed': upload_speed,
        'download_speed': download_speed
    }

def main():
    status_path = '/opt/ezrec-backend/status.json'
    while True:
        try:
            status = {
                'cpu_usage': get_cpu_usage(),
                'memory_usage': get_memory_usage(),
                'storage': get_storage(),
                'temperature': get_temperature(),
                'uptime': get_uptime(),
                'errors': get_errors(),
                'recent_recordings': get_recent_recordings(),
                'is_recording': is_recording(),
                'network': get_network_status(),
                'timestamp': datetime.now().isoformat()
            }
            with open(status_path, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            log.error(f"Failed to update status.json: {e}")
        time.sleep(5)

if __name__ == '__main__':
    main() 