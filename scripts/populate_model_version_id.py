import sqlite3, json, os
DB = os.path.abspath('data/civitai_dataset.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, civitai_id, raw_metadata, model_version_id FROM civitai_prompts WHERE model_version_id IS NULL OR model_version_id = ''")
rows = cur.fetchall()
print('To process rows:', len(rows))
updated = 0
for rid, civ_id, raw, mv in rows:
    try:
        if not raw:
            continue
        data = json.loads(raw)
        # try several common fields
        found = None
        if isinstance(data.get('modelVersionId'), int) or isinstance(data.get('modelVersionId'), str):
            found = data.get('modelVersionId')
        elif isinstance(data.get('modelVersionIds'), list) and data.get('modelVersionIds'):
            found = data.get('modelVersionIds')[0]
        else:
            # check meta.civitaiResources
            meta = data.get('meta') or {}
            civres = meta.get('civitaiResources') or data.get('civitaiResources') or []
            if isinstance(civres, list):
                for r in civres:
                    if isinstance(r, dict) and r.get('type') == 'checkpoint' and (r.get('modelVersionId') or r.get('id')):
                        found = r.get('modelVersionId') or r.get('id')
                        break
        if found:
            cur.execute('UPDATE civitai_prompts SET model_version_id = ? WHERE id = ?', (str(found), rid))
            updated += 1
    except Exception:
        continue
conn.commit()
conn.close()
print('Updated rows:', updated)
