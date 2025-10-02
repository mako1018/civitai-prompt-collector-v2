#!/usr/bin/env python3
"""
モデル974693の NSFW="X" パラメータでの新規収集テスト
既存データと比較してどの程度性的表現が向上するかをテスト
"""

import requests
import json
import sqlite3
import time
from typing import List, Dict, Any
from collections import defaultdict

class Model974693NSFWTest:
    def __init__(self):
        self.base_url = "https://civitai.com/api/v1/images"
        self.model_id = 974693
        self.version_id = 2091367
        self.db_path = 'data/civitai_dataset.db'

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
        }

    def test_nsfw_collection(self, limit: int = 50):
        """nsfw="X"パラメータでの収集テスト"""
        print(f"=== モデル 974693/2091367 NSFW=\"X\" 収集テスト ===\n")

        # 既存データの統計
        self.analyze_existing_data()

        print(f"\n🔍 nsfw=\"X\" パラメータでの新規収集テスト...")

        # NSFWパラメータ付きで収集
        params = {
            'modelId': self.model_id,
            'modelVersionId': self.version_id,
            'nsfw': 'X',  # 明示的コンテンツを含む
            'limit': limit,
            'sort': 'Most Reactions'
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get('items', [])
            print(f"📊 取得したアイテム数: {len(items)}件")

            if not items:
                print("❌ データが取得できませんでした")
                return

            # 性的表現の分析
            sexual_analysis = defaultdict(list)
            explicit_prompts = []

            for item in items:
                meta = item.get('meta', {})
                prompt = meta.get('prompt', '')

                if not prompt:
                    continue

                prompt_lower = prompt.lower()
                has_sexual = False
                item_keywords = []

                for category, keywords in self.sexual_keywords.items():
                    for keyword in keywords:
                        if keyword in prompt_lower:
                            sexual_analysis[category].append({
                                'keyword': keyword,
                                'prompt': prompt[:150] + "..." if len(prompt) > 150 else prompt,
                                'item_id': item.get('id'),
                                'stats': item.get('stats', {})
                            })
                            item_keywords.append(keyword)
                            has_sexual = True

                if has_sexual:
                    explicit_prompts.append({
                        'prompt': prompt,
                        'keywords': item_keywords,
                        'stats': item.get('stats', {}),
                        'nsfw': item.get('nsfw', False)
                    })

            # 結果レポート
            print(f"\n📈 NSFW収集結果:")
            print(f"  総取得アイテム: {len(items)}件")
            print(f"  性的表現含有: {len(explicit_prompts)}件 ({len(explicit_prompts)/len(items)*100:.1f}%)")

            print(f"\n🔥 性的表現カテゴリー別統計:")
            total_matches = 0
            for category, matches in sexual_analysis.items():
                if matches:
                    unique_keywords = set(match['keyword'] for match in matches)
                    total_matches += len(matches)
                    print(f"\n  【{category}】: {len(matches)}件のマッチ, {len(unique_keywords)}種類")

                    # トップキーワード
                    keyword_counts = defaultdict(int)
                    for match in matches:
                        keyword_counts[match['keyword']] += 1

                    for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"    - '{keyword}': {count}件")

            # 最も露骨なプロンプトを表示
            print(f"\n🔞 最も露骨なプロンプト例 (上位10件):")
            explicit_prompts.sort(key=lambda x: len(x['keywords']), reverse=True)

            for i, prompt_data in enumerate(explicit_prompts[:10]):
                print(f"\n  {i+1}. キーワード数: {len(prompt_data['keywords'])}個")
                print(f"     キーワード: {', '.join(prompt_data['keywords'][:8])}")
                print(f"     NSFW フラグ: {prompt_data['nsfw']}")
                print(f"     プロンプト: {prompt_data['prompt'][:120]}...")

            # 改善ポテンシャルの分析
            self.analyze_improvement_potential(explicit_prompts, total_matches)

        except requests.exceptions.RequestException as e:
            print(f"❌ API エラー: {e}")
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")

    def analyze_existing_data(self):
        """既存データの統計"""
        print("📋 既存データ統計:")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        #既存データの性的表現統計
        cursor.execute("""
            SELECT COUNT(*) FROM civitai_prompts
            WHERE model_name = 'urn:air:sdxl:checkpoint:civitai:974693@2091367' OR model_id = '2091367'
        """)
        existing_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM civitai_prompts p
            JOIN prompt_categories pc ON p.id = pc.prompt_id
            WHERE (p.model_name = 'urn:air:sdxl:checkpoint:civitai:974693@2091367' OR p.model_id = '2091367')
            AND pc.category = 'NSFW'
        """)
        nsfw_count = cursor.fetchone()[0]

        print(f"  既存プロンプト総数: {existing_count}件")
        print(f"  既存NSFW分類: {nsfw_count}件 ({nsfw_count/existing_count*100:.1f}%)")

        conn.close()

    def analyze_improvement_potential(self, explicit_prompts: List[Dict], total_matches: int):
        """改善ポテンシャルの分析"""
        print(f"\n💡 改善ポテンシャル分析:")
        print(f"  NSFW収集での性的表現含有率: {len(explicit_prompts)/50*100:.1f}% (テスト50件中)")
        print(f"  既存データでの性的表現含有率: 約15% (39件中推定)")

        if len(explicit_prompts) > 7:  # 50件中15%以上
            print(f"  🎯 改善ポテンシャル: 高")
            print(f"     - NSFW収集により明らかに性的表現の多いプロンプトが取得可能")
            print(f"     - WD14の表現力向上に大幅貢献する見込み")
        else:
            print(f"  ⚠️  改善ポテンシャル: 限定的")
            print(f"     - このモデルでは性的表現の大幅な向上は期待できない")

        # 最も価値の高いキーワードを特定
        all_keywords = []
        for prompt_data in explicit_prompts:
            all_keywords.extend(prompt_data['keywords'])

        if all_keywords:
            keyword_freq = defaultdict(int)
            for keyword in all_keywords:
                keyword_freq[keyword] += 1

            print(f"\n🏆 最も価値の高い新規キーワード (上位10個):")
            for keyword, freq in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - '{keyword}': {freq}回出現")

def main():
    tester = Model974693NSFWTest()
    tester.test_nsfw_collection(limit=50)

if __name__ == "__main__":
    main()
