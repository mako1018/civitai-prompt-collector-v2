#!/usr/bin/env python3
"""Show DB status: grouped counts, collection_state, and sample prompt resources"""
import sqlite3
from pprint import pprint

DB='data/civitai_dataset.db'
print(f"Using DB: {DB}\n")
conn=sqlite3.connect(DB)
cur=conn.cursor()

print("Top model_id / model_version_id counts (limit 50):")
try:
    cur.execute("SELECT COALESCE(model_id,''), COALESCE(model_version_id,''), COUNT(*) as cnt FROM civitai_prompts GROUP BY model_id, model_version_id ORDER BY cnt DESC LIMIT 50")
    rows=cur.fetchall()
    for r in rows:
        print(f"  model_id={r[0] or '(empty)'} / version_id={r[1] or '(empty)'} : {r[2]}")
except Exception as e:
    print('  Failed to query civitai_prompts grouping:', e)

print('\nTotal prompts:')
try:
    cur.execute('SELECT COUNT(*) FROM civitai_prompts')
    print(' ', cur.fetchone()[0])
except Exception as e:
    print('  Failed to get total:', e)

print('\ncollection_state rows (latest 20):')
try:
    cur.execute("SELECT id, model_id, version_id, last_offset, total_collected, next_page_cursor, last_update FROM collection_state ORDER BY id DESC LIMIT 20")
    rows=cur.fetchall()
    if not rows:
        print('  (no rows)')
    else:
        for r in rows:
            print(f"  id={r[0]} model_id={r[1]} version_id={r[2]} last_offset={r[3]} total_collected={r[4]} next_page_cursor={r[5]} last_update={r[6]}")
except Exception as e:
    print('  collection_state query failed:', e)

# sample civitai ids
sample_ids = ['96785312','94670467','94044836','94044842','94044845']
print('\nSample prompts and resources:')
for cid in sample_ids:
    try:
        cur.execute('SELECT id, civitai_id, model_id, model_version_id FROM civitai_prompts WHERE civitai_id = ?', (cid,))
        r = cur.fetchone()
        if not r:
            print(f'  civitai_id={cid}: not found')
            continue
        pid = r[0]
        print(f"  civitai_id={cid} -> prompt.id={pid} model_id={r[2]} model_version_id={r[3]}")
        # resources
        try:
            cur.execute('SELECT resource_index, resource_type, resource_name, resource_model_id, resource_model_version_id, resource_id FROM prompt_resources WHERE prompt_id = ? ORDER BY resource_index', (pid,))
            ress = cur.fetchall()
            if not ress:
                print('    (no resources)')
            else:
                for rr in ress:
                    print(f"    - idx={rr[0]} type={rr[1]} name={rr[2]} modelId={rr[3]} modelVersionId={rr[4]} resourceId={rr[5]}")
        except Exception as e:
            print('    failed to query prompt_resources:', e)
    except Exception as e:
        print('  sample query error:', e)

# also show aggregates of duplicates by model/version for prompts that appear multiple times across runs
print('\nAggregate counts by model_version_id (for prompts that exist):')
try:
    cur.execute("SELECT COALESCE(model_version_id,''), COUNT(*) FROM civitai_prompts GROUP BY model_version_id ORDER BY COUNT(*) DESC LIMIT 50")
    for r in cur.fetchall():
        print(f"  version_id={r[0] or '(empty)'} : {r[1]}")
except Exception as e:
    print('  failed aggregate by model_version_id:', e)

conn.close()
print('\nDone')
