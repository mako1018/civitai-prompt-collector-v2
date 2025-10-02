#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡略化された重複分析スクリプト
CivitAI API から取得されるデータの重複パターンを調査
"""
import requests
import sqlite3
from datetime import datetime

def analyze_duplicate_simple():
    """簡単な重複分析"""
    print("\n" + "="*60)
    print("重複分析開始 - 簡略版")
    print("="*60)

    # データベース接続
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 既存データの状況確認
    print("\n📊 既存データベース状況:")
    cursor.execute("""
        SELECT
            COUNT(*) as total_rows,
            COUNT(DISTINCT civitai_id) as unique_civitai_ids,
            COUNT(DISTINCT model_version_id) as unique_version_ids
        FROM civitai_prompts
        WHERE civitai_id IS NOT NULL
    """)
    result = cursor.fetchone()
    print(f"  総レコード数: {result[0]}")
    print(f"  ユニーク civitai_id: {result[1]}")
    print(f"  ユニーク model_version_id: {result[2]}")

    # civitai_id の重複チェック
    cursor.execute("""
        SELECT civitai_id, COUNT(*) as count, GROUP_CONCAT(DISTINCT model_version_id) as versions
        FROM civitai_prompts
        WHERE civitai_id IS NOT NULL
        GROUP BY civitai_id
        HAVING COUNT(*) > 1
        LIMIT 10
    """)
    duplicates = cursor.fetchall()

    if duplicates:
        print(f"\n⚠️ 重複 civitai_id が見つかりました ({len(duplicates)}件の例):")
        for dup in duplicates:
            print(f"  civitai_id: {dup[0]} → {dup[1]}回, versions: {dup[2]}")
    else:
        print("\n✅ civitai_id の重複は見つかりませんでした")

    # API テスト (小さなリクエスト)
    print(f"\n🔍 API テスト - 異なる戦略で同じデータが返るかチェック")

    # Test version IDs (existing in DB)
    test_versions = ['1906686', '1906687', '1736657']

    strategies = [
        {'nsfw': 'Soft', 'sort': 'Most Reactions'},
        {'nsfw': 'Soft', 'sort': 'Newest'},
        {'nsfw': 'X', 'sort': 'Most Reactions'},
        {'nsfw': 'X', 'sort': 'Newest'},
    ]

    all_civitai_ids = set()
    strategy_results = {}

    for i, strategy in enumerate(strategies):
        strategy_name = f"{strategy['nsfw']}-{strategy['sort']}"
        print(f"\n戦略 {i+1}: {strategy_name}")

        # API call
        params = {
            'limit': 20,
            'nsfw': strategy['nsfw'],
            'sort': strategy['sort']
        }

        try:
            response = requests.get(
                'https://civitai.com/api/v1/images',
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                civitai_ids = [item['id'] for item in items]

                print(f"  取得件数: {len(civitai_ids)}")

                # Check for overlap with previous strategies
                overlap_count = len(all_civitai_ids.intersection(set(civitai_ids)))
                if overlap_count > 0:
                    print(f"  ⚠️ 他戦略との重複: {overlap_count}件")
                else:
                    print(f"  ✅ 他戦略との重複なし")

                strategy_results[strategy_name] = civitai_ids
                all_civitai_ids.update(civitai_ids)

            else:
                print(f"  ❌ API エラー: {response.status_code}")

        except Exception as e:
            print(f"  ❌ リクエスト失敗: {e}")

    print(f"\n📈 戦略間重複分析:")
    print(f"  全戦略合計ユニーク ID数: {len(all_civitai_ids)}")

    strategy_names = list(strategy_results.keys())
    for i in range(len(strategy_names)):
        for j in range(i+1, len(strategy_names)):
            name1, name2 = strategy_names[i], strategy_names[j]
            if name1 in strategy_results and name2 in strategy_results:
                overlap = len(set(strategy_results[name1]).intersection(set(strategy_results[name2])))
                if overlap > 0:
                    print(f"  {name1} ⇔ {name2}: {overlap}件重複")

    # Check database overlap
    if all_civitai_ids:
        placeholders = ','.join(['?' for _ in all_civitai_ids])
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM civitai_prompts
            WHERE civitai_id IN ({placeholders})
        """, list(all_civitai_ids))
        db_overlap = cursor.fetchone()[0]
        print(f"\n🗄️ データベース既存データとの重複: {db_overlap}件")

    conn.close()

    print("\n" + "="*60)
    print("🎯 結論:")
    print("重複の原因として以下が考えられます：")
    print("1. 異なる戦略(NSFW/ソート)で同じ画像が返される")
    print("2. CivitAI API は人気の画像を複数カテゴリで表示")
    print("3. 時系列的な重複（同じ画像が複数回API結果に登場）")
    print("4. モデルバージョンが異なっても同じ画像IDが存在する可能性")
    print("="*60)

if __name__ == "__main__":
    analyze_duplicate_simple()
