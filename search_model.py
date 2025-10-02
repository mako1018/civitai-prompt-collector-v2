#!/usr/bin/env python3
"""モデル974693検索スクリプト"""
import sqlite3

conn = sqlite3.connect('data/civitai_dataset.db')
cursor = conn.cursor()

print("=== Model 974693 / Version 2091367 検索 ===")

# 1. 直接的なID検索
cursor.execute("""
    SELECT DISTINCT model_id, model_name, COUNT(*)
    FROM civitai_prompts
    WHERE model_id LIKE '%974693%' OR model_name LIKE '%974693%'
    GROUP BY model_id, model_name
""")
results1 = cursor.fetchall()

print("📋 モデルID 974693 検索結果:")
for result in results1:
    print(f"  Model ID: {result[0]}, Name: {result[1]}, Count: {result[2]}")

# 2. バージョンID検索
cursor.execute("""
    SELECT DISTINCT model_version_id, model_name, COUNT(*)
    FROM civitai_prompts
    WHERE model_version_id LIKE '%2091367%'
    GROUP BY model_version_id, model_name
""")
results2 = cursor.fetchall()

print(f"\n📋 バージョンID 2091367 検索結果:")
for result in results2:
    print(f"  Version ID: {result[0]}, Name: {result[1]}, Count: {result[2]}")

# 3. URN形式検索
cursor.execute("""
    SELECT model_name, model_id, model_version_id, COUNT(*)
    FROM civitai_prompts
    WHERE model_name LIKE '%974693%' OR model_name LIKE '%2091367%'
    GROUP BY model_name
    ORDER BY COUNT(*) DESC
""")
results3 = cursor.fetchall()

print(f"\n📋 URN形式検索結果:")
for result in results3:
    print(f"  Name: {result[0]}")
    print(f"  Model ID: {result[1]}, Version ID: {result[2]}, Count: {result[3]}")

# 4. データベース内のすべてのモデルを表示（上位20件）
cursor.execute("""
    SELECT model_name, COUNT(*) as count
    FROM civitai_prompts
    WHERE model_name IS NOT NULL AND model_name != ''
    GROUP BY model_name
    ORDER BY count DESC
    LIMIT 20
""")
all_models = cursor.fetchall()

print(f"\n📋 データベース内の主要モデル（上位20件）:")
for model, count in all_models:
    print(f"  {model}: {count}件")
    if "974693" in model or "2091367" in model:
        print(f"    ★ 該当モデル発見!")

conn.close()
