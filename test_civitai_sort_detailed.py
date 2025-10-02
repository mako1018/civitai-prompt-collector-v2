#!/usr/bin/env python3
"""
CivitAI API の正確なソートパラメータを確認
公式ドキュメントに基づく正しい値を検証
"""

import requests
import json

def test_exact_sort_values():
    """正確なソートパラメータの値をテスト"""

    print("=== CivitAI API 正確なソートパラメータ検証 ===\n")

    # 推測される正しいソート値
    possible_sorts = [
        # 一般的なパターン
        'Most Reactions',
        'Most Downloads',
        'Most Likes',
        'Most Discussed',
        'Newest',
        'Oldest',

        # 小文字バリエーション
        'most reactions',
        'most downloads',
        'most likes',
        'newest',
        'oldest',

        # アンダースコアバリエーション
        'most_reactions',
        'most_downloads',
        'most_likes',
        'most_discussed',

        # 短縮形
        'reactions',
        'downloads',
        'likes',
        'comments',
        'new',
        'old'
    ]

    working_sorts = []
    failed_sorts = []

    for sort_value in possible_sorts:
        try:
            response = requests.get(
                'https://civitai.com/api/v1/images',
                params={
                    'limit': 2,
                    'sort': sort_value
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])

                print(f"✅ '{sort_value}': 正常 ({len(items)}件)")
                working_sorts.append(sort_value)

            elif response.status_code == 400:
                error_data = response.json().get('error', {})
                if 'invalid_value' in str(error_data):
                    print(f"❌ '{sort_value}': 無効な値")
                else:
                    print(f"❌ '{sort_value}': {response.status_code} - その他エラー")
                failed_sorts.append(sort_value)

            else:
                print(f"❌ '{sort_value}': HTTP {response.status_code}")
                failed_sorts.append(sort_value)

        except Exception as e:
            print(f"❌ '{sort_value}': 例外 - {str(e)[:50]}")
            failed_sorts.append(sort_value)

    print(f"\n📊 検証結果:")
    print(f"✅ 有効なソート値: {len(working_sorts)}個")
    print(f"❌ 無効なソート値: {len(failed_sorts)}個")

    if working_sorts:
        print(f"\n🎯 使用可能なソート値:")
        for sort in working_sorts:
            print(f"  - '{sort}'")

    return working_sorts

def test_nsfw_parameter_combinations():
    """NSFWパラメータとソートの組み合わせテスト"""

    print(f"\n=== NSFWパラメータ + ソート組み合わせテスト ===\n")

    working_sorts = ['Most Reactions', 'Newest', 'Oldest']
    nsfw_levels = ['None', 'Soft', 'Mature', 'X']

    results = {}

    for nsfw in nsfw_levels:
        for sort in working_sorts:
            try:
                response = requests.get(
                    'https://civitai.com/api/v1/images',
                    params={
                        'limit': 2,
                        'sort': sort,
                        'nsfw': nsfw
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    results[f"{nsfw}+{sort}"] = len(items)
                    print(f"✅ NSFW={nsfw} + Sort={sort}: {len(items)}件")
                else:
                    results[f"{nsfw}+{sort}"] = f"Error {response.status_code}"
                    print(f"❌ NSFW={nsfw} + Sort={sort}: HTTP {response.status_code}")

            except Exception as e:
                results[f"{nsfw}+{sort}"] = f"Exception"
                print(f"❌ NSFW={nsfw} + Sort={sort}: 例外")

    print(f"\n📈 NSFW + ソート組み合わせ結果:")
    successful_combinations = []
    for combo, result in results.items():
        if isinstance(result, int):
            successful_combinations.append(combo)

    print(f"✅ 成功組み合わせ: {len(successful_combinations)}個")
    for combo in successful_combinations:
        print(f"  - {combo}")

    return results

if __name__ == "__main__":
    # 正確なソートパラメータを確認
    working_sorts = test_exact_sort_values()

    # NSFWとの組み合わせテスト
    combo_results = test_nsfw_parameter_combinations()
