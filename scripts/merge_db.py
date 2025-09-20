import sqlite3

src='src/data/civitai_dataset.db'
dst='data/civitai_dataset.db'

print('Opening source:', src)
print('Opening dest:', dst)

s_conn=sqlite3.connect(src)
s_cur=s_conn.cursor()

d_conn=sqlite3.connect(dst)
d_cur=d_conn.cursor()

# Ensure tables exist in destination
s_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Src tables:', s_cur.fetchall())

d_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Dst tables:', d_cur.fetchall())

# Copy civitai_prompts rows that do not exist in dst (by civitai_id)
s_cur.execute('SELECT * FROM civitai_prompts')
rows = s_cur.fetchall()
cols = [d[0] for d in s_cur.description]
print('src civitai_prompts cols:', cols)

inserted = 0
for r in rows:
    rowdict = dict(zip(cols, r))
    civid = rowdict.get('civitai_id')
    if civid is None:
        continue
    d_cur.execute('SELECT id FROM civitai_prompts WHERE civitai_id=?', (civid,))
    if d_cur.fetchone():
        continue
    # build insert
    placeholders = ','.join('?' for _ in cols)
    values = [rowdict[c] for c in cols]
    try:
        d_cur.execute(f"INSERT INTO civitai_prompts ({','.join(cols)}) VALUES ({placeholders})", values)
        inserted += 1
    except Exception as e:
        print('insert error', e)

# Copy prompt_categories: assume prompt_ids may differ; try to map by civitai_id
s_cur.execute('SELECT * FROM prompt_categories')
rows = s_cur.fetchall()
cols = [d[0] for d in s_cur.description]
print('src prompt_categories cols:', cols)

inserted_cat=0
for r in rows:
    rowdict = dict(zip(cols, r))
    pid = rowdict.get('prompt_id')
    # find civitai_id for this prompt
    s_cur.execute('SELECT civitai_id FROM civitai_prompts WHERE id=?',(pid,))
    res = s_cur.fetchone()
    if not res:
        continue
    civid = res[0]
    # find new prompt id in dest
    d_cur.execute('SELECT id FROM civitai_prompts WHERE civitai_id=?',(civid,))
    new = d_cur.fetchone()
    if not new:
        continue
    new_pid = new[0]
    # check if category already exists
    d_cur.execute('SELECT id FROM prompt_categories WHERE prompt_id=? AND category=?',(new_pid,rowdict.get('category')))
    if d_cur.fetchone():
        continue
    try:
        # insert with mapped prompt_id
        cols2 = cols.copy()
        vals = [rowdict[c] for c in cols2]
        # replace prompt_id with new_pid
        idx = cols2.index('prompt_id')
        vals[idx]=new_pid
        placeholders = ','.join('?' for _ in cols2)
        d_cur.execute(f"INSERT INTO prompt_categories ({','.join(cols2)}) VALUES ({placeholders})", vals)
        inserted_cat += 1
    except Exception as e:
        print('cat insert error', e)

print('inserts prompts:', inserted, 'categories:', inserted_cat)

d_conn.commit()
d_conn.close()
s_conn.close()

# report final counts
import sqlite3
for p in [dst, src]:
    conn=sqlite3.connect(p)
    cur=conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM civitai_prompts')
        print(p, 'civitai_prompts=', cur.fetchone()[0])
        cur.execute('SELECT COUNT(*) FROM prompt_categories')
        print(p, 'prompt_categories=', cur.fetchone()[0])
    except Exception as e:
        print('error reporting', e)
    conn.close()
