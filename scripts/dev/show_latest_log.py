import os
from pathlib import Path
from datetime import datetime

logs_dir = Path(__file__).resolve().parent
log_files = list(logs_dir.glob('collect*.log'))
if not log_files:
    print('No collect_*.log files found in', logs_dir)
    raise SystemExit(0)

# pick the most recently modified
latest = max(log_files, key=lambda p: p.stat().st_mtime)
print('Latest log:', latest)
print('Modified:', datetime.fromtimestamp(latest.stat().st_mtime).isoformat())
print('--- tail (last 200 lines) ---')
with open(latest, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.read().splitlines()
    tail = lines[-200:]
    for line in tail:
        print(line)
