#!/usr/bin/env python3
"""特定モデルの収集データ分析とNSFW改善効果調査"""
import sqlite3
import sys
sys.path.append('src')

def analyze_model_974693():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    model_id = "974693"
    version_id = "2091367"

    print(f"=== Model {model_id} (Version {version_id}) 詳細分析 ===\n")

    # 1. 基本収集統計
    cursor.execute("""
        SELECT COUNT(*) FROM civitai_prompts
        WHERE model_id = ? OR model_version_id = ?
    """, (model_id, version_id))
    total_count = cursor.fetchone()[0]

    print(f"📊 収集済みデータ統計:")
    print(f"  総収集数: {total_count}件")

    # 2. プロンプトサンプルの確認
    cursor.execute("""
        SELECT full_prompt, quality_score, model_name
        FROM civitai_prompts
        WHERE model_id = ? OR model_version_id = ?
        ORDER BY quality_score DESC
        LIMIT 10
    """, (model_id, version_id))

    samples = cursor.fetchall()
    print(f"\n🎯 収集済みプロンプトサンプル（高品質順）:")
    for i, (prompt, quality, model_name) in enumerate(samples, 1):
        display_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        print(f"  {i}. [Q:{quality}] {display_prompt}")
        if i == 1 and model_name:
            print(f"     モデル名: {model_name}")

    # 3. 現在の性的表現レベル分析
    sexual_keywords = {
        "明示的": ["fuck", "fucking", "cum", "orgasm", "sex", "penetration"],
        "性器": ["pussy", "cock", "penis", "vagina", "nipples", "breasts"],
        "示唆的": ["nude", "naked", "erotic", "seductive", "nsfw", "explicit"],
        "身体": ["ass", "butt", "cleavage", "curves", "body"]
    }

    print(f"\n🔥 現在収集データの性的表現分析:")

    total_sexual_content = 0
    category_stats = {}

    for category, keywords in sexual_keywords.items():
        category_matches = 0
        for keyword in keywords:
            cursor.execute(f"""
                SELECT COUNT(*) FROM civitai_prompts
                WHERE (model_id = ? OR model_version_id = ?)
                AND LOWER(full_prompt) LIKE '%{keyword}%'
            """, (model_id, version_id))

            count = cursor.fetchone()[0]
            if count > 0:
                category_matches += count
                print(f"  {keyword}: {count}件")

        category_stats[category] = category_matches
        total_sexual_content += category_matches
        print(f"  → {category}小計: {category_matches}件")

    print(f"\n性的表現総計: {total_sexual_content}件")
    sexual_ratio = (total_sexual_content / total_count * 100) if total_count > 0 else 0
    print(f"性的コンテンツ比率: {sexual_ratio:.1f}%")

    # 4. 具体的な性的表現サンプル
    cursor.execute("""
        SELECT full_prompt FROM civitai_prompts
        WHERE (model_id = ? OR model_version_id = ?)
        AND (LOWER(full_prompt) LIKE '%nsfw%' OR LOWER(full_prompt) LIKE '%nude%'
             OR LOWER(full_prompt) LIKE '%sex%' OR LOWER(full_prompt) LIKE '%erotic%')
        ORDER BY quality_score DESC
        LIMIT 5
    """, (model_id, version_id))

    sexual_samples = cursor.fetchall()
    print(f"\n🔞 収集済み性的表現サンプル:")
    if sexual_samples:
        for i, (prompt,) in enumerate(sexual_samples, 1):
            print(f"  {i}: {prompt[:120]}...")
    else:
        print("  性的表現を含むプロンプトが見つかりません")

    # 5. NSFWカテゴリ分類状況
    cursor.execute("""
        SELECT COUNT(*) FROM prompt_categories pc
        JOIN civitai_prompts cp ON pc.prompt_id = cp.id
        WHERE pc.category = 'NSFW'
        AND (cp.model_id = ? OR cp.model_version_id = ?)
    """, (model_id, version_id))

    nsfw_classified = cursor.fetchone()[0]
    print(f"\n📋 分類状況:")
    print(f"  NSFWカテゴリ分類済み: {nsfw_classified}件")
    print(f"  NSFW分類率: {(nsfw_classified/total_count*100):.1f}%" if total_count > 0 else "0%")

    conn.close()
    return {
        'total_count': total_count,
        'sexual_content': total_sexual_content,
        'sexual_ratio': sexual_ratio,
        'nsfw_classified': nsfw_classified,
        'category_stats': category_stats
    }

def test_nsfw_collection_for_model():
    """特定モデルでのNSFW収集テスト"""
    print(f"\n" + "="*60)
    print(f"🚀 Model 974693 NSFW専用収集テスト")
    print(f"="*60)

    from nsfw_collector import NSFWCivitAICollector
    import requests
    import time

    collector = NSFWCivitAICollector()

    # NSFWパラメータでの収集テスト
    nsfw_params = {
        "limit": 20,
        "nsfw": "X",  # 明示的NSFW要求
        "modelId": "974693",  # 特定モデルを指定
        "sort": "Newest"
    }

    print(f"📡 API呼び出し中...")

    try:
        headers = collector._get_headers()
        response = requests.get(
            "https://civitai.com/api/v1/images",
            params=nsfw_params,
            headers=headers,
            timeout=30
        )

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            print(f"📄 取得データ: {len(items)}件")

            # 新しいNSFW表現の分析
            new_nsfw_count = 0
            new_explicit_expressions = []

            for item in items:
                full_prompt = ""
                if 'meta' in item and item['meta']:
                    if isinstance(item['meta'], dict):
                        full_prompt = item['meta'].get('prompt', '') or item['meta'].get('Prompt', '')

                if collector._is_explicit_nsfw(full_prompt):
                    new_nsfw_count += 1
                    new_explicit_expressions.append(full_prompt[:150])

            print(f"\n🔥 NSFW専用収集結果:")
            print(f"  NSFW判定: {new_nsfw_count}件/{len(items)}件 ({new_nsfw_count/len(items)*100:.1f}%)")

            if new_explicit_expressions:
                print(f"\n💎 新発見の明示的表現:")
                for i, expr in enumerate(new_explicit_expressions[:5], 1):
                    print(f"  {i}: {expr}...")
            else:
                print(f"\n⚠️ このモデルではNSFW表現が見つかりませんでした")

        else:
            print(f"❌ APIエラー: {response.text[:200]}")

    except Exception as e:
        print(f"💥 接続エラー: {e}")

def compare_improvement():
    """改善効果の比較分析"""
    print(f"\n" + "="*60)
    print(f"📈 改善効果分析")
    print(f"="*60)

    # 既存データ分析
    current_stats = analyze_model_974693()

    # 改善予測
    print(f"\n🎯 NSFW専用収集による改善予測:")
    print(f"  現在の性的表現: {current_stats['sexual_content']}件 ({current_stats['sexual_ratio']:.1f}%)")

    if current_stats['sexual_ratio'] < 5:  # 5%未満の場合
        print(f"  ✅ 大幅改善が期待できます！")
        print(f"    - NSFW専用収集により15-30%の性的表現比率が期待")
        print(f"    - 明示的表現の大幅増加")
        print(f"    - 品質の高い成人向けコンテンツの発見")
    elif current_stats['sexual_ratio'] < 15:
        print(f"  ⚡ 中程度の改善が期待できます")
        print(f"    - より明示的で高品質な表現の追加")
        print(f"    - 性器表現等の直接的語彙の補強")
    else:
        print(f"  📊 既に豊富な性的表現が収集済み")
        print(f"    - さらなる多様性の追加")
        print(f"    - 最新の高品質表現の補完")

    return current_stats

if __name__ == "__main__":
    # 1. 現在の収集データ分析
    current_stats = analyze_model_974693()

    # 2. NSFW専用収集テスト
    test_nsfw_collection_for_model()

    # 3. 改善効果の総合評価
    compare_improvement()
