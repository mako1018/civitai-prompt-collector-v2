import sqlite3

conn = sqlite3.connect('data/civitai_dataset.db')
cursor = conn.cursor()

print("=== データベース構造確認 ===")

# テーブル一覧
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print(f"テーブル一覧: {tables}")

# civitai_prompts テーブルの構造
if ('civitai_prompts',) in tables:
    cursor.execute('PRAGMA table_info(civitai_prompts)')
    columns = cursor.fetchall()
    print(f"\ncivitai_prompts カラム:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

# データ数確認
cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
total_count = cursor.fetchone()[0]
print(f"\n総レコード数: {total_count}")

# civitai_id での重複チェック
cursor.execute('''
    SELECT civitai_id, COUNT(*) as count
    FROM civitai_prompts
    WHERE civitai_id IS NOT NULL
    GROUP BY civitai_id
    HAVING COUNT(*) > 1
    LIMIT 10
''')
duplicates = cursor.fetchall()

if duplicates:
    print(f"\n重複 civitai_id ({len(duplicates)} 件の例):")
    for dup in duplicates:
        print(f"  civitai_id: {dup[0]} → {dup[1]}回")
else:
    print("\ncivitai_id の重複は見つかりませんでした")

conn.close()
