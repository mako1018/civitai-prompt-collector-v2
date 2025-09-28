import sqlite3
from pathlib import Path

v = '2094547'
DB = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(DB))
cur = conn.cursor()

print('DB:', DB)
print('\nDistinct model_name/model_id for rows with model_version_id =', v)
try:
    cur.execute('SELECT DISTINCT model_name, model_id FROM civitai_prompts WHERE model_version_id = ?', (v,))
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('query failed:', e)

print('\nSample raw_metadata snippets containing the version id:')
try:
    cur.execute("SELECT civitai_id, substr(raw_metadata,1,400) FROM civitai_prompts WHERE raw_metadata LIKE ? LIMIT 10", (f'%{v}%',))
    for r in cur.fetchall():
        print(r[0])
        print(r[1])
        print('---')
except Exception as e:
    print('raw metadata query failed:', e)

# If not found, fallback: see collection_state to find model_id (if stored)
print('\ncollection_state rows for this version (if any):')
try:
    cur.execute('SELECT * FROM collection_state WHERE version_id = ?', (v,))
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('collection_state query failed:', e)

conn.close()
print('\nDone')
