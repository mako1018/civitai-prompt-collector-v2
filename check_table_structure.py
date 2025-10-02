import sqlite3

conn = sqlite3.connect('data/civitai_dataset.db')
cursor = conn.cursor()

# テーブル構造確認
cursor.execute('PRAGMA table_info(collection_state)')
print('📋 collection_state table structure:')
for row in cursor.fetchall():
    print(f'  {row}')

print('\n📊 Current collection_state data:')
cursor.execute('SELECT * FROM collection_state LIMIT 5')
for row in cursor.fetchall():
    print(f'  {row}')

conn.close()
