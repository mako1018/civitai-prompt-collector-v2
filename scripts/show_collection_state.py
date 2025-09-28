#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
cur.execute("SELECT id, model_id, version_id, last_offset, total_collected, next_page_cursor, last_update FROM collection_state")
rows = cur.fetchall()
if not rows:
    print('collection_state: (no rows)')
else:
    print('collection_state rows:')
    for r in rows:
        print(r)
conn.close()
