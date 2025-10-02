#!/usr/bin/env python3
"""
モデル974693/version 2091367の既存データのNSFW分析
既存の39件のプロンプトの性的表現レベルを詳細分析
"""

import sqlite3
import re
from typing import Dict, List, Tuple
from collections import defaultdict

class ModelNSFWAnalyzer:
    def __init__(self, db_path: str = 'data/civitai_dataset.db'):
        self.db_path = db_path

        # 性的表現キーワードの階層分類
        self.sexual_keywords = {
            'explicit_genital': ['pussy', 'vagina', 'cock', 'penis', 'dick', 'clit', 'labia'],
            'explicit_acts': ['sex', 'fucking', 'blowjob', 'handjob', 'footjob', 'titjob',
                            'masturbation', 'masturbate', 'orgasm', 'cum', 'cumshot',
                            'creampie', 'gangbang', 'threesome', 'anal', 'oral'],
            'explicit_body': ['breasts', 'tits', 'boobs', 'nipples', 'ass', 'butt', 'thighs',
                            'cleavage', 'nude', 'naked', 'topless', 'bottomless'],
            'suggestive': ['sexy', 'seductive', 'erotic', 'aroused', 'horny', 'kinky',
                         'submissive', 'dominant', 'fetish', 'bdsm', 'bondage'],
            'poses': ['spread legs', 'legs apart', 'bent over', 'on all fours',
                     'missionary', 'doggy style', 'cowgirl', 'reverse cowgirl'],
            'clothing': ['lingerie', 'panties', 'bra', 'stockings', 'fishnet',
                       'corset', 'thong', 'bikini', 'micro bikini']
        }

    def analyze_existing_data(self):
        """既存のモデル974693データを分析"""
        print("=== モデル 974693/2091367 既存データNSFW分析 ===\n")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # URN形式でデータを取得
        urn_pattern = "urn:air:sdxl:checkpoint:civitai:974693@2091367"

        # まずプロンプトデータとカテゴリーをJOINで取得
        cursor.execute("""
            SELECT p.id, p.full_prompt, p.model_name, p.model_id, pc.category
            FROM civitai_prompts p
            LEFT JOIN prompt_categories pc ON p.id = pc.prompt_id
            WHERE p.model_name = ? OR p.model_id = '2091367'
        """, (urn_pattern,))

        results = cursor.fetchall()
        print(f"📊 収集済みデータ（JOINクエリ）: {len(results)}件\n")

        if not results:
            print("❌ データが見つかりませんでした")
            return

        # データを整理（プロンプトIDごとにグループ化）
        prompts_data = defaultdict(lambda: {'prompt': '', 'categories': []})
        for prompt_id, full_prompt, model_name, model_id, category in results:
            prompts_data[prompt_id]['prompt'] = full_prompt or ''
            prompts_data[prompt_id]['model_name'] = model_name or ''
            prompts_data[prompt_id]['model_id'] = model_id or ''
            if category:
                prompts_data[prompt_id]['categories'].append(category)

        print(f"📊 ユニークなプロンプト数: {len(prompts_data)}件\n")

        # NSFW分析
        category_stats = defaultdict(int)
        sexual_analysis = defaultdict(list)

        for prompt_id, data in prompts_data.items():
            prompt_text = data['prompt']
            categories = data['categories']

            for cat in categories:
                category_stats[cat] += 1

            # 性的表現の詳細分析
            if prompt_text:
                prompt_lower = prompt_text.lower()
                for category, keywords in self.sexual_keywords.items():
                    for keyword in keywords:
                        if keyword in prompt_lower:
                            sexual_analysis[category].append({
                                'id': prompt_id,
                                'keyword': keyword,
                                'text': prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text,
                                'categories': categories
                            })

        # 結果表示
        print("📈 カテゴリー分布:")
        total_prompts = len(prompts_data)
        for category, count in sorted(category_stats.items()):
            percentage = (count / total_prompts) * 100
            print(f"  {category}: {count}件 ({percentage:.1f}%)")

        # NSFWカテゴリーの統計
        nsfw_categories = [cat for cat in category_stats.keys() if 'nsfw' in cat.lower() or 'explicit' in cat.lower()]
        total_nsfw = sum(category_stats[cat] for cat in nsfw_categories)
        print(f"\n📊 NSFW関連カテゴリー合計: {total_nsfw}件 ({(total_nsfw/total_prompts*100):.1f}%)")

        print(f"\n🔍 性的表現の詳細分析:")
        total_sexual_matches = 0
        for category, matches in sexual_analysis.items():
            if matches:
                unique_keywords = set(match['keyword'] for match in matches)
                total_sexual_matches += len(matches)
                print(f"\n  【{category}】: {len(matches)}件のマッチ, {len(unique_keywords)}種類のキーワード")

                # 上位キーワードを表示
                keyword_counts = defaultdict(int)
                for match in matches:
                    keyword_counts[match['keyword']] += 1

                for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    - '{keyword}': {count}件")

        print(f"\n📊 全体統計:")
        print(f"  総プロンプト数: {total_prompts}件")
        print(f"  性的表現マッチ数: {total_sexual_matches}件")
        print(f"  性的表現率: {(total_sexual_matches/total_prompts*100):.1f}%")

        # カテゴリー別性的表現分析
        print(f"\n🎯 カテゴリー別性的表現詳細:")
        for prompt_id, data in prompts_data.items():
            prompt_text = data['prompt']
            categories = data['categories']

            if not prompt_text:
                continue

            prompt_lower = prompt_text.lower()
            sexual_count = 0
            found_keywords = []

            for category, keywords in self.sexual_keywords.items():
                for keyword in keywords:
                    if keyword in prompt_lower:
                        sexual_count += 1
                        found_keywords.append(keyword)

            if sexual_count > 0:
                print(f"  ID {prompt_id} (カテゴリー: {', '.join(categories) if categories else 'なし'}): {sexual_count}個のキーワード")
                print(f"    キーワード: {', '.join(found_keywords[:5])}")
                print(f"    プロンプト: {prompt_text[:80]}...")
                print()

        conn.close()

    def suggest_improvements(self):
        """改善提案を生成"""
        print("\n💡 改善提案:")
        print("1. 現在のNSFWレベル分類が適切かチェック")
        print("2. nsfw='X'パラメータでの再収集でより明示的なコンテンツ取得")
        print("3. 性的表現の不足部分を特定し、ターゲット収集実行")
        print("4. WD14補完用の表現パターン拡張")

def main():
    analyzer = ModelNSFWAnalyzer()
    analyzer.analyze_existing_data()
    analyzer.suggest_improvements()

if __name__ == "__main__":
    main()
