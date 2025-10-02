#!/usr/bin/env python3
"""
プロンプト分析・分解・カテゴライズ検証ツール

収集したプロンプトデータを分析して、効果的な分解・分類戦略を検討する
"""

import sqlite3
import re
import json
from collections import Counter, defaultdict
from typing import List, Dict, Set, Tuple
import pandas as pd

class PromptAnalyzer:
    def __init__(self, db_path: str = "data/civitai_dataset.db"):
        self.db_path = db_path
        self.conn = None

    def connect_db(self):
        self.conn = sqlite3.connect(self.db_path)

    def close_db(self):
        if self.conn:
            self.conn.close()

    def analyze_prompt_structure(self) -> Dict:
        """プロンプト構造の基本分析"""
        self.connect_db()
        cursor = self.conn.cursor()

        # 基本統計
        cursor.execute("""
            SELECT
                COUNT(*) as total_prompts,
                AVG(prompt_length) as avg_length,
                MIN(prompt_length) as min_length,
                MAX(prompt_length) as max_length,
                AVG(tag_count) as avg_tag_count,
                MIN(tag_count) as min_tag_count,
                MAX(tag_count) as max_tag_count
            FROM civitai_prompts
        """)

        stats = cursor.fetchone()

        # サンプルプロンプト取得
        cursor.execute("SELECT full_prompt, negative_prompt FROM civitai_prompts LIMIT 10")
        samples = cursor.fetchall()

        self.close_db()

        return {
            'total_prompts': stats[0],
            'avg_length': stats[1],
            'min_length': stats[2],
            'max_length': stats[3],
            'avg_tag_count': stats[4],
            'min_tag_count': stats[5],
            'max_tag_count': stats[6],
            'samples': samples
        }

    def extract_common_patterns(self) -> Dict:
        """プロンプトの共通パターン抽出"""
        self.connect_db()
        cursor = self.conn.cursor()

        cursor.execute("SELECT full_prompt FROM civitai_prompts WHERE full_prompt IS NOT NULL")
        prompts = [row[0] for row in cursor.fetchall()]

        # パターン分析
        patterns = {
            'quality_terms': Counter(),
            'style_terms': Counter(),
            'character_terms': Counter(),
            'technical_terms': Counter(),
            'comma_separated': 0,
            'parentheses_usage': 0,
            'weight_usage': 0,
            'embedding_usage': 0
        }

        # 品質関連キーワード
        quality_keywords = ['masterpiece', 'best quality', 'high quality', 'extremely detailed',
                           'ultra detailed', 'detailed', 'realistic', 'photorealistic',
                           'high resolution', '8k', '4k', 'ultra high res']

        # スタイル関連キーワード
        style_keywords = ['anime', 'realistic', 'cartoon', 'oil painting', 'watercolor',
                         'digital art', 'concept art', 'portrait', 'landscape', 'abstract']

        # キャラクター関連キーワード
        character_keywords = ['girl', 'boy', 'woman', 'man', 'female', 'male', 'person',
                            'beautiful', 'cute', 'handsome', 'young', 'old']

        # 技術的キーワード
        technical_keywords = ['depth of field', 'bokeh', 'lighting', 'shadows', 'composition',
                            'camera angle', 'perspective', 'focus', 'blur', 'sharp']

        for prompt in prompts:
            if not prompt:
                continue

            prompt_lower = prompt.lower()

            # カンマ区切りチェック
            if ',' in prompt:
                patterns['comma_separated'] += 1

            # 括弧使用チェック
            if '(' in prompt or '[' in prompt:
                patterns['parentheses_usage'] += 1

            # 重み付けチェック (:数字)
            if re.search(r':\s*\d+\.?\d*', prompt):
                patterns['weight_usage'] += 1

            # エンベッディング使用チェック
            if '<' in prompt and '>' in prompt:
                patterns['embedding_usage'] += 1

            # キーワード分析
            for keyword in quality_keywords:
                if keyword in prompt_lower:
                    patterns['quality_terms'][keyword] += 1

            for keyword in style_keywords:
                if keyword in prompt_lower:
                    patterns['style_terms'][keyword] += 1

            for keyword in character_keywords:
                if keyword in prompt_lower:
                    patterns['character_terms'][keyword] += 1

            for keyword in technical_keywords:
                if keyword in prompt_lower:
                    patterns['technical_terms'][keyword] += 1

        self.close_db()
        return patterns

    def categorize_prompts(self) -> Dict:
        """プロンプトの自動カテゴライズ試行"""
        self.connect_db()
        cursor = self.conn.cursor()

        cursor.execute("SELECT id, full_prompt, quality_score FROM civitai_prompts WHERE full_prompt IS NOT NULL")
        prompts = cursor.fetchall()

        categories = {
            'realistic_portrait': [],
            'anime_character': [],
            'landscape_scene': [],
            'abstract_art': [],
            'technical_photo': [],
            'fantasy_creature': [],
            'uncategorized': []
        }

        # カテゴライズルール
        for pid, prompt, quality in prompts:
            if not prompt:
                continue

            prompt_lower = prompt.lower()

            # リアルポートレート
            if any(word in prompt_lower for word in ['realistic', 'photorealistic', 'portrait', 'woman', 'man', 'girl', 'boy']):
                if any(word in prompt_lower for word in ['realistic', 'photorealistic', 'photo']):
                    categories['realistic_portrait'].append((pid, prompt[:100], quality))
                    continue

            # アニメキャラクター
            if any(word in prompt_lower for word in ['anime', 'manga', 'cartoon', '1girl', '1boy', 'cute']):
                categories['anime_character'].append((pid, prompt[:100], quality))
                continue

            # 風景シーン
            if any(word in prompt_lower for word in ['landscape', 'scenery', 'background', 'environment', 'nature']):
                categories['landscape_scene'].append((pid, prompt[:100], quality))
                continue

            # 抽象アート
            if any(word in prompt_lower for word in ['abstract', 'artistic', 'concept art', 'surreal']):
                categories['abstract_art'].append((pid, prompt[:100], quality))
                continue

            # テクニカル写真
            if any(word in prompt_lower for word in ['macro', 'close-up', 'depth of field', 'bokeh', 'professional']):
                categories['technical_photo'].append((pid, prompt[:100], quality))
                continue

            # ファンタジー
            if any(word in prompt_lower for word in ['fantasy', 'dragon', 'magic', 'creature', 'monster']):
                categories['fantasy_creature'].append((pid, prompt[:100], quality))
                continue

            # 未分類
            categories['uncategorized'].append((pid, prompt[:100], quality))

        self.close_db()
        return categories

    def suggest_tag_taxonomy(self) -> Dict:
        """タグ分類体系の提案"""
        patterns = self.extract_common_patterns()

        taxonomy = {
            'quality_modifiers': {
                'description': '品質・解像度関連のタグ',
                'examples': list(patterns['quality_terms'].most_common(10)),
                'usage': 'プロンプトの品質向上に使用'
            },
            'style_descriptors': {
                'description': 'アートスタイル・表現方法',
                'examples': list(patterns['style_terms'].most_common(10)),
                'usage': '出力スタイルの指定'
            },
            'subject_elements': {
                'description': '主題・キャラクター要素',
                'examples': list(patterns['character_terms'].most_common(10)),
                'usage': '描画対象の指定'
            },
            'technical_parameters': {
                'description': '技術的パラメータ',
                'examples': list(patterns['technical_terms'].most_common(10)),
                'usage': 'カメラ設定や技術的効果'
            },
            'syntax_patterns': {
                'comma_separation': patterns['comma_separated'],
                'weight_notation': patterns['weight_usage'],
                'embedding_usage': patterns['embedding_usage'],
                'parentheses_usage': patterns['parentheses_usage']
            }
        }

        return taxonomy

def main():
    """メイン分析実行"""
    analyzer = PromptAnalyzer()

    print("🔍 プロンプトデータ分析開始...")
    print("=" * 60)

    # 1. 基本構造分析
    print("\n📊 1. 基本構造分析")
    stats = analyzer.analyze_prompt_structure()
    print(f"総プロンプト数: {stats['total_prompts']}")
    print(f"平均文字数: {stats['avg_length']:.1f}")
    print(f"文字数範囲: {stats['min_length']} - {stats['max_length']}")
    print(f"平均タグ数: {stats['avg_tag_count']:.1f}")
    print(f"タグ数範囲: {stats['min_tag_count']} - {stats['max_tag_count']}")

    # 2. パターン分析
    print("\n🎯 2. 共通パターン分析")
    patterns = analyzer.extract_common_patterns()

    print(f"カンマ区切り使用: {patterns['comma_separated']}/{stats['total_prompts']} ({patterns['comma_separated']/stats['total_prompts']*100:.1f}%)")
    print(f"重み付け使用: {patterns['weight_usage']}/{stats['total_prompts']} ({patterns['weight_usage']/stats['total_prompts']*100:.1f}%)")
    print(f"括弧使用: {patterns['parentheses_usage']}/{stats['total_prompts']} ({patterns['parentheses_usage']/stats['total_prompts']*100:.1f}%)")
    print(f"エンベッディング使用: {patterns['embedding_usage']}/{stats['total_prompts']} ({patterns['embedding_usage']/stats['total_prompts']*100:.1f}%)")

    print("\n🏆 品質関連キーワード TOP5:")
    for keyword, count in patterns['quality_terms'].most_common(5):
        print(f"  {keyword}: {count}回")

    print("\n🎨 スタイル関連キーワード TOP5:")
    for keyword, count in patterns['style_terms'].most_common(5):
        print(f"  {keyword}: {count}回")

    # 3. カテゴライズ試行
    print("\n📂 3. 自動カテゴライズ結果")
    categories = analyzer.categorize_prompts()

    for category, prompts in categories.items():
        if prompts:
            print(f"\n{category.replace('_', ' ').title()}: {len(prompts)}件")
            # 上位3件を表示
            for i, (pid, prompt, quality) in enumerate(prompts[:3]):
                print(f"  [{pid}] (Q:{quality}) {prompt}...")

    # 4. タグ分類体系提案
    print("\n🏗️ 4. 推奨タグ分類体系")
    taxonomy = analyzer.suggest_tag_taxonomy()

    for category, info in taxonomy.items():
        if category != 'syntax_patterns':
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"  説明: {info['description']}")
            print(f"  用途: {info['usage']}")
            print(f"  主要例: {[item[0] for item in info['examples'][:5]]}")

    print("\n📝 構文パターン使用状況:")
    syntax = taxonomy['syntax_patterns']
    for pattern, count in syntax.items():
        if pattern != 'syntax_patterns':
            print(f"  {pattern.replace('_', ' ')}: {count}")

    print("\n✅ 分析完了！")
    print("\n💡 推奨事項:")
    print("1. カンマ区切り形式が主流 → パーサーはカンマ分割ベース")
    print("2. 重み付け記法を考慮 → :数値 パターンの処理")
    print("3. 品質タグは共通 → 標準化して再利用可能")
    print("4. スタイル分類は明確 → カテゴリー別学習データ作成")
    print("5. 技術的パラメータは分離 → ComfyUI設定との連携")

if __name__ == "__main__":
    main()
