#!/usr/bin/env python3
"""NSFWカテゴリ分析スクリプト"""
import sqlite3
import sys
sys.path.append('src')

def analyze_nsfw_data():
    # データベース接続
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 1. 総プロンプト数
    cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
    total_prompts = cursor.fetchone()[0]
    print(f'総プロンプト数: {total_prompts}')

    # 2. カテゴリ分布
    cursor.execute('SELECT category, COUNT(*) FROM prompt_categories GROUP BY category ORDER BY COUNT(*) DESC')
    categories = cursor.fetchall()
    print(f'\nカテゴリ分布:')
    for cat, count in categories:
        percentage = (count / total_prompts * 100) if total_prompts > 0 else 0
        print(f'  {cat}: {count}件 ({percentage:.1f}%)')

    # 3. NSFWキーワード詳細分析
    nsfw_keywords = ['nsfw', 'nude', 'naked', 'explicit', 'adult', 'erotic', 'topless', 'nipples', 'underwear', 'lingerie']
    print(f'\nNSFWキーワード個別検索:')
    total_nsfw_matches = 0
    for keyword in nsfw_keywords:
        cursor.execute(f"SELECT COUNT(*) FROM civitai_prompts WHERE LOWER(full_prompt) LIKE '%{keyword}%'")
        count = cursor.fetchone()[0]
        total_nsfw_matches += count
        print(f'  {keyword}: {count}件')

    print(f'NSFWキーワード総マッチ数: {total_nsfw_matches}件')

    # 4. 未分類プロンプト数
    cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE id NOT IN (SELECT prompt_id FROM prompt_categories)')
    uncategorized = cursor.fetchone()[0]
    print(f'\n未分類プロンプト: {uncategorized}件 ({(uncategorized/total_prompts*100):.1f}%)')

    # 5. NSFWカテゴリに分類されたプロンプトの確認
    cursor.execute("SELECT COUNT(*) FROM prompt_categories WHERE category = 'NSFW'")
    nsfw_categorized = cursor.fetchone()[0]
    print(f'NSFWカテゴリ分類済み: {nsfw_categorized}件')

    # 6. NSFWプロンプトの実際のサンプル（短縮版）
    cursor.execute("SELECT full_prompt FROM civitai_prompts WHERE LOWER(full_prompt) LIKE '%nsfw%' OR LOWER(full_prompt) LIKE '%nude%' LIMIT 5")
    nsfw_samples = cursor.fetchall()
    print(f'\nNSFWプロンプトサンプル:')
    for i, (prompt,) in enumerate(nsfw_samples, 1):
        print(f'  {i}: {prompt[:80]}...')

    # 7. 分類されていないNSFWプロンプトを検索
    cursor.execute("""
        SELECT COUNT(*) FROM civitai_prompts
        WHERE (LOWER(full_prompt) LIKE '%nsfw%' OR LOWER(full_prompt) LIKE '%nude%' OR LOWER(full_prompt) LIKE '%explicit%')
        AND id NOT IN (SELECT prompt_id FROM prompt_categories WHERE category = 'NSFW')
    """)
    uncategorized_nsfw = cursor.fetchone()[0]
    print(f'\n分類されていないNSFWプロンプト: {uncategorized_nsfw}件')

    conn.close()

if __name__ == "__main__":
    analyze_nsfw_data()
