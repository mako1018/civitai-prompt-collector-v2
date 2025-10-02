#!/usr/bin/env python3
"""
CivitAI API継続収集テスト - モデルバージョン1906686
"""

import requests
import time
import json

def test_continuous_collection():
    """継続収集の問題を調査する"""

    # 指定されたモデルバージョン
    model_version_id = '1906686'
    base_url = "https://civitai.com/api/v1/images"

    print(f"モデルバージョン {model_version_id} のAPI動作テスト")
    print("=" * 60)

    # 1回目: 通常の200件取得
    print("\n🔍 1回目: 通常の200件取得")
    params1 = {
        'modelVersionId': model_version_id,
        'nsfw': 'X',
        'sort': 'Newest',
        'limit': 200
    }

    print(f"パラメータ: {params1}")

    try:
        response1 = requests.get(base_url, params=params1, timeout=30)
        print(f"ステータスコード: {response1.status_code}")

        if response1.status_code == 200:
            data1 = response1.json()
            items1 = data1.get('items', [])
            print(f"取得件数: {len(items1)}件")

            if items1:
                # 最初と最後のIDを確認
                first_id = items1[0].get('id')
                last_id = items1[-1].get('id')
                print(f"最初のID: {first_id}")
                print(f"最後のID: {last_id}")

                # IDの分布を確認
                all_ids = [item.get('id') for item in items1 if item.get('id')]
                all_ids_int = [int(id) for id in all_ids if id]
                all_ids_int.sort(reverse=True)  # 降順ソート（新しい順）

                print(f"ID範囲: {max(all_ids_int)} ~ {min(all_ids_int)}")
                print(f"最新5件のID: {all_ids_int[:5]}")
                print(f"最古5件のID: {all_ids_int[-5:]}")

                # 2回目のテスト用に最大IDを記録
                max_id = max(all_ids_int)

                print(f"\n🔍 2回目: 継続収集シミュレーション（ID {max_id} より新しいデータ）")

                # しばらく待ってから2回目のリクエスト
                time.sleep(2)

                # 2回目: 同じパラメータで再リクエスト
                response2 = requests.get(base_url, params=params1, timeout=30)
                print(f"ステータスコード: {response2.status_code}")

                if response2.status_code == 200:
                    data2 = response2.json()
                    items2 = data2.get('items', [])
                    print(f"2回目取得件数: {len(items2)}件")

                    if items2:
                        # 2回目のIDを確認
                        ids2 = [item.get('id') for item in items2 if item.get('id')]
                        ids2_int = [int(id) for id in ids2 if id]

                        # max_idより新しいIDがあるかチェック
                        newer_ids = [id for id in ids2_int if id > max_id]
                        same_or_older = [id for id in ids2_int if id <= max_id]

                        print(f"2回目の最新ID: {max(ids2_int) if ids2_int else 'なし'}")
                        print(f"1回目の最大ID ({max_id}) より新しいID数: {len(newer_ids)}件")
                        print(f"1回目と同じ・古いID数: {len(same_or_older)}件")

                        if newer_ids:
                            print(f"新しいIDの例: {sorted(newer_ids, reverse=True)[:5]}")

                        # 1回目と2回目で同じデータが返ってきているかチェック
                        common_ids = set(all_ids_int) & set(ids2_int)
                        print(f"1回目と2回目で重複するID数: {len(common_ids)}件")

                        if len(common_ids) == len(all_ids_int):
                            print("⚠️  1回目と2回目で完全に同じデータが返されています")

                        # ページング情報を確認
                        metadata1 = data1.get('metadata', {})
                        metadata2 = data2.get('metadata', {})

                        print(f"\n📄 ページング情報:")
                        print(f"1回目メタデータ: {metadata1}")
                        print(f"2回目メタデータ: {metadata2}")

                        # 3回目: より多くのデータを取得してみる
                        print(f"\n🔍 3回目: limit=100で再テスト")
                        params3 = params1.copy()
                        params3['limit'] = 100

                        time.sleep(2)
                        response3 = requests.get(base_url, params=params3, timeout=30)

                        if response3.status_code == 200:
                            data3 = response3.json()
                            items3 = data3.get('items', [])
                            ids3 = [int(item.get('id')) for item in items3 if item.get('id')]

                            print(f"3回目取得件数: {len(items3)}件")
                            if ids3:
                                print(f"3回目ID範囲: {max(ids3)} ~ {min(ids3)}")

                                # 異なるページのデータが取得できるかテスト
                                unique_to_3rd = set(ids3) - set(all_ids_int)
                                print(f"3回目だけの新しいID数: {len(unique_to_3rd)}件")

        else:
            print(f"❌ エラー: {response1.status_code}")
            try:
                error_data = response1.json()
                print(f"エラー詳細: {error_data}")
            except:
                print(f"レスポンス: {response1.text[:200]}...")

    except Exception as e:
        print(f"❌ 例外: {e}")

    print("\n" + "=" * 60)
    print("継続収集テスト完了")

if __name__ == "__main__":
    test_continuous_collection()
