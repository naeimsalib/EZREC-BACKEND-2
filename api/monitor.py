import time
import json
import psutil
from pathlib import Path
from datetime import datetime

SYSTEM_STATUS_FILE = Path("/opt/ezrec-backend/api/local_data/status.json")

def get_status():
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict(),
        "uptime_seconds": time.time() - psutil.boot_time(),
    }

def main():
    SYSTEM_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    while True:
        status = get_status()
        SYSTEM_STATUS_FILE.write_text(json.dumps(status, indent=2))
        time.sleep(3)

if __name__ == "__main__":
    main()
