import sqlite3, json
p='data/civitai_dataset.db'
conn=sqlite3.connect(p)
c=conn.cursor()
c.execute("SELECT id, model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state WHERE model_id = ? AND version_id = ?", ('2091367','2091367'))
row=c.fetchone()
conn.close()
print(json.dumps(row, ensure_ascii=False, indent=2))
