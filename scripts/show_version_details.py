import sqlite3
from pathlib import Path

def inspect_version(conn, v):
    cur = conn.cursor()
    out = {}
    # count rows with model_version_id == v
    try:
        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (v,))
        out['model_version_id_count'] = cur.fetchone()[0]
    except Exception:
        out['model_version_id_count'] = None
    # count rows where raw_metadata contains v
    try:
        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', (f'%{v}%',))
        out['raw_metadata_count'] = cur.fetchone()[0]
    except Exception:
        out['raw_metadata_count'] = None
    # count rows where raw_metadata contains v but model_version_id IS NULL or ''
    try:
        cur.execute("SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ? AND (model_version_id IS NULL OR model_version_id = '')", (f'%{v}%',))
        out['raw_contains_but_no_mv'] = cur.fetchone()[0]
    except Exception:
        out['raw_contains_but_no_mv'] = None
    # sample civitai_ids where model_version_id == v (limit 10)
    try:
        cur.execute('SELECT civitai_id FROM civitai_prompts WHERE model_version_id = ? ORDER BY collected_at DESC LIMIT 10', (v,))
        out['sample_model_version_ids'] = [r[0] for r in cur.fetchall()]
    except Exception:
        out['sample_model_version_ids'] = []
    # sample civitai_ids where raw_metadata contains v but model_version_id is null
    try:
        cur.execute("SELECT civitai_id FROM civitai_prompts WHERE raw_metadata LIKE ? AND (model_version_id IS NULL OR model_version_id = '') ORDER BY collected_at DESC LIMIT 10", (f'%{v}%',))
        out['sample_raw_only'] = [r[0] for r in cur.fetchall()]
    except Exception:
        out['sample_raw_only'] = []
    return out

DB = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(DB))

print('DB:', DB)
for v in ('2091367','2094547'):
    print('\n===== version', v, '=====')
    info = inspect_version(conn, v)
    for k,vv in info.items():
        print(f'{k}: {vv}')

# print collection_state rows for these versions
print('\ncollection_state rows for these versions:')
cur = conn.cursor()
for v in ('2091367','2094547'):
    cur.execute('SELECT * FROM collection_state WHERE version_id = ?', (v,))
    rows = cur.fetchall()
    print(v, rows)

conn.close()
print('\nDone')
