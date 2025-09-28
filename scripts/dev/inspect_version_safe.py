import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
print('DB:', db_path)
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

print('\nPRAGMA table_info(collection_state)')
try:
    cur.execute("PRAGMA table_info(collection_state)")
    cols = cur.fetchall()
    for c in cols:
        print(c)
except Exception as e:
    print('collection_state not found or error:', e)

print('\nPRAGMA table_info(civitai_prompts)')
cur.execute("PRAGMA table_info(civitai_prompts)")
cols2 = cur.fetchall()
for c in cols2:
    print(c)

# show collection_state rows (safe columns)
print('\ncollection_state rows (select *) limit 20:')
try:
    cur.execute('SELECT * FROM collection_state LIMIT 20')
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('could not select from collection_state:', e)

# determine candidate column names for version in civitai_prompts
col_names = [c[1] for c in cols2]
print('\ncolumns in civitai_prompts:', col_names)

target = '2094547'
found_rows = []
if 'model_version_id' in col_names:
    q = 'SELECT civitai_id, id, model_version_id, collected_at FROM civitai_prompts WHERE model_version_id = ? ORDER BY collected_at DESC'
    cur.execute(q, (target,))
    found_rows = cur.fetchall()
    print(f"\nRows where model_version_id = {target}: {len(found_rows)}")
elif 'version_id' in col_names:
    q = 'SELECT civitai_id, id, version_id, collected_at FROM civitai_prompts WHERE version_id = ? ORDER BY collected_at DESC'
    cur.execute(q, (target,))
    found_rows = cur.fetchall()
    print(f"\nRows where version_id = {target}: {len(found_rows)}")
else:
    print('\nNo explicit model_version column found; searching raw_metadata...')
    q = "SELECT civitai_id, id, substr(raw_metadata,1,200), collected_at FROM civitai_prompts WHERE raw_metadata LIKE ? ORDER BY collected_at DESC LIMIT 200"
    cur.execute(q, (f'%{target}%',))
    found_rows = cur.fetchall()
    print(f"Rows where raw_metadata contains {target}: {len(found_rows)} (sample up to 200)")

# print a few samples
print('\nSample rows:')
for r in found_rows[:20]:
    print(r)

# show total counts and last 50 civitai_ids
print('\nLatest 50 civitai_ids in DB (most recent collected_at):')
try:
    cur.execute('SELECT civitai_id, collected_at FROM civitai_prompts ORDER BY collected_at DESC LIMIT 50')
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('could not list latest civitai_ids:', e)

conn.close()
print('\nDone')
