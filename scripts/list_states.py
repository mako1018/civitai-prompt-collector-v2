import sqlite3, json
conn=sqlite3.connect('data/civitai_dataset.db')
c=conn.cursor()
c.execute("SELECT id, model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state WHERE version_id = ? ORDER BY id", ('2091367',))
rows=c.fetchall()
conn.close()
print(json.dumps(rows, ensure_ascii=False, indent=2))
