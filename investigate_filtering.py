#!/usr/bin/env python3
"""CivitAI収集フィルタリング調査スクリプト"""
import sqlite3
import sys
sys.path.append('src')

def investigate_collection_filtering():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    print("=== CivitAI収集フィルタリング調査 ===\n")

    # 1. 収集されたデータの基本統計
    cursor.execute("SELECT COUNT(*) FROM civitai_prompts")
    total_prompts = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(collected_at), MAX(collected_at) FROM civitai_prompts")
    date_range = cursor.fetchone()

    print(f"📊 収集データ統計:")
    print(f"  総プロンプト数: {total_prompts}件")
    print(f"  収集期間: {date_range[0]} ～ {date_range[1]}")

    # 2. NSFWフラグの確認（テーブルにnsfw列がない場合はスキップ）
    nsfw_available = False
    try:
        cursor.execute("""
            SELECT
                SUM(CASE WHEN nsfw = 1 THEN 1 ELSE 0 END) as nsfw_count,
                SUM(CASE WHEN nsfw = 0 THEN 1 ELSE 0 END) as sfw_count,
                COUNT(*) as total
            FROM civitai_prompts
        """)
        nsfw_stats = cursor.fetchone()
        nsfw_available = True
    except sqlite3.OperationalError:
        nsfw_stats = (0, total_prompts, total_prompts)
        nsfw_available = False

    print(f"\n📋 NSFWフラグ統計:")
    if nsfw_available:
        print(f"  NSFW flagged: {nsfw_stats[0]}件 ({(nsfw_stats[0]/nsfw_stats[2]*100):.1f}%)")
        print(f"  SFW flagged: {nsfw_stats[1]}件 ({(nsfw_stats[1]/nsfw_stats[2]*100):.1f}%)")
    else:
        print(f"  NSFWフラグカラム未実装 - 代替方法で分析")

    # 3. 空のプロンプトの確認
    cursor.execute("""
        SELECT COUNT(*) FROM civitai_prompts
        WHERE full_prompt IS NULL OR full_prompt = '' OR LENGTH(full_prompt) < 10
    """)
    empty_prompts = cursor.fetchone()[0]

    print(f"\n🚫 空/短いプロンプト:")
    print(f"  空または10文字未満: {empty_prompts}件 ({(empty_prompts/total_prompts*100):.1f}%)")

    # 4. プロンプト長の分布
    cursor.execute("""
        SELECT
            CASE
                WHEN LENGTH(full_prompt) < 50 THEN 'Very Short (<50)'
                WHEN LENGTH(full_prompt) < 100 THEN 'Short (50-99)'
                WHEN LENGTH(full_prompt) < 200 THEN 'Medium (100-199)'
                WHEN LENGTH(full_prompt) < 500 THEN 'Long (200-499)'
                ELSE 'Very Long (500+)'
            END as length_category,
            COUNT(*) as count
        FROM civitai_prompts
        WHERE full_prompt IS NOT NULL AND full_prompt != ''
        GROUP BY length_category
        ORDER BY MIN(LENGTH(full_prompt))
    """)

    length_distribution = cursor.fetchall()
    print(f"\n📏 プロンプト長分布:")
    for category, count in length_distribution:
        percentage = (count / total_prompts * 100) if total_prompts > 0 else 0
        print(f"  {category}: {count}件 ({percentage:.1f}%)")

    # 5. 収集されたモデルの種類確認
    cursor.execute("""
        SELECT model_name, COUNT(*) as count
        FROM civitai_prompts
        WHERE model_name IS NOT NULL AND model_name != ''
        GROUP BY model_name
        ORDER BY count DESC
        LIMIT 10
    """)

    top_models = cursor.fetchall()
    print(f"\n🎨 収集された主要モデル:")
    for model, count in top_models:
        print(f"  {model}: {count}件")

    # 6. 実際に露骨な表現が含まれているプロンプトの詳細調査
    explicit_keywords = [
        'fuck', 'fucking', 'fucked',
        'cum', 'cumming', 'cumshot', 'creampie',
        'orgasm', 'climax', 'masturbat',
        'blowjob', 'oral sex', 'anal sex',
        'penetrat', 'thrust', 'pound',
        'moan', 'scream', 'gasp'
    ]

    print(f"\n🔥 露骨な表現の詳細調査:")

    total_explicit = 0
    for keyword in explicit_keywords:
        cursor.execute(f"""
            SELECT COUNT(*) FROM civitai_prompts
            WHERE LOWER(full_prompt) LIKE '%{keyword}%'
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  {keyword}: {count}件")
            total_explicit += count

    print(f"  → 露骨表現総計: {total_explicit}件")

    # 7. 収集時の品質スコアフィルタリング確認
    cursor.execute("""
        SELECT
            CASE
                WHEN quality_score >= 20 THEN 'Excellent (20+)'
                WHEN quality_score >= 15 THEN 'High (15-19)'
                WHEN quality_score >= 10 THEN 'Good (10-14)'
                WHEN quality_score >= 5 THEN 'Fair (5-9)'
                ELSE 'Low (0-4)'
            END as quality_range,
            COUNT(*) as count
        FROM civitai_prompts
        GROUP BY quality_range
        ORDER BY MIN(quality_score) DESC
    """)

    quality_distribution = cursor.fetchall()
    print(f"\n⭐ 品質スコア分布:")
    for range_name, count in quality_distribution:
        percentage = (count / total_prompts * 100) if total_prompts > 0 else 0
        print(f"  {range_name}: {count}件 ({percentage:.1f}%)")

    # 8. 実際の露骨なプロンプトサンプル
    cursor.execute("""
        SELECT full_prompt, quality_score
        FROM civitai_prompts
        WHERE (LOWER(full_prompt) LIKE '%fuck%' OR LOWER(full_prompt) LIKE '%cum%'
               OR LOWER(full_prompt) LIKE '%orgasm%' OR LOWER(full_prompt) LIKE '%sex%')
        AND LENGTH(full_prompt) > 50
        ORDER BY quality_score DESC
        LIMIT 5
    """)

    explicit_samples = cursor.fetchall()
    print(f"\n🔍 収集された露骨プロンプトサンプル:")
    for i, (prompt, quality) in enumerate(explicit_samples, 1):
        print(f"  {i}. [Q:{quality}] {prompt[:100]}...")

    # 9. 収集状態テーブルの確認（収集設定の調査）
    cursor.execute("SELECT * FROM collection_state ORDER BY last_update DESC LIMIT 5")
    collection_states = cursor.fetchall()

    print(f"\n🔄 最近の収集状態:")
    for state in collection_states:
        print(f"  Model: {state[1] if state[1] else 'ALL'}, "
              f"Version: {state[2]}, "
              f"Last Offset: {state[3]}, "
              f"Total Collected: {state[4]}, "
              f"Status: {state[6] if len(state) > 6 else 'N/A'}")

    # 10. 収集フィルタリングの推測
    print(f"\n🤔 収集フィルタリング推測:")

    # NSFWフィルタリングの可能性
    if nsfw_available and nsfw_stats[0] < nsfw_stats[1] * 0.1:  # NSFWが10%未満
        print(f"  ❌ NSFWコンテンツが意図的にフィルタリングされている可能性")
    elif not nsfw_available:
        print(f"  ❓ NSFWフラグが記録されていない（収集時にNSFWフィルタリングされた可能性）")

    # 品質フィルタリングの可能性
    low_quality = sum(count for range_name, count in quality_distribution
                     if 'Low' in range_name or 'Fair' in range_name)
    if low_quality > total_prompts * 0.7:
        print(f"  ⚠️ 低品質コンテンツが多い（品質フィルタが無効の可能性）")

    # 短いプロンプトの多さ
    short_prompts = sum(count for category, count in length_distribution
                       if 'Short' in category or 'Very Short' in category)
    if short_prompts > total_prompts * 0.5:
        print(f"  📝 短いプロンプトが多い（詳細な性的表現が省略されている可能性）")

    conn.close()

if __name__ == "__main__":
    investigate_collection_filtering()
