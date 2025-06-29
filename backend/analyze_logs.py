import os
import re
import subprocess
from pathlib import Path

LOG_PATH = Path('/opt/ezrec-backend/logs/ezrec.log')

print("\n=== EZREC Crash/Log Analyzer ===\n")

if not LOG_PATH.exists():
    print(f"Log file not found: {LOG_PATH}")
else:
    with open(LOG_PATH, 'r') as f:
        lines = f.readlines()
    # Find recent errors and tracebacks
    errors = [l for l in lines if 'ERROR' in l or 'CRITICAL' in l]
    tracebacks = []
    tb = []
    for l in lines:
        if 'Traceback (most recent call last):' in l:
            tb = [l]
        elif tb:
            tb.append(l)
            if l.strip() == '' or l.startswith('202'):
                tracebacks.append(''.join(tb))
                tb = []
    print(f"Found {len(errors)} error/critical log lines.")
    if errors:
        print("Most recent error:")
        print(errors[-1])
    if tracebacks:
        print("Most recent traceback:")
        print(tracebacks[-1])
    else:
        print("No Python tracebacks found in log.")

# Check systemd journal for OOM, segfault, or service failures
print("\n--- Systemd Journal Analysis (last 2 days) ---\n")
try:
    cmd = [
        'journalctl', '-u', 'ezrec-backend.service', '--since', '2 days ago', '--no-pager'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    journal_lines = result.stdout.splitlines()
    crash_lines = [l for l in journal_lines if re.search(r'(fail|error|oom|killed|segfault|core|exited|crash)', l, re.I)]
    print(f"Found {len(crash_lines)} suspicious lines in systemd journal.")
    if crash_lines:
        print("Most recent crash/system error:")
        print(crash_lines[-1])
    else:
        print("No recent systemd-level crashes detected.")
except Exception as e:
    print(f"Failed to analyze systemd journal: {e}")

print("\n--- End of Report ---\n") 