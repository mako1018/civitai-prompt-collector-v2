#!/usr/bin/env python3
"""
Show collection_state and recent prompts summary.
Usage:
  python .\scripts\show_db_summary.py
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
print('DB:', db_path)
try:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    print('\n-- collection_state --')
    try:
        # Query actual columns present in collection_state
        cur.execute('SELECT id, model_id, version_id, last_offset, total_collected, next_page_cursor, last_update FROM collection_state')
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(r)
        else:
            print('(no rows)')
    except Exception as e:
        print('collection_state table not found or query failed:', e)

    print('\n-- recent prompts (last 10) --')
    try:
        cur.execute('SELECT id, model_name, model_id, collected_at FROM civitai_prompts ORDER BY collected_at DESC LIMIT 10')
        for r in cur.fetchall():
            print(r)
    except Exception as e:
        print('civitai_prompts query failed:', e)

    print('\n-- counts --')
    try:
        cur.execute('SELECT COUNT(*) FROM civitai_prompts')
        print('total prompts:', cur.fetchone()[0])
    except Exception as e:
        print('count query failed:', e)

    conn.close()
except Exception as e:
    print('Failed to open DB:', e)
    raise
