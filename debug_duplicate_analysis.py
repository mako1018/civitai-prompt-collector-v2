#!/usr/bin/env python3
"""
重複発生の原因を詳細分析するスクリプト
"""

import sqlite3
import requests
from pathlib import Path
import json
import sys

# プロジェクトルートを設定
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'src'))

try:
    import config
    API_BASE_URL = config.API_BASE_URL
    USER_AGENT = config.USER_AGENT
    CIVITAI_API_KEY = config.CIVITAI_API_KEY
    DEFAULT_DB_PATH = config.DEFAULT_DB_PATH
except ImportError:
    print("⚠️ config.pyが見つかりません。デフォルト設定を使用します。")
    API_BASE_URL = "https://civitai.com/api/v1/images"
    USER_AGENT = "Mozilla/5.0"
    CIVITAI_API_KEY = None
    DEFAULT_DB_PATH = "data/civitai_dataset.db"

def analyze_duplicates(version_id):
    """指定されたversion_idで重複分析を実行"""
    print(f"🔍 Version ID {version_id} の重複分析を開始...")

    # データベース接続
    db_path = Path(project_root) / DEFAULT_DB_PATH
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. データベース内の既存データ確認
        cursor.execute("""
            SELECT civitai_id, collected_at, raw_metadata
            FROM civitai_prompts
            WHERE model_version_id = ?
            ORDER BY civitai_id
        """, (str(version_id),))

        existing_data = cursor.fetchall()
        print(f"📊 データベース内の既存データ: {len(existing_data)}件")

        if existing_data:
            print(f"   最小 civitai_id: {min(row[0] for row in existing_data)}")
            print(f"   最大 civitai_id: {max(row[0] for row in existing_data)}")

            # civitai_idの重複チェック
            civitai_ids = [row[0] for row in existing_data]
            unique_ids = set(civitai_ids)
            if len(civitai_ids) != len(unique_ids):
                print(f"⚠️ データベース内でcivitai_idが重複しています！")
                print(f"   総件数: {len(civitai_ids)}, ユニーク件数: {len(unique_ids)}")
            else:
                print(f"✅ データベース内のcivitai_idは全てユニークです")

        # 2. APIから最新データを取得して比較
        print(f"\n🌐 CivitAI APIから最新データを取得中...")

        headers = {"User-Agent": USER_AGENT}
        if CIVITAI_API_KEY:
            headers['Authorization'] = f"Bearer {CIVITAI_API_KEY}"

        # 複数のソート方法でテスト
        sort_methods = ['Most Reactions', 'Newest']
        nsfw_levels = ['Soft', 'X']

        api_results = {}

        for nsfw in nsfw_levels:
            for sort in sort_methods:
                strategy_key = f"{nsfw}+{sort}"
                print(f"   📥 {strategy_key} で取得中...")

                params = {
                    'modelVersionId': version_id,
                    'nsfw': nsfw,
                    'sort': sort,
                    'limit': 50  # 少量でテスト
                }

                try:
                    response = requests.get(API_BASE_URL, params=params, headers=headers, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('items', [])
                        civitai_ids = [str(item['id']) for item in items if item.get('id')]

                        api_results[strategy_key] = {
                            'total_items': len(items),
                            'civitai_ids': civitai_ids,
                            'metadata': data.get('metadata', {})
                        }

                        print(f"      取得件数: {len(items)}件")
                        if civitai_ids:
                            print(f"      ID範囲: {min(civitai_ids)} ~ {max(civitai_ids)}")
                    else:
                        print(f"      ❌ API エラー: HTTP {response.status_code}")
                        api_results[strategy_key] = {'error': response.status_code}

                except Exception as e:
                    print(f"      ❌ 取得エラー: {e}")
                    api_results[strategy_key] = {'error': str(e)}

        # 3. 戦略間での重複分析
        print(f"\n🔍 戦略間での重複分析...")
        all_api_ids = []
        for strategy, result in api_results.items():
            if 'civitai_ids' in result:
                all_api_ids.extend(result['civitai_ids'])
                print(f"   {strategy}: {len(result['civitai_ids'])}件")

        if all_api_ids:
            unique_api_ids = set(all_api_ids)
            print(f"\n📊 API取得結果:")
            print(f"   全戦略合計: {len(all_api_ids)}件")
            print(f"   ユニークID: {len(unique_api_ids)}件")
            print(f"   戦略間重複: {len(all_api_ids) - len(unique_api_ids)}件")

            if len(all_api_ids) != len(unique_api_ids):
                print(f"\n⚠️ 戦略間で重複するcivitai_id:")
                from collections import Counter
                id_counts = Counter(all_api_ids)
                duplicates = {id_: count for id_, count in id_counts.items() if count > 1}
                for dup_id, count in list(duplicates.items())[:10]:  # 最初の10件表示
                    print(f"      ID {dup_id}: {count}回出現")
                if len(duplicates) > 10:
                    print(f"      ... 他 {len(duplicates) - 10} 件")

        # 4. データベース既存データとAPIデータの重複分析
        if existing_data and all_api_ids:
            existing_ids = set(row[0] for row in existing_data)
            api_ids_set = set(all_api_ids)

            overlap = existing_ids.intersection(api_ids_set)
            print(f"\n🔄 データベース既存データとAPIデータの重複:")
            print(f"   既存データ: {len(existing_ids)}件")
            print(f"   API取得データ: {len(api_ids_set)}件")
            print(f"   重複: {len(overlap)}件")
            print(f"   新規データ: {len(api_ids_set) - len(overlap)}件")

            if overlap:
                print(f"   重複ID例: {list(overlap)[:10]}")

        # 5. APIメタデータ分析
        print(f"\n📄 APIメタデータ分析:")
        for strategy, result in api_results.items():
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"   {strategy}:")
                print(f"      totalItems: {metadata.get('totalItems', 'N/A')}")
                print(f"      currentPage: {metadata.get('currentPage', 'N/A')}")
                print(f"      pageSize: {metadata.get('pageSize', 'N/A')}")
                print(f"      nextCursor: {metadata.get('nextCursor', 'N/A')[:20] if metadata.get('nextCursor') else 'N/A'}...")

    finally:
        conn.close()

def main():
    print("🔍 CivitAI 重複分析ツール")
    print("=" * 50)

    version_id = input("分析するVersion ID を入力してください: ").strip()
    if not version_id:
        print("❌ Version ID が入力されていません")
        return

    analyze_duplicates(version_id)

if __name__ == "__main__":
    main()
