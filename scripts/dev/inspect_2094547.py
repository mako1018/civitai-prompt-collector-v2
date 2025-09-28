import sqlite3

db='data/civitai_dataset.db'
conn=sqlite3.connect(db)
cur=conn.cursor()
print('collect_state rows:')
for r in cur.execute('SELECT id, model_id, model_version_id, total_collected, saved, api_url, updated_at FROM collection_state ORDER BY id'):
    print(r)
print('\nSaved civitai_ids for model_version_id=2094547:')
for r in cur.execute("SELECT civitai_id, id, model_version_id, collected_at FROM civitai_prompts WHERE model_version_id = ? ORDER BY collected_at DESC", ('2094547',)):
    print(r)
print('\nAny rows with raw_metadata containing 2094547: limit 10')
for r in cur.execute("SELECT civitai_id, id, substr(raw_metadata,1,200) FROM civitai_prompts WHERE raw_metadata LIKE ? LIMIT 10", ('%2094547%',)):
    print(r)
conn.close()
print('\nDone')
