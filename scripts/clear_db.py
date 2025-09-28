#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
tables = ['prompt_categories','civitai_prompts','collection_state']
for t in tables:
    try:
        cur.execute(f"DELETE FROM {t}")
        print('Cleared', t)
    except Exception as e:
        print('Failed to clear', t, e)
conn.commit()
cur.execute('VACUUM')
print('VACUUM done')
conn.close()
