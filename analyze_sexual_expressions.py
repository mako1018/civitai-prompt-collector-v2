#!/usr/bin/env python3
"""性的表現専用の詳細分析スクリプト"""
import sqlite3
import sys
sys.path.append('src')

def analyze_sexual_expressions():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 1. 性行為関連の具体的キーワード検索
    sexual_act_keywords = [
        'sex', 'fucking', 'penetration', 'insertion', 'thrusting',
        'oral', 'blowjob', 'fellatio', 'cunnilingus', 'licking',
        'fingering', 'touching', 'groping', 'fondling', 'caressing',
        'kiss', 'kissing', 'making out', 'french kiss',
        'missionary', 'doggy', 'cowgirl', 'reverse cowgirl',
        'anal', 'vaginal', 'creampie', 'cumshot', 'orgasm', 'climax',
        'masturbation', 'self pleasure', 'solo play'
    ]

    # 2. 性的器官の詳細表現
    sexual_anatomy_keywords = [
        'pussy', 'vagina', 'cunt', 'slit', 'labia', 'clitoris', 'clit',
        'penis', 'cock', 'dick', 'shaft', 'glans', 'balls', 'testicles',
        'nipples', 'areola', 'breasts', 'boobs', 'tits', 'chest',
        'ass', 'buttocks', 'anus', 'asshole', 'butt', 'rear'
    ]

    # 3. 性的状態・形容表現
    sexual_descriptors = [
        'wet', 'moist', 'dripping', 'soaked', 'juicy', 'slippery',
        'hard', 'erect', 'stiff', 'throbbing', 'pulsing',
        'tight', 'loose', 'stretched', 'gaping', 'spread',
        'swollen', 'engorged', 'sensitive', 'tender',
        'aroused', 'horny', 'lustful', 'passionate', 'heated',
        'moaning', 'gasping', 'panting', 'breathless', 'sweating'
    ]

    # 4. 性的衣装・状況
    sexual_context = [
        'naked', 'nude', 'undressed', 'stripped', 'exposed',
        'lingerie', 'underwear', 'panties', 'bra', 'stockings',
        'fishnet', 'garter', 'corset', 'bustier', 'teddy',
        'transparent', 'see-through', 'sheer', 'revealing',
        'topless', 'bottomless', 'partial nudity', 'wardrobe malfunction',
        'bedroom', 'bed', 'shower', 'bath', 'hotel room',
        'intimate', 'private', 'secluded', 'alone together'
    ]

    print("=== 性的表現の詳細分析 ===\n")

    all_categories = {
        "性行為関連": sexual_act_keywords,
        "性器・身体部位": sexual_anatomy_keywords,
        "性的形容・状態": sexual_descriptors,
        "性的状況・衣装": sexual_context
    }

    total_sexual_matches = 0
    category_details = {}

    for category_name, keywords in all_categories.items():
        print(f"### {category_name} ###")
        category_total = 0
        category_keywords = {}

        for keyword in keywords:
            cursor.execute(f"""
                SELECT COUNT(*) FROM civitai_prompts
                WHERE LOWER(full_prompt) LIKE '%{keyword}%'
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  {keyword}: {count}件")
                category_keywords[keyword] = count
                category_total += count

        print(f"  → {category_name} 小計: {category_total}件\n")
        category_details[category_name] = {
            'total': category_total,
            'keywords': category_keywords
        }
        total_sexual_matches += category_total

    print(f"性的表現 総マッチ数: {total_sexual_matches}件")

    # 5. 現在のNSFWカテゴリとの比較
    cursor.execute("SELECT COUNT(*) FROM prompt_categories WHERE category = 'NSFW'")
    current_nsfw = cursor.fetchone()[0]

    print(f"現在のNSFWカテゴリ: {current_nsfw}件")
    print(f"検出された性的表現: {total_sexual_matches}件")
    print(f"収集漏れ推定: {total_sexual_matches - current_nsfw}件")

    # 6. 高度な性的表現のサンプル取得
    cursor.execute("""
        SELECT full_prompt FROM civitai_prompts
        WHERE (LOWER(full_prompt) LIKE '%sex%' OR LOWER(full_prompt) LIKE '%fucking%'
               OR LOWER(full_prompt) LIKE '%penetration%' OR LOWER(full_prompt) LIKE '%orgasm%'
               OR LOWER(full_prompt) LIKE '%moaning%' OR LOWER(full_prompt) LIKE '%wet%')
        AND LENGTH(full_prompt) > 50
        LIMIT 10
    """)

    explicit_samples = cursor.fetchall()
    print(f"\n=== 性的表現含有プロンプトサンプル ===")
    for i, (prompt,) in enumerate(explicit_samples, 1):
        # 性的キーワードを強調表示
        display_prompt = prompt[:120] + "..." if len(prompt) > 120 else prompt
        print(f"{i}: {display_prompt}")

    # 7. 未分類の性的表現プロンプト数
    cursor.execute("""
        SELECT COUNT(*) FROM civitai_prompts cp
        WHERE (LOWER(cp.full_prompt) LIKE '%sex%' OR LOWER(cp.full_prompt) LIKE '%fucking%'
               OR LOWER(cp.full_prompt) LIKE '%penetration%' OR LOWER(cp.full_prompt) LIKE '%pussy%'
               OR LOWER(cp.full_prompt) LIKE '%cock%' OR LOWER(cp.full_prompt) LIKE '%orgasm%')
        AND cp.id NOT IN (SELECT prompt_id FROM prompt_categories WHERE category = 'NSFW')
    """)

    uncategorized_sexual = cursor.fetchone()[0]
    print(f"\n未分類の性的表現プロンプト: {uncategorized_sexual}件")

    # 8. 品質スコア別の性的表現分布
    cursor.execute("""
        SELECT
            CASE
                WHEN quality_score >= 20 THEN 'Very High (20+)'
                WHEN quality_score >= 15 THEN 'High (15-19)'
                WHEN quality_score >= 10 THEN 'Medium (10-14)'
                ELSE 'Low (0-9)'
            END as quality_range,
            COUNT(*) as count
        FROM civitai_prompts
        WHERE LOWER(full_prompt) LIKE '%sex%' OR LOWER(full_prompt) LIKE '%fucking%'
              OR LOWER(full_prompt) LIKE '%orgasm%' OR LOWER(full_prompt) LIKE '%pussy%'
        GROUP BY quality_range
        ORDER BY MIN(quality_score) DESC
    """)

    quality_distribution = cursor.fetchall()
    print(f"\n=== 性的表現プロンプトの品質分布 ===")
    for quality_range, count in quality_distribution:
        print(f"{quality_range}: {count}件")

    conn.close()

if __name__ == "__main__":
    analyze_sexual_expressions()
