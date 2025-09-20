import sqlite3
paths=['data/civitai_dataset.db','src/data/civitai_dataset.db']
for p in paths:
    try:
        conn=sqlite3.connect(p)
        cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM civitai_prompts")
        cnt=cur.fetchone()[0]
        print(p, 'civitai_prompts=',cnt)
        cur.execute("SELECT COUNT(*) FROM prompt_categories")
        cnt2=cur.fetchone()[0]
        print(p, 'prompt_categories=',cnt2)
        conn.close()
    except Exception as e:
        print(p, 'ERROR', e)
