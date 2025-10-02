#!/usr/bin/env python3
"""分類されていないNSFWプロンプトの詳細分析"""
import sqlite3
import sys
sys.path.append('src')

def analyze_uncategorized_nsfw():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 分類されていないNSFWプロンプトを詳細取得
    cursor.execute("""
        SELECT id, full_prompt FROM civitai_prompts
        WHERE (LOWER(full_prompt) LIKE '%nsfw%' OR LOWER(full_prompt) LIKE '%nude%'
               OR LOWER(full_prompt) LIKE '%explicit%' OR LOWER(full_prompt) LIKE '%adult%'
               OR LOWER(full_prompt) LIKE '%erotic%' OR LOWER(full_prompt) LIKE '%nipples%'
               OR LOWER(full_prompt) LIKE '%lingerie%' OR LOWER(full_prompt) LIKE '%topless%')
        AND id NOT IN (SELECT prompt_id FROM prompt_categories WHERE category = 'NSFW')
        LIMIT 20
    """)

    uncategorized_nsfw = cursor.fetchall()
    print(f"分類されていないNSFWプロンプト（詳細）:")
    print(f"総数: {len(uncategorized_nsfw)}件（表示: 先頭20件）")
    print("-" * 80)

    for prompt_id, full_prompt in uncategorized_nsfw:
        print(f"ID: {prompt_id}")
        print(f"プロンプト: {full_prompt}")
        print("-" * 40)

    # カテゴリ別の分類確認
    print("\n\n=== カテゴリ別分類状況 ===")
    for prompt_id, _ in uncategorized_nsfw[:5]:  # 最初の5件をチェック
        cursor.execute("SELECT category, confidence FROM prompt_categories WHERE prompt_id = ?", (prompt_id,))
        categories = cursor.fetchall()
        print(f"ID {prompt_id} の分類状況:")
        if categories:
            for cat, conf in categories:
                print(f"  - {cat}: {conf:.3f}")
        else:
            print(f"  - 未分類")
        print()

    # NSFWキーワードを含む全プロンプトの分類状況
    cursor.execute("""
        SELECT
            CASE WHEN pc.category IS NOT NULL THEN pc.category ELSE 'uncategorized' END as category,
            COUNT(*) as count
        FROM civitai_prompts cp
        LEFT JOIN prompt_categories pc ON cp.id = pc.prompt_id
        WHERE LOWER(cp.full_prompt) LIKE '%nsfw%' OR LOWER(cp.full_prompt) LIKE '%nude%'
              OR LOWER(cp.full_prompt) LIKE '%explicit%' OR LOWER(cp.full_prompt) LIKE '%adult%'
              OR LOWER(cp.full_prompt) LIKE '%erotic%' OR LOWER(cp.full_prompt) LIKE '%nipples%'
        GROUP BY CASE WHEN pc.category IS NOT NULL THEN pc.category ELSE 'uncategorized' END
        ORDER BY count DESC
    """)

    nsfw_distribution = cursor.fetchall()
    print("\n=== NSFWキーワード含有プロンプトのカテゴリ分布 ===")
    for category, count in nsfw_distribution:
        print(f"{category}: {count}件")

    conn.close()

if __name__ == "__main__":
    analyze_uncategorized_nsfw()
