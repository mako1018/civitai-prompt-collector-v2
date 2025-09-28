import sqlite3
import json
from src.config import DEFAULT_DB_PATH

conn = sqlite3.connect(DEFAULT_DB_PATH)
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM prompt_categories')
count = c.fetchone()[0]
print('prompt_categories count:', count)

c.execute('SELECT category, COUNT(*) FROM prompt_categories GROUP BY category')
rows = c.fetchall()
print('category breakdown:')
for cat, cnt in rows:
    print(f'  {cat}: {cnt}')

conn.close()
