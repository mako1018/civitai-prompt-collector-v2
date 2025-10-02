import sqlite3

conn = sqlite3.connect('data/civitai_dataset.db')
cursor = conn.cursor()

print("📋 civitai_prompts table structure:")
cursor.execute('PRAGMA table_info(civitai_prompts)')
for row in cursor.fetchall():
    print(f'  {row}')

print(f"\n📊 Total rows in civitai_prompts:")
cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
total_rows = cursor.fetchone()[0]
print(f'  {total_rows}')

print(f"\n📊 Recent entries (last 5):")
cursor.execute('SELECT civitai_id, model_version_id, full_prompt FROM civitai_prompts ORDER BY collected_at DESC LIMIT 5')
for row in cursor.fetchall():
    civitai_id, version_id, prompt = row
    short_prompt = (prompt[:50] + "...") if prompt and len(prompt) > 50 else prompt
    print(f'  ID:{civitai_id}, Version:{version_id}, Prompt:{short_prompt}')

print(f"\n🎯 Version 2091367 specific data:")
cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
version_count = cursor.fetchone()[0]
print(f'  Version 2091367 entries: {version_count}')

conn.close()
