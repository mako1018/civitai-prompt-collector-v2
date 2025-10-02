#!/usr/bin/env python3
"""
CivitAI APIのページングテスト
"""

import requests
import time

def test_pagination():
    """ページングを使った正しい継続収集をテスト"""

    model_version_id = '1906686'
    base_url = "https://civitai.com/api/v1/images"

    print(f"モデルバージョン {model_version_id} のページングテスト")
    print("=" * 60)

    # 1回目: 通常の200件取得
    print("\n🔍 1回目: 通常の200件取得")
    params1 = {
        'modelVersionId': model_version_id,
        'nsfw': 'X',
        'sort': 'Newest',
        'limit': 50  # テスト用に少なく
    }

    try:
        response1 = requests.get(base_url, params=params1, timeout=30)
        print(f"ステータスコード: {response1.status_code}")

        if response1.status_code == 200:
            data1 = response1.json()
            items1 = data1.get('items', [])
            metadata1 = data1.get('metadata', {})

            print(f"取得件数: {len(items1)}件")

            if items1:
                ids1 = [item.get('id') for item in items1 if item.get('id')]
                print(f"1回目のID例: {ids1[:5]} ... {ids1[-5:]}")

                # 次のページのcursorを取得
                next_cursor = metadata1.get('nextCursor')
                print(f"nextCursor: {next_cursor}")

                if next_cursor:
                    print(f"\n🔍 2回目: cursorを使って次のページを取得")

                    # 2回目: cursorを使って次のページを取得
                    params2 = params1.copy()
                    params2['cursor'] = next_cursor

                    time.sleep(1)
                    response2 = requests.get(base_url, params=params2, timeout=30)
                    print(f"ステータスコード: {response2.status_code}")

                    if response2.status_code == 200:
                        data2 = response2.json()
                        items2 = data2.get('items', [])
                        metadata2 = data2.get('metadata', {})

                        print(f"2回目取得件数: {len(items2)}件")

                        if items2:
                            ids2 = [item.get('id') for item in items2 if item.get('id')]
                            print(f"2回目のID例: {ids2[:5]} ... {ids2[-5:]}")

                            # 重複チェック
                            common_ids = set(ids1) & set(ids2)
                            print(f"重複ID数: {len(common_ids)}件")

                            if len(common_ids) == 0:
                                print("✅ 正常: 1回目と2回目で異なるデータが取得されました")
                            else:
                                print("⚠️  重複あり")

                            # 3回目のテスト
                            next_cursor2 = metadata2.get('nextCursor')
                            if next_cursor2:
                                print(f"\n🔍 3回目: さらに次のページを取得")

                                params3 = params1.copy()
                                params3['cursor'] = next_cursor2

                                time.sleep(1)
                                response3 = requests.get(base_url, params=params3, timeout=30)

                                if response3.status_code == 200:
                                    data3 = response3.json()
                                    items3 = data3.get('items', [])

                                    print(f"3回目取得件数: {len(items3)}件")

                                    if items3:
                                        ids3 = [item.get('id') for item in items3 if item.get('id')]
                                        print(f"3回目のID例: {ids3[:5]} ... {ids3[-5:]}")

                                        # 全体の重複チェック
                                        all_ids = set(ids1) | set(ids2) | set(ids3)
                                        total_unique = len(all_ids)
                                        total_fetched = len(ids1) + len(ids2) + len(ids3)

                                        print(f"合計取得: {total_fetched}件")
                                        print(f"ユニークID: {total_unique}件")
                                        print(f"重複率: {((total_fetched - total_unique) / total_fetched * 100):.1f}%")

    except Exception as e:
        print(f"❌ 例外: {e}")

    print("\n" + "=" * 60)
    print("ページングテスト完了")

if __name__ == "__main__":
    test_pagination()
