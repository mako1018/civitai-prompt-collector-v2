import sqlite3
import json
DB=r"C:\APP\civitai-prompt-collector-v2\data\civitai_dataset.db"
try:
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    def count(q, params=()):
        cur.execute(q, params)
        r = cur.fetchone()
        return r[0] if r else 0

    total = count('SELECT COUNT(*) FROM civitai_prompts')
    c_modelid_1705430 = count('SELECT COUNT(*) FROM civitai_prompts WHERE model_id = ?', ('1705430',))
    c_modelid_1934796 = count('SELECT COUNT(*) FROM civitai_prompts WHERE model_id = ?', ('1934796',))
    c_raw_contains_1705430 = count('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', ('%1705430%',))
    c_raw_contains_1934796 = count('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', ('%1934796%',))

    print('TOTAL_ROWS:', total)
    print('model_id == 1705430 :', c_modelid_1705430)
    print('model_id == 1934796 :', c_modelid_1934796)
    print("raw_metadata CONTAINS '1705430':", c_raw_contains_1705430)
    print("raw_metadata CONTAINS '1934796':", c_raw_contains_1934796)

    print('\nSAMPLES where raw_metadata contains 1934796 (up to 5 rows):')
    cur.execute('SELECT civitai_id, model_id, model_name, substr(raw_metadata,1,800) FROM civitai_prompts WHERE raw_metadata LIKE ? LIMIT 5', ('%1934796%',))
    rows = cur.fetchall()
    for r in rows:
        print(json.dumps({'civitai_id': r[0], 'model_id': r[1], 'model_name': r[2], 'raw_metadata_snippet': r[3]}, ensure_ascii=False))

    conn.close()
except Exception as e:
    print('ERROR:', e)
    raise
