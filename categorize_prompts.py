#!/usr/bin/env python3
"""
Civitai Prompt Categorizer - プロンプトカテゴリ分類ツール
収集済みプロンプトを10カテゴリに自動分類
"""

import sqlite3
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

# プロジェクトルート追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import DEFAULT_DB_PATH
from src.database import DatabaseManager

class PromptCategorizer:
    """プロンプトカテゴリ分類器"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.categories = {
            'nsfw': [
                'nude', 'naked', 'nsfw', 'sex', 'erotic', 'masturbation', 'pussy', 'penis',
                'vagina', 'breasts', 'nipples', 'cleavage', 'ass', 'butt', 'topless',
                'bottomless', 'lingerie', 'underwear', 'panties', 'bra', 'swimsuit',
                'sensual', 'seductive', 'provocative', 'intimate', 'passionate', 'aroused',
                'orgasm', 'climax', 'pleasure', 'lust', 'desire', 'tempting', 'alluring'
            ],
            'style': [
                'anime', 'manga', 'realistic', 'photorealistic', 'hyperrealistic', 'cartoon',
                'illustration', 'digital art', 'oil painting', 'watercolor', 'sketch',
                'cyberpunk', 'steampunk', 'gothic', 'vintage', 'retro', 'modern', 'classic',
                'impressionist', 'expressionist', 'surrealist', 'abstract', 'minimalist',
                'art nouveau', 'art deco', 'baroque', 'renaissance', 'romantic'
            ],
            'lighting': [
                'soft lighting', 'harsh lighting', 'dramatic lighting', 'natural lighting',
                'studio lighting', 'rim lighting', 'backlighting', 'side lighting',
                'golden hour', 'blue hour', 'sunset', 'sunrise', 'neon', 'candlelight',
                'moonlight', 'sunlight', 'overcast', 'chiaroscuro', 'volumetric lighting',
                'god rays', 'lens flare', 'bloom', 'glow', 'shadows', 'highlights'
            ],
            'composition': [
                'portrait', 'landscape', 'close-up', 'wide shot', 'medium shot', 'full body',
                'upper body', 'headshot', 'profile', 'three-quarter view', 'back view',
                'rule of thirds', 'centered', 'symmetrical', 'asymmetrical', 'diagonal',
                'leading lines', 'depth of field', 'bokeh', 'shallow focus', 'sharp focus',
                'framing', 'cropping', 'negative space', 'foreground', 'background'
            ],
            'mood': [
                'happy', 'sad', 'angry', 'peaceful', 'melancholic', 'joyful', 'serious',
                'mysterious', 'dreamy', 'ethereal', 'dark', 'bright', 'warm', 'cold',
                'cozy', 'elegant', 'graceful', 'powerful', 'delicate', 'fierce',
                'gentle', 'aggressive', 'calm', 'energetic', 'vibrant', 'muted'
            ],
            'technical': [
                'high resolution', '4k', '8k', 'hdr', 'ray tracing', 'subsurface scattering',
                'global illumination', 'ambient occlusion', 'motion blur', 'film grain',
                'chromatic aberration', 'vignette', 'noise', 'sharp', 'detailed',
                'intricate', 'complex', 'simple', 'clean', 'messy', 'rough', 'smooth'
            ],
            'pose': [
                'standing', 'sitting', 'lying', 'kneeling', 'crouching', 'leaning',
                'walking', 'running', 'jumping', 'dancing', 'stretching', 'relaxing',
                'thinking', 'looking', 'smiling', 'laughing', 'crying', 'shouting',
                'hands on hips', 'arms crossed', 'hand on chin', 'covering face'
            ],
            'angle': [
                'front view', 'side view', 'back view', 'three-quarter view', 'profile',
                'low angle', 'high angle', 'bird eye view', 'worm eye view', 'dutch angle',
                'overhead', 'underneath', 'diagonal', 'straight on', 'tilted'
            ],
            'camera_film': [
                'canon', 'nikon', 'sony', 'fujifilm', 'leica', 'hasselblad', 'pentax',
                '35mm', '50mm', '85mm', '24-70mm', 'wide angle', 'telephoto', 'macro',
                'fisheye', 'prime lens', 'zoom lens', 'aperture', 'shutter speed', 'iso',
                'film photography', 'digital photography', 'polaroid', 'instant camera'
            ],
            'basic': [
                'woman', 'man', 'girl', 'boy', 'person', 'people', 'human', 'face',
                'eyes', 'hair', 'skin', 'clothes', 'dress', 'shirt', 'pants', 'shoes',
                'jewelry', 'makeup', 'expression', 'emotion', 'beauty', 'handsome'
            ]
        }

    def categorize_prompt(self, prompt_text: str) -> List[Tuple[str, float, List[str]]]:
        """プロンプトをカテゴリ分類"""
        if not prompt_text:
            return []

        prompt_lower = prompt_text.lower()
        results = []

        for category, keywords in self.categories.items():
            matched_keywords = []
            total_matches = 0

            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    matched_keywords.append(keyword)
                    # キーワードの重要度に基づくスコア計算
                    if len(keyword) > 10:  # 長いキーワードは高スコア
                        total_matches += 2
                    elif len(keyword) > 5:
                        total_matches += 1.5
                    else:
                        total_matches += 1

            if matched_keywords:
                # 信頼度計算（マッチ数とキーワード品質を考慮）
                confidence = min(total_matches / len(keywords) * 5, 1.0)
                results.append((category, confidence, matched_keywords))

        # 信頼度順でソート
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def categorize_all_prompts(self) -> Dict:
        """全プロンプトを分類してデータベースに保存"""
        db = DatabaseManager(self.db_path)

        # prompt_categoriesテーブルを作成
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            confidence REAL NOT NULL,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
        )
        """)

        # 既存の分類結果をクリア
        cursor.execute("DELETE FROM prompt_categories")
        conn.commit()

        # 全プロンプトを取得
        cursor.execute("""
        SELECT id, full_prompt
        FROM civitai_prompts
        WHERE full_prompt IS NOT NULL AND full_prompt != ''
        """)

        prompts = cursor.fetchall()
        total_prompts = len(prompts)

        print(f"🔄 {total_prompts}件のプロンプトを分類中...")

        processed = 0
        stats = {
            'total_processed': 0,
            'total_categories': 0,
            'category_counts': {},
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0
        }

        for prompt_id, prompt_text in prompts:
            categories = self.categorize_prompt(prompt_text)

            for category, confidence, keywords in categories:
                # データベースに保存
                cursor.execute("""
                INSERT INTO prompt_categories (prompt_id, category, confidence, keywords)
                VALUES (?, ?, ?, ?)
                """, (prompt_id, category, confidence, ', '.join(keywords)))

                # 統計更新
                if category not in stats['category_counts']:
                    stats['category_counts'][category] = 0
                stats['category_counts'][category] += 1

                if confidence >= 0.7:
                    stats['high_confidence'] += 1
                elif confidence >= 0.4:
                    stats['medium_confidence'] += 1
                else:
                    stats['low_confidence'] += 1

                stats['total_categories'] += 1

            processed += 1
            if processed % 100 == 0:
                print(f"  📊 進行状況: {processed}/{total_prompts} ({processed/total_prompts*100:.1f}%)")

        conn.commit()
        conn.close()

        stats['total_processed'] = processed

        print("\n✅ 分類完了!")
        print(f"📊 処理済み: {stats['total_processed']:,}件")
        print(f"🏷️ 総分類数: {stats['total_categories']:,}件")
        print(f"🎯 高信頼度: {stats['high_confidence']:,}件 (≥70%)")
        print(f"📈 中信頼度: {stats['medium_confidence']:,}件 (40-69%)")
        print(f"📉 低信頼度: {stats['low_confidence']:,}件 (<40%)")

        print(f"\n📋 カテゴリ別件数:")
        for category, count in sorted(stats['category_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count:,}件")

        return stats

def main():
    """メイン実行"""
    print("🎯 Civitai Prompt Categorizer")
    print("=" * 50)

    categorizer = PromptCategorizer()

    # データベース存在確認
    if not Path(categorizer.db_path).exists():
        print(f"❌ データベースが見つかりません: {categorizer.db_path}")
        print("まず収集を実行してください: python main.py --collect-only")
        return

    # 分類実行
    stats = categorizer.categorize_all_prompts()

    print(f"\n💡 次のステップ:")
    print(f"1. streamlit run ui/streamlit_app_10category.py  # 10カテゴリ分析UI")
    print(f"2. python statistics_dashboard.py              # 統計ダッシュボード")
    print(f"3. python prompt_analysis.py                   # プロンプト分析")

if __name__ == "__main__":
    main()
