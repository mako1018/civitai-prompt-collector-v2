#!/usr/bin/env python3
"""Backfill prompt_resources table from civitai_prompts.raw_metadata for entire DB.

Behavior:
- Creates a timestamped backup of the DB file (data/civitai_dataset.db.YYYYMMDDHHMMSS.bak)
- Ensures prompt_resources table exists (CREATE TABLE IF NOT EXISTS)
- Iterates all rows in civitai_prompts, parses raw_metadata, extracts civitaiResources
- Inserts resources via DatabaseManager.save_prompt_resources (DELETE+INSERT sync)

Note: may take a few minutes on large DBs. Run from project root.
"""
import os
import sys
import shutil
import time
import json
from datetime import datetime

# Ensure project root is on sys.path so `src` package imports work when run as a script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database import create_database

DB_PATH = 'data/civitai_dataset.db'

def backup_db(path: str) -> str:
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    bak = f"{path}.{ts}.bak"
    shutil.copy2(path, bak)
    return bak


def ensure_prompt_resources_table(db_path: str):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS prompt_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            resource_index INTEGER,
            resource_type TEXT,
            resource_name TEXT,
            resource_model_id TEXT,
            resource_model_version_id TEXT,
            resource_id TEXT,
            resource_raw TEXT,
            FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
        )
    ''')
    conn.commit()
    conn.close()


def parse_resources_from_raw(raw_text: str):
    try:
        parsed = json.loads(raw_text)
    except Exception:
        return []
    meta = parsed.get('meta') or parsed.get('metadata') or {}
    civres = meta.get('civitaiResources') or parsed.get('civitaiResources') or []
    resources = []
    if isinstance(civres, list):
        for idx, r in enumerate(civres):
            if not isinstance(r, dict):
                continue
            resources.append({
                'index': idx,
                'type': r.get('type') or r.get('resourceType') or '',
                'name': r.get('name') or r.get('resourceName') or r.get('checkpointName') or '',
                'modelId': str(r.get('modelId') or r.get('model') or ''),
                'modelVersionId': str(r.get('modelVersionId') or r.get('id') or ''),
                'resourceId': str(r.get('id') or r.get('resourceId') or ''),
                'raw': json.dumps(r, ensure_ascii=False)
            })
    return resources


def main():
    if not os.path.exists(DB_PATH):
        print('DB not found at', DB_PATH)
        return

    print('Backing up DB...')
    bak = backup_db(DB_PATH)
    print('Backup created:', bak)

    print('Ensuring prompt_resources table exists...')
    ensure_prompt_resources_table(DB_PATH)

    db = create_database(DB_PATH)

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, civitai_id, raw_metadata FROM civitai_prompts')

    total = 0
    found = 0
    saved = 0
    start = time.time()

    for row in cur.fetchall():
        total += 1
        pid = row[0]
        raw = row[2]
        if not raw:
            continue
        resources = parse_resources_from_raw(raw)
        if resources:
            found += 1
            try:
                ok = db.save_prompt_resources(pid, resources)
                if ok:
                    saved += 1
            except Exception as e:
                print(f'Failed to save resources for prompt_id={pid}: {e}')
        if total % 1000 == 0:
            elapsed = time.time() - start
            print(f'  processed {total} rows ({found} with resources, {saved} saved) - elapsed {elapsed:.1f}s')

    elapsed = time.time() - start
    print('\nBackfill completed')
    print(f'  total rows processed: {total}')
    print(f'  prompts with resources found: {found}')
    print(f'  prompts saved to prompt_resources: {saved}')
    print(f'  elapsed: {elapsed:.1f}s')

if __name__ == '__main__':
    main()
