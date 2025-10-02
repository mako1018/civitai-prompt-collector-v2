#!/usr/bin/env python3
"""NSFW分類強化スクリプト - 既存データの再分類と精度向上"""
import sqlite3
import sys
import re
from typing import List, Tuple, Dict
from dataclasses import dataclass

sys.path.append('src')
from database import DatabaseManager

@dataclass
class NSFWClassificationResult:
    is_nsfw: bool
    confidence: float
    matched_keywords: List[str]
    category_scores: Dict[str, float]

class EnhancedNSFWClassifier:
    """強化されたNSFW分類器"""

    def __init__(self):
        self.nsfw_keywords = self._load_enhanced_nsfw_keywords()
        self.confidence_threshold = 0.3

    def _load_enhanced_nsfw_keywords(self) -> Dict[str, List[str]]:
        """拡張NSFWキーワード辞書"""
        return {
            "explicit_high": [
                "nsfw", "explicit", "nude", "naked", "pussy", "topless", "bottomless",
                "nipples", "breasts", "uncensored", "18+", "erotic", "sexual", "sex"
            ],
            "explicit_medium": [
                "cleavage", "underwear", "lingerie", "bikini", "revealing", "exposed",
                "pantyhose", "stockings", "thong", "bra", "panties", "see-through",
                "transparent", "wet clothes", "bare shoulders", "midriff", "navel"
            ],
            "suggestive": [
                "seductive", "provocative", "suggestive", "sexy", "sensual", "alluring",
                "enticing", "bedroom eyes", "sultry", "flirtatious", "tempting",
                "passionate", "desire", "lust", "charm", "attraction"
            ],
            "adult_context": [
                "adult", "mature", "aged up", "18yo", "20yo", "young adult",
                "mature woman", "adult woman", "grown up", "of age"
            ],
            "poses_expressions": [
                "seductive pose", "bedroom pose", "sultry expression", "provocative look",
                "enticing expression", "alluring gaze", "passionate expression",
                "legs spread", "arched back", "touching self", "caressing"
            ]
        }

    def classify(self, prompt: str) -> NSFWClassificationResult:
        """プロンプトのNSFW分類を実行"""
        prompt_lower = prompt.lower()

        category_scores = {
            "explicit_high": 0.0,
            "explicit_medium": 0.0,
            "suggestive": 0.0,
            "adult_context": 0.0,
            "poses_expressions": 0.0
        }

        matched_keywords = []

        # カテゴリ別スコア計算
        for category, keywords in self.nsfw_keywords.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    if category == "explicit_high":
                        category_scores[category] += 3.0
                    elif category == "explicit_medium":
                        category_scores[category] += 2.0
                    else:
                        category_scores[category] += 1.0
                    matched_keywords.append(keyword)

        # 複合パターンボーナス
        compound_bonus = self._detect_compound_patterns(prompt_lower)

        # 総合スコア計算
        total_score = sum(category_scores.values()) + compound_bonus
        confidence = min(total_score / 10.0, 1.0)

        return NSFWClassificationResult(
            is_nsfw=confidence >= self.confidence_threshold,
            confidence=confidence,
            matched_keywords=matched_keywords,
            category_scores=category_scores
        )

    def _detect_compound_patterns(self, prompt: str) -> float:
        """複合パターン検出"""
        compound_score = 0.0

        # 身体部位 + 形容詞
        body_descriptors = [
            ("large breasts", 1.5), ("huge breasts", 2.0), ("curvy body", 1.0),
            ("perfect body", 0.5), ("toned thighs", 0.5), ("long legs", 0.3)
        ]

        for pattern, score in body_descriptors:
            if pattern in prompt:
                compound_score += score

        # 視線・表情の複合
        gaze_patterns = [
            ("bedroom eyes", 2.0), ("seductive gaze", 1.5), ("lustful look", 2.0),
            ("enticing expression", 1.0), ("provocative smile", 1.0)
        ]

        for pattern, score in gaze_patterns:
            if pattern in prompt:
                compound_score += score

        return compound_score

def reclassify_nsfw_data():
    """既存データのNSFW再分類を実行"""

    print("NSFW分類強化プログラム開始...")

    # データベース接続
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # 強化分類器初期化
    classifier = EnhancedNSFWClassifier()

    # 1. NSFWキーワードを含むが他カテゴリに分類されているプロンプトを取得
    cursor.execute("""
        SELECT DISTINCT cp.id, cp.full_prompt, pc.category, pc.confidence
        FROM civitai_prompts cp
        LEFT JOIN prompt_categories pc ON cp.id = pc.prompt_id
        WHERE LOWER(cp.full_prompt) LIKE '%nsfw%'
           OR LOWER(cp.full_prompt) LIKE '%nude%'
           OR LOWER(cp.full_prompt) LIKE '%explicit%'
           OR LOWER(cp.full_prompt) LIKE '%adult%'
           OR LOWER(cp.full_prompt) LIKE '%seductive%'
           OR LOWER(cp.full_prompt) LIKE '%sexy%'
           OR LOWER(cp.full_prompt) LIKE '%erotic%'
           OR LOWER(cp.full_prompt) LIKE '%provocative%'
           OR LOWER(cp.full_prompt) LIKE '%suggestive%'
           OR LOWER(cp.full_prompt) LIKE '%bedroom eyes%'
           OR LOWER(cp.full_prompt) LIKE '%enticing%'
           OR LOWER(cp.full_prompt) LIKE '%alluring%'
    """)

    candidates = cursor.fetchall()
    print(f"NSFW候補プロンプト: {len(candidates)}件を分析中...")

    # 2. 再分類実行
    reclassified = 0
    newly_classified = 0
    improved_confidence = 0

    for prompt_id, full_prompt, current_category, current_confidence in candidates:
        result = classifier.classify(full_prompt)

        if result.is_nsfw:
            if current_category != "NSFW":
                # 他カテゴリからNSFWに変更
                if current_category:
                    cursor.execute("""
                        UPDATE prompt_categories
                        SET category = 'NSFW', confidence = ?
                        WHERE prompt_id = ?
                    """, (result.confidence, prompt_id))
                    reclassified += 1
                else:
                    # 新規NSFW分類
                    cursor.execute("""
                        INSERT INTO prompt_categories (prompt_id, category, confidence)
                        VALUES (?, 'NSFW', ?)
                    """, (prompt_id, result.confidence))
                    newly_classified += 1
            elif result.confidence > (current_confidence or 0):
                # NSFW信頼度の向上
                cursor.execute("""
                    UPDATE prompt_categories
                    SET confidence = ?
                    WHERE prompt_id = ? AND category = 'NSFW'
                """, (result.confidence, prompt_id))
                improved_confidence += 1

    # 3. 結果のコミット
    conn.commit()

    # 4. 分析結果の表示
    print(f"\n=== NSFW分類強化 完了 ===")
    print(f"他カテゴリからNSFWに再分類: {reclassified}件")
    print(f"新規NSFW分類: {newly_classified}件")
    print(f"NSFW信頼度向上: {improved_confidence}件")

    # 5. 最終統計
    cursor.execute("SELECT category, COUNT(*) FROM prompt_categories GROUP BY category ORDER BY COUNT(*) DESC")
    final_distribution = cursor.fetchall()

    print(f"\n=== 最終カテゴリ分布 ===")
    for category, count in final_distribution:
        print(f"{category}: {count}件")

    # 6. NSFWサンプル確認
    cursor.execute("""
        SELECT full_prompt FROM civitai_prompts cp
        JOIN prompt_categories pc ON cp.id = pc.prompt_id
        WHERE pc.category = 'NSFW' AND pc.confidence >= 0.7
        ORDER BY pc.confidence DESC
        LIMIT 5
    """)

    high_confidence_nsfw = cursor.fetchall()
    print(f"\n=== 高信頼度NSFWサンプル ===")
    for i, (prompt,) in enumerate(high_confidence_nsfw, 1):
        print(f"{i}: {prompt[:100]}...")

    conn.close()
    print(f"\nNSFW分類強化が完了しました！")

if __name__ == "__main__":
    reclassify_nsfw_data()
