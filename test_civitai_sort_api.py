#!/usr/bin/env python3
"""
CivitAI API ソートパラメータのテスト
各ソートオプションが実際に機能するかを検証
"""

import requests
import json
from datetime import datetime

def test_civitai_sort_parameters():
    """CivitAI APIの各ソートパラメータをテスト"""

    print("=== CivitAI API ソートパラメータ検証 ===\n")

    # テストするソートパラメータ
    sort_params = [
        'Most Reactions',
        'Most Downloads',
        'Most Likes',
        'Most Discussed',
        'Newest',
        'Oldest'
    ]

    results = {}

    for sort_param in sort_params:
        print(f"🔍 テスト中: {sort_param}")

        try:
            response = requests.get(
                'https://civitai.com/api/v1/images',
                params={
                    'limit': 5,
                    'sort': sort_param
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                metadata = data.get('metadata', {})

                if items:
                    # 最初のアイテムの統計を確認
                    first_item = items[0]
                    stats = first_item.get('stats', {})

                    result = {
                        'status': 'success',
                        'item_count': len(items),
                        'first_item_stats': {
                            'reactions': stats.get('reactionCount', 0),
                            'downloads': stats.get('downloadCount', 0),
                            'likes': stats.get('likeCount', 0),
                            'comments': stats.get('commentCount', 0)
                        },
                        'metadata': metadata
                    }

                    print(f"  ✅ 成功: {len(items)}件取得")
                    print(f"     リアクション: {stats.get('reactionCount', 0)}")
                    print(f"     ダウンロード: {stats.get('downloadCount', 0)}")
                    print(f"     いいね: {stats.get('likeCount', 0)}")

                else:
                    result = {'status': 'success_no_items', 'message': 'レスポンス成功だがアイテムなし'}
                    print(f"  ✅ 成功だがアイテムなし")

            else:
                result = {
                    'status': 'http_error',
                    'status_code': response.status_code,
                    'error': response.text[:100]
                }
                print(f"  ❌ HTTPエラー: {response.status_code}")
                print(f"     エラー内容: {response.text[:100]}")

        except requests.exceptions.Timeout:
            result = {'status': 'timeout', 'error': 'リクエストタイムアウト'}
            print(f"  ❌ タイムアウト")

        except Exception as e:
            result = {'status': 'exception', 'error': str(e)}
            print(f"  ❌ 例外エラー: {str(e)[:100]}")

        results[sort_param] = result
        print()

    # 結果サマリー
    print("📊 テスト結果サマリー:")
    successful_sorts = []
    failed_sorts = []

    for sort_param, result in results.items():
        if result['status'] == 'success':
            successful_sorts.append(sort_param)
            print(f"  ✅ {sort_param}: 正常動作")
        else:
            failed_sorts.append(sort_param)
            print(f"  ❌ {sort_param}: {result.get('error', '失敗')}")

    print(f"\n📈 結果統計:")
    print(f"  成功: {len(successful_sorts)}/{len(sort_params)}")
    print(f"  失敗: {len(failed_sorts)}/{len(sort_params)}")

    if successful_sorts:
        print(f"\n✅ 使用可能なソートパラメータ:")
        for sort in successful_sorts:
            print(f"  - {sort}")

    if failed_sorts:
        print(f"\n❌ 使用不可能なソートパラメータ:")
        for sort in failed_sorts:
            print(f"  - {sort}")

    return results

def test_specific_model_sort(model_id="974693", version_id="2091367"):
    """特定モデルでのソート動作テスト"""

    print(f"\n=== 特定モデル {model_id}/{version_id} でのソートテスト ===\n")

    working_sorts = ['Most Reactions', 'Newest']  # 事前テストで成功したもの

    for sort_param in working_sorts:
        print(f"🔍 {sort_param} + モデル {model_id} テスト:")

        try:
            response = requests.get(
                'https://civitai.com/api/v1/images',
                params={
                    'modelVersionId': version_id,
                    'sort': sort_param,
                    'limit': 3
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                total_items = data.get('metadata', {}).get('totalItems')

                print(f"  ✅ 成功: {len(items)}件取得 (総数: {total_items})")

                if items:
                    for i, item in enumerate(items[:2]):
                        stats = item.get('stats', {})
                        print(f"    {i+1}. リアクション: {stats.get('reactionCount', 0)} | "
                              f"ダウンロード: {stats.get('downloadCount', 0)}")

            else:
                print(f"  ❌ HTTPエラー: {response.status_code}")

        except Exception as e:
            print(f"  ❌ エラー: {str(e)[:100]}")

        print()

if __name__ == "__main__":
    # 基本ソートパラメータテスト
    results = test_civitai_sort_parameters()

    # 特定モデルでのテスト
    test_specific_model_sort()
