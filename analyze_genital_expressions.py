#!/usr/bin/env python3
"""性器表現の詳細分析スクリプト"""
import sqlite3
import sys
sys.path.append('src')

def analyze_genital_expressions():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    print("=== 性器表現の詳細分析 ===\n")

    # 1. 女性器表現
    female_genitals = {
        "直接表現": ["pussy", "vagina", "cunt", "vulva"],
        "部位詳細": ["labia", "clitoris", "clit", "g-spot", "cervix"],
        "俗語・スラング": ["snatch", "twat", "beaver", "muff", "cooch"],
        "婉曲表現": ["slit", "opening", "entrance", "core", "center"],
        "状態表現": ["wet pussy", "tight pussy", "dripping", "soaked", "gaping"]
    }

    # 2. 男性器表現
    male_genitals = {
        "直接表現": ["penis", "cock", "dick", "phallus"],
        "部位詳細": ["glans", "shaft", "foreskin", "head", "tip"],
        "俗語・スラング": ["rod", "member", "manhood", "tool", "stick"],
        "状態表現": ["hard cock", "erect penis", "throbbing", "swollen", "rigid"]
    }

    # 3. 共通性器表現
    general_genitals = {
        "生殖器総称": ["genitals", "private parts", "intimate parts", "naughty bits"],
        "性的器官": ["sex organs", "reproductive organs", "erogenous zones"],
        "医学用語": ["reproductive anatomy", "sexual anatomy", "genital area"]
    }

    all_categories = {
        "🌸 女性器表現": female_genitals,
        "🍆 男性器表現": male_genitals,
        "⚥ 共通性器表現": general_genitals
    }

    total_genital_matches = 0
    detailed_results = {}

    for main_category, subcategories in all_categories.items():
        print(f"{main_category}")
        print("=" * 50)

        category_total = 0
        category_details = {}

        for subcat_name, keywords in subcategories.items():
            print(f"\n### {subcat_name} ###")
            subcat_total = 0
            subcat_keywords = {}

            for keyword in keywords:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM civitai_prompts
                    WHERE LOWER(full_prompt) LIKE '%{keyword}%'
                """)
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f"  {keyword}: {count}件")
                    subcat_keywords[keyword] = count
                    subcat_total += count
                    category_total += count
                    total_genital_matches += count
                elif keyword in ["pussy", "vagina", "penis", "cock"]:
                    # 主要キーワードは0件でも表示
                    print(f"  {keyword}: {count}件")

            if subcat_keywords:
                category_details[subcat_name] = {
                    'total': subcat_total,
                    'keywords': subcat_keywords
                }

        print(f"\n{main_category} 小計: {category_total}件")
        print("\n" + "="*60 + "\n")

        detailed_results[main_category] = {
            'total': category_total,
            'details': category_details
        }

    print(f"性器表現 総マッチ数: {total_genital_matches}件\n")

    # 4. 具体的な性器表現プロンプトのサンプル取得
    print("=== 性器表現含有プロンプト サンプル ===")

    major_genital_terms = ["pussy", "vagina", "cock", "penis", "clit", "labia"]
    for term in major_genital_terms:
        cursor.execute(f"""
            SELECT full_prompt FROM civitai_prompts
            WHERE LOWER(full_prompt) LIKE '%{term}%'
            AND LENGTH(full_prompt) > 30
            LIMIT 3
        """)

        samples = cursor.fetchall()
        if samples:
            print(f"\n🔍 '{term}' を含むプロンプト:")
            for i, (prompt,) in enumerate(samples, 1):
                display_prompt = prompt[:150] + "..." if len(prompt) > 150 else prompt
                print(f"  {i}: {display_prompt}")
        else:
            print(f"\n🔍 '{term}' を含むプロンプト: 該当なし")

    # 5. 性器表現の品質分析
    cursor.execute(f"""
        SELECT
            CASE
                WHEN quality_score >= 20 THEN 'Very High (20+)'
                WHEN quality_score >= 15 THEN 'High (15-19)'
                WHEN quality_score >= 10 THEN 'Medium (10-14)'
                ELSE 'Low (0-9)'
            END as quality_range,
            COUNT(*) as count
        FROM civitai_prompts
        WHERE LOWER(full_prompt) LIKE '%pussy%' OR LOWER(full_prompt) LIKE '%vagina%'
              OR LOWER(full_prompt) LIKE '%cock%' OR LOWER(full_prompt) LIKE '%penis%'
              OR LOWER(full_prompt) LIKE '%clit%' OR LOWER(full_prompt) LIKE '%labia%'
        GROUP BY quality_range
        ORDER BY MIN(quality_score) DESC
    """)

    quality_distribution = cursor.fetchall()
    print(f"\n=== 性器表現プロンプトの品質分布 ===")
    for quality_range, count in quality_distribution:
        print(f"{quality_range}: {count}件")

    # 6. 他のキーワードとの共起分析
    print(f"\n=== 性器表現との共起キーワード ===")

    cursor.execute("""
        SELECT full_prompt FROM civitai_prompts
        WHERE (LOWER(full_prompt) LIKE '%pussy%' OR LOWER(full_prompt) LIKE '%cock%')
        AND LENGTH(full_prompt) > 50
        LIMIT 10
    """)

    cooccurrence_samples = cursor.fetchall()
    common_cooccurrences = {}

    for (prompt,) in cooccurrence_samples:
        words = prompt.lower().split()
        for word in words:
            if word in ["wet", "tight", "hard", "soft", "pink", "spread", "open", "close"]:
                common_cooccurrences[word] = common_cooccurrences.get(word, 0) + 1

    if common_cooccurrences:
        print("よく一緒に使われる形容詞:")
        for word, count in sorted(common_cooccurrences.items(), key=lambda x: x[1], reverse=True):
            print(f"  {word}: {count}回")

    # 7. 性器表現が少ない理由の推測
    print(f"\n=== 性器表現が少ない理由の分析 ===")

    # CivitAIのコンテンツポリシーの影響を調査
    cursor.execute("""
        SELECT COUNT(*) FROM civitai_prompts
        WHERE LOWER(full_prompt) LIKE '%nsfw%' OR LOWER(full_prompt) LIKE '%explicit%'
    """)
    explicit_marked = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM civitai_prompts")
    total_prompts = cursor.fetchone()[0]

    explicit_ratio = (explicit_marked / total_prompts) * 100 if total_prompts > 0 else 0

    print(f"総プロンプト数: {total_prompts}件")
    print(f"明示的マーク付き: {explicit_marked}件 ({explicit_ratio:.1f}%)")
    print(f"推測される理由:")
    print(f"  1. CivitAIのコンテンツポリシーにより直接的性器表現が制限されている可能性")
    print(f"  2. ユーザーが婉曲表現や暗示的表現を好む傾向")
    print(f"  3. プラットフォームのモデレーションにより直接的表現が除外されている可能性")
    print(f"  4. アート・イラスト系のプロンプトが多く、写実的な解剖学表現が少ない")

    conn.close()

if __name__ == "__main__":
    analyze_genital_expressions()
