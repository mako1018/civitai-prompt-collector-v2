"""
Automated UI test script (runs similar flow to UI):
1. Fetch model metadata for a given model id
2. Pick first model version id
3. Launch scripts/run_one_collect.py as a subprocess with --version-id and --max-items
4. Wait briefly, then query collection_state for that version and print the JSON
5. Tail Streamlit logs and the run_one_collect log

Run from project root with: python scripts/automated_ui_test.py
"""

import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.collector import CivitaiAPIClient
from src.database import DatabaseManager

LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(exist_ok=True)

MODEL_ID = 2091367
MAX_ITEMS = 10

def main():
    client = CivitaiAPIClient()
    print('[test] Fetching model metadata for', MODEL_ID)
    model_meta = client.get_model_meta(MODEL_ID)
    if not model_meta:
        print('[test] Failed to fetch model metadata')
    else:
        print('[test] model title:', model_meta.get('name'))

    # pick a version id (if available)
    version_id = None
    if model_meta and isinstance(model_meta, dict):
        mvs = model_meta.get('modelVersions') or []
        if mvs:
            version_id = mvs[0].get('id')
    print('[test] Selected version_id =', version_id)

    # If we don't have a version_id, do not attempt to start the runner because
    # scripts/run_one_collect.py requires both --model-id and --version-id.
    if not version_id:
        print('[test] No version_id available; skipping runner start to avoid argument errors.')
        print('[test] If you want to test runner start, choose a valid model/version and re-run this script.')
        proc = None
        runner_log = None
    else:
        # start runner with both required args
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        runner_log = LOGS_DIR / f'run_one_collect_m{MODEL_ID}_v{version_id}_{timestamp}.log'
        args = [sys.executable, str(Path('scripts') / 'run_one_collect.py'), '--model-id', str(MODEL_ID), '--version-id', str(version_id), '--max-items', str(MAX_ITEMS)]
        print('[test] Starting runner:', ' '.join(args))
        with open(runner_log, 'wb') as outf:
            proc = subprocess.Popen(args, stdout=outf, stderr=subprocess.STDOUT)
        print('[test] runner pid', proc.pid, 'log:', runner_log)

    # wait a bit for it to do work
    time.sleep(12)

    # read DB collection_state
    db = DatabaseManager()
    rows = db.get_collection_state_for_version(version_id)
    print('[test] collection_state rows:')
    print(json.dumps(rows, ensure_ascii=False, indent=2))

    # Also check summary_json specifically
    try:
        conn = db._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT summary_json FROM collection_state WHERE model_id = ? AND version_id = ?", (str(MODEL_ID), str(version_id)))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            summary = json.loads(row[0])
            print('[test] summary_json from DB:')
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print('[test] No summary_json in DB')
    except Exception as e:
        print('[test] Failed to read summary_json:', e)

    # tail run_one_collect log
    print('\n[test] Tail of runner log:')
    try:
        with open(runner_log, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            seek_pos = max(0, size - 2000)
            f.seek(seek_pos)
            print(f.read().decode('utf-8', errors='replace'))
    except Exception as e:
        print('[test] Failed to read runner log:', e)

    # tail streamlit log
    streamlit_log = LOGS_DIR / 'streamlit_8504.log'
    print('\n[test] Tail of streamlit log:')
    if streamlit_log.exists():
        with open(streamlit_log, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            seek_pos = max(0, size - 2000)
            f.seek(seek_pos)
            print(f.read().decode('utf-8', errors='replace'))
    else:
        print('[test] streamlit log not found at', streamlit_log)

if __name__ == '__main__':
    main()
