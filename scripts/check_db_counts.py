import sqlite3
conn=sqlite3.connect('data/civitai_dataset.db')
cur=conn.cursor()
cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
rows_with_mv = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', ('%2091367%',))
raw_contains = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM civitai_prompts')
total = cur.fetchone()[0]
conn.close()
print(rows_with_mv, raw_contains, total)
