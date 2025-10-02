#!/usr/bin/env python3
"""性的表現専用の強化分類・収集システム"""
import sqlite3
import sys
from typing import List, Dict, Tuple
from dataclasses import dataclass

sys.path.append('src')

@dataclass
class SexualExpressionResult:
    category: str
    intensity: str  # mild, moderate, explicit
    confidence: float
    matched_keywords: List[str]
    context_type: str  # anatomical, act, descriptive, situational

class SexualExpressionClassifier:
    """性的表現専用の高精度分類器"""

    def __init__(self):
        self.sexual_keywords = self._load_sexual_expression_dictionary()

    def _load_sexual_expression_dictionary(self) -> Dict[str, Dict]:
        """性的表現の包括的辞書"""
        return {
            "explicit_acts": {
                "keywords": [
                    "sex", "fucking", "penetration", "insertion", "thrusting",
                    "orgasm", "climax", "cumming", "creampie", "cumshot",
                    "blowjob", "fellatio", "oral sex", "cunnilingus",
                    "anal sex", "vaginal sex", "masturbation", "fingering"
                ],
                "intensity": "explicit",
                "weight": 5.0
            },
            "sexual_anatomy": {
                "keywords": [
                    "pussy", "vagina", "cunt", "slit", "labia", "clitoris", "clit",
                    "penis", "cock", "dick", "shaft", "glans", "balls", "testicles",
                    "nipples", "areola", "breasts", "boobs", "tits", "cleavage",
                    "ass", "buttocks", "anus", "asshole", "butt", "rear end"
                ],
                "intensity": "moderate",
                "weight": 3.0
            },
            "sexual_descriptors": {
                "keywords": [
                    "wet", "moist", "dripping", "soaked", "juicy", "slippery",
                    "hard", "erect", "stiff", "throbbing", "pulsing", "swollen",
                    "tight", "loose", "stretched", "gaping", "spread wide",
                    "aroused", "horny", "lustful", "passionate", "heated", "burning",
                    "moaning", "gasping", "panting", "breathless", "sweating", "trembling"
                ],
                "intensity": "moderate",
                "weight": 2.0
            },
            "sexual_situations": {
                "keywords": [
                    "naked", "nude", "undressed", "stripped", "exposed", "bare",
                    "lingerie", "underwear", "panties", "bra", "stockings", "garter",
                    "transparent", "see-through", "sheer", "revealing", "skimpy",
                    "topless", "bottomless", "partial nudity", "wardrobe malfunction",
                    "bedroom", "bed", "shower", "bath", "intimate", "private", "alone"
                ],
                "intensity": "mild",
                "weight": 1.5
            },
            "sexual_poses": {
                "keywords": [
                    "seductive pose", "provocative pose", "legs spread", "arched back",
                    "bent over", "on all fours", "missionary", "doggy style", "cowgirl",
                    "reverse cowgirl", "69 position", "spooning", "from behind",
                    "touching self", "caressing", "groping", "fondling", "embracing"
                ],
                "intensity": "moderate",
                "weight": 2.5
            },
            "sexual_expressions": {
                "keywords": [
                    "bedroom eyes", "lustful gaze", "seductive smile", "sultry expression",
                    "orgasmic face", "pleasure face", "ecstasy", "blissful expression",
                    "come hither look", "fuck me eyes", "hungry look", "desire in eyes",
                    "passionate kiss", "french kiss", "tongue out", "licking lips"
                ],
                "intensity": "moderate",
                "weight": 2.0
            }
        }

    def classify_sexual_content(self, prompt: str) -> SexualExpressionResult:
        """プロンプトの性的内容を詳細分析"""
        prompt_lower = prompt.lower()

        total_score = 0.0
        matched_keywords = []
        intensity_scores = {"explicit": 0, "moderate": 0, "mild": 0}
        category_matches = {}

        # カテゴリ別分析
        for category, data in self.sexual_keywords.items():
            category_score = 0
            category_keywords = []

            for keyword in data["keywords"]:
                if keyword in prompt_lower:
                    score = data["weight"]
                    total_score += score
                    category_score += score
                    matched_keywords.append(keyword)
                    category_keywords.append(keyword)
                    intensity_scores[data["intensity"]] += score

            if category_keywords:
                category_matches[category] = {
                    "score": category_score,
                    "keywords": category_keywords
                }

        # 総合評価
        if intensity_scores["explicit"] > 0:
            intensity = "explicit"
        elif intensity_scores["moderate"] >= 3.0:
            intensity = "moderate"
        elif total_score >= 1.5:
            intensity = "mild"
        else:
            intensity = "none"

        # 主要カテゴリ決定
        if category_matches:
            primary_category = max(category_matches.keys(),
                                 key=lambda k: category_matches[k]["score"])
        else:
            primary_category = "none"

        confidence = min(total_score / 10.0, 1.0)

        return SexualExpressionResult(
            category="NSFW_SEXUAL" if intensity != "none" else "NON_SEXUAL",
            intensity=intensity,
            confidence=confidence,
            matched_keywords=matched_keywords,
            context_type=primary_category
        )

def reclassify_sexual_expressions():
    """性的表現の包括的再分類"""

    print("🔥 性的表現専用分類システム 開始 🔥")
    print("=" * 60)

    # データベース接続
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 分類器初期化
    classifier = SexualExpressionClassifier()

    # 1. 性的キーワードを含む全プロンプトを取得
    sexual_keywords_query = """
        SELECT DISTINCT id, full_prompt FROM civitai_prompts
        WHERE LOWER(full_prompt) LIKE '%sex%' OR LOWER(full_prompt) LIKE '%fucking%'
           OR LOWER(full_prompt) LIKE '%orgasm%' OR LOWER(full_prompt) LIKE '%pussy%'
           OR LOWER(full_prompt) LIKE '%cock%' OR LOWER(full_prompt) LIKE '%penis%'
           OR LOWER(full_prompt) LIKE '%breasts%' OR LOWER(full_prompt) LIKE '%nipples%'
           OR LOWER(full_prompt) LIKE '%ass%' OR LOWER(full_prompt) LIKE '%butt%'
           OR LOWER(full_prompt) LIKE '%wet%' OR LOWER(full_prompt) LIKE '%moaning%'
           OR LOWER(full_prompt) LIKE '%tight%' OR LOWER(full_prompt) LIKE '%anal%'
           OR LOWER(full_prompt) LIKE '%oral%' OR LOWER(full_prompt) LIKE '%kiss%'
           OR LOWER(full_prompt) LIKE '%seductive%' OR LOWER(full_prompt) LIKE '%provocative%'
           OR LOWER(full_prompt) LIKE '%lingerie%' OR LOWER(full_prompt) LIKE '%naked%'
           OR LOWER(full_prompt) LIKE '%bedroom%' OR LOWER(full_prompt) LIKE '%intimate%'
    """

    cursor.execute(sexual_keywords_query)
    sexual_candidates = cursor.fetchall()

    print(f"性的表現候補: {len(sexual_candidates)}件を分析...")

    # 2. 分析・再分類実行
    classification_stats = {
        "explicit": 0,
        "moderate": 0,
        "mild": 0,
        "reclassified": 0,
        "newly_classified": 0
    }

    high_value_samples = []

    for prompt_id, full_prompt in sexual_candidates:
        result = classifier.classify_sexual_content(full_prompt)

        if result.category == "NSFW_SEXUAL":
            # 既存分類確認
            cursor.execute("""
                SELECT category FROM prompt_categories WHERE prompt_id = ?
            """, (prompt_id,))
            current_category = cursor.fetchone()

            if current_category and current_category[0] != "NSFW":
                # 他カテゴリから性的NSFWに再分類
                cursor.execute("""
                    UPDATE prompt_categories
                    SET category = 'NSFW', confidence = ?
                    WHERE prompt_id = ?
                """, (result.confidence, prompt_id))
                classification_stats["reclassified"] += 1
            elif not current_category:
                # 新規性的分類
                cursor.execute("""
                    INSERT INTO prompt_categories (prompt_id, category, confidence)
                    VALUES (?, 'NSFW', ?)
                """, (prompt_id, result.confidence))
                classification_stats["newly_classified"] += 1

            # 強度別統計
            classification_stats[result.intensity] += 1

            # 高品質サンプル収集
            if (result.intensity == "explicit" or result.confidence >= 0.7) and len(high_value_samples) < 10:
                high_value_samples.append({
                    "prompt": full_prompt,
                    "intensity": result.intensity,
                    "confidence": result.confidence,
                    "keywords": result.matched_keywords[:5]
                })

    # 3. 結果コミット
    conn.commit()

    # 4. 統計表示
    print(f"\n🎯 性的表現分類 完了統計")
    print(f"{'=' * 40}")
    print(f"明示的表現 (explicit): {classification_stats['explicit']}件")
    print(f"中程度表現 (moderate): {classification_stats['moderate']}件")
    print(f"軽度表現 (mild): {classification_stats['mild']}件")
    print(f"再分類実行: {classification_stats['reclassified']}件")
    print(f"新規分類: {classification_stats['newly_classified']}件")

    # 5. 最終NSFW統計
    cursor.execute("SELECT COUNT(*) FROM prompt_categories WHERE category = 'NSFW'")
    final_nsfw_count = cursor.fetchone()[0]

    print(f"\n📊 最終NSFW統計")
    print(f"NSFW総数: {final_nsfw_count}件")
    print(f"改善数: +{classification_stats['reclassified'] + classification_stats['newly_classified']}件")

    # 6. 高価値サンプル表示
    print(f"\n🔥 高品質性的表現サンプル")
    print(f"{'=' * 50}")
    for i, sample in enumerate(high_value_samples, 1):
        print(f"{i}. [{sample['intensity'].upper()}] 信頼度: {sample['confidence']:.2f}")
        print(f"   キーワード: {', '.join(sample['keywords'])}")
        print(f"   プロンプト: {sample['prompt'][:100]}...")
        print(f"   {'-' * 30}")

    conn.close()
    print(f"\n✅ 性的表現の分類強化が完了しました！")
    print(f"WD14補強用の高品質性的表現データが大幅に増加しました。")

if __name__ == "__main__":
    reclassify_sexual_expressions()
