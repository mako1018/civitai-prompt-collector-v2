import sqlite3, json, argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, default=20)
args = parser.parse_args()
DB = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'
conn = sqlite3.connect(str(DB))
c = conn.cursor()
# collection_state recent rows
c.execute('SELECT id, model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state ORDER BY last_update DESC LIMIT ?', (args.limit,))
rows = c.fetchall()
cols = [d[0] for d in c.description]
states = [dict(zip(cols, r)) for r in rows]
# total prompts
c.execute('SELECT COUNT(*) FROM civitai_prompts')
total = c.fetchone()[0]
conn.close()
print(json.dumps({'db_path': str(DB), 'total_prompts': total, 'collection_state_recent': states}, ensure_ascii=False, indent=2))
