import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()

def show_collection_state():
    print('collection_state rows:')
    cur.execute('SELECT id, model_id, version_id, total_collected, saved, next_page_cursor, last_update FROM collection_state ORDER BY id')
    for r in cur.fetchall():
        print(r)

def show_prompts_for_version(v, limit=20):
    print(f"\nPrompts with model_version_id = {v} (count & sample):")
    try:
        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (v,))
        cnt = cur.fetchone()[0]
    except Exception:
        cnt = 0
    print('count =', cnt)
    try:
        cur.execute('SELECT civitai_id, id, model_name, collected_at FROM civitai_prompts WHERE model_version_id = ? ORDER BY collected_at DESC LIMIT ?', (v, limit))
        rows = cur.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print('error fetching rows:', e)

show_collection_state()
show_prompts_for_version('2091367', limit=10)
show_prompts_for_version('2094547', limit=10)

conn.close()
print('\nDone')
