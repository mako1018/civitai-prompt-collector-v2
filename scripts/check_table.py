import sqlite3, json
p='data/civitai_dataset.db'
conn=sqlite3.connect(p)
c=conn.cursor()
c.execute("PRAGMA table_info(collection_state)")
cols=c.fetchall()
conn.close()
print(json.dumps(cols, ensure_ascii=False, indent=2))
