#!/usr/bin/env python3
"""
CivitAI API制限テストスクリプト
"""

import requests
import time

def test_api_limits():
    """APIの制限をテストする"""
    base_url = "https://civitai.com/api/v1/images"

    # 基本的なパラメータ
    base_params = {
        'modelVersionId': '2091367',  # 既知のmodel version ID
        'nsfw': 'X',
        'sort': 'Most Reactions'
    }

    # 異なるlimit値をテスト
    test_limits = [50, 100, 200, 500, 1000]

    print("CivitAI API制限テスト開始...")
    print("=" * 50)

    for limit in test_limits:
        params = base_params.copy()
        params['limit'] = limit

        print(f"\nテスト: limit={limit}")
        print(f"リクエスト: {base_url}")
        print(f"パラメータ: {params}")

        try:
            response = requests.get(base_url, params=params, timeout=10)
            print(f"ステータスコード: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                print(f"✅ 成功 - 取得件数: {len(items)}件")
                if 'metadata' in data:
                    metadata = data['metadata']
                    print(f"   メタデータ: totalItems={metadata.get('totalItems')}, currentPage={metadata.get('currentPage')}")
            else:
                print(f"❌ エラー: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   エラー詳細: {error_data}")
                except:
                    print(f"   レスポンス: {response.text[:200]}...")

        except Exception as e:
            print(f"❌ 例外: {e}")

        # API制限を避けるため1秒待機
        time.sleep(1)

    print("\n" + "=" * 50)
    print("テスト完了")

if __name__ == "__main__":
    test_api_limits()
