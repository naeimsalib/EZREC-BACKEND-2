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

def read_is_recording():
    status_path = '/opt/ezrec-backend/status.json'
    if os.path.exists(status_path):
        try:
            with open(status_path) as f:
                status = json.load(f)
            return status.get('is_recording', False)
        except Exception:
            return False
    return False

last_upload_speed = None
last_download_speed = None

def get_network_status(_cycle=[0]):
    global last_upload_speed, last_download_speed
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
    # Upload/download speed (run speedtest CLI every 12th cycle ~1min)
    _cycle[0] += 1
    if _cycle[0] >= 12:
        try:
            result = subprocess.run(
                ['speedtest', '--format=json'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                # speedtest CLI reports bandwidth in bytes/sec, convert to Mbps
                last_download_speed = round(data['download']['bandwidth'] * 8 / 1_000_000, 2)  # Mbps
                last_upload_speed = round(data['upload']['bandwidth'] * 8 / 1_000_000, 2)      # Mbps
            else:
                log.error(f"Speedtest CLI failed: {result.stderr}")
                last_download_speed = None
                last_upload_speed = None
        except Exception as e:
            log.error(f"Speedtest CLI exception: {e}")
            last_download_speed = None
            last_upload_speed = None
        _cycle[0] = 0
    return {
        'wifi_connected': wifi_connected,
        'signal_strength': signal,
        'upload_speed': last_upload_speed,
        'download_speed': last_download_speed
    }

def main():
    status_path = '/opt/ezrec-backend/status.json'
    while True:
        try:
            # Read the current is_recording value
            is_recording = False
            if os.path.exists(status_path):
                try:
                    with open(status_path) as f:
                        status = json.load(f)
                    is_recording = status.get('is_recording', False)
                except Exception:
                    pass
            status = {
                'cpu_usage': get_cpu_usage(),
                'memory_usage': get_memory_usage(),
                'storage': get_storage(),
                'temperature': get_temperature(),
                'uptime': get_uptime(),
                'errors': get_errors(),
                'recent_recordings': get_recent_recordings(),
                'is_recording': is_recording,  # preserve the value
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