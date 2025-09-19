"""
プロンプト自動分類モジュール
CivitAIから収集したプロンプトを6カテゴリに自動分類
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

# 一時的にCATEGORIESを直接定義（config.pyが未作成の場合）
try:
    from .config import CATEGORIES
except ImportError:
    try:
        from src.config import CATEGORIES
    except ImportError:
        # config.pyが存在しない場合の暫定対応
        CATEGORIES = [
            "Character",
            "Style",
            "Environment",
            "Technical",
            "Objects",
            "Artistic"
        ]

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """分類結果を格納するデータクラス"""
    category: str
    confidence: float
    matched_keywords: List[str]

class PromptCategorizer:
    """プロンプト分類器"""

    def __init__(self):
        """初期化: カテゴリ別キーワード定義を読み込み"""
        self.category_keywords = self._load_category_keywords()
        self.confidence_weights = self._load_confidence_weights()

    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """カテゴリ別キーワードを定義"""
        return {
            "Character": [
                # 人物・キャラクター関連
                "girl", "woman", "man", "boy", "character", "person", "people",
                "face", "portrait", "beautiful", "cute", "handsome", "sexy",
                "anime", "manga", "waifu", "husbando", "idol", "model",
                "cosplay", "uniform", "dress", "clothing", "outfit",
                "hair", "eyes", "smile", "expression", "pose", "standing",
                "sitting", "lying", "walking", "running", "dancing",
                # 年齢・属性
                "teen", "young", "adult", "mature", "old", "child",
                "male", "female", "non-binary", "transgender",
                # 職業・役割
                "teacher", "student", "nurse", "maid", "warrior", "knight",
                "princess", "queen", "king", "priest", "witch", "demon",
                "angel", "vampire", "elf", "catgirl", "foxgirl"
            ],

            "Style": [
                # アートスタイル
                "realistic", "photorealistic", "hyperrealistic", "photography",
                "anime", "manga", "cartoon", "illustration", "painting",
                "digital art", "concept art", "sketch", "line art",
                "watercolor", "oil painting", "acrylic", "pencil drawing",
                "3d render", "cgi", "unreal engine", "blender",
                # アーティスト・スタジオ
                "studio ghibli", "pixar", "disney", "makoto shinkai",
                "hayao miyazaki", "artstation", "deviantart",
                # 写真・映像スタイル
                "cinematic", "film", "movie", "documentary", "vintage",
                "retro", "modern", "futuristic", "cyberpunk", "steampunk",
                "gothic", "baroque", "renaissance", "impressionist",
                # 品質・技術用語
                "masterpiece", "best quality", "high quality", "detailed",
                "ultra detailed", "extremely detailed", "intricate",
                "sharp focus", "professional", "award winning"
            ],

            "Environment": [
                # 場所・環境
                "background", "scenery", "landscape", "cityscape", "seascape",
                "indoor", "outdoor", "room", "bedroom", "kitchen", "bathroom",
                "office", "school", "classroom", "library", "cafe", "restaurant",
                "park", "garden", "forest", "mountain", "beach", "ocean",
                "city", "town", "village", "street", "road", "building",
                "house", "castle", "temple", "shrine", "church", "bridge",
                "sky", "clouds", "sun", "moon", "stars", "night", "day",
                "sunset", "sunrise", "rain", "snow", "storm", "weather",
                # 架空・ファンタジー環境
                "fantasy", "magical", "enchanted", "mystical", "ethereal",
                "otherworldly", "dimensional", "space", "alien planet",
                "underwater", "underground", "heaven", "hell", "limbo"
            ],

            "Technical": [
                # カメラ・撮影技術
                "camera", "lens", "focal length", "aperture", "depth of field",
                "bokeh", "macro", "wide angle", "telephoto", "fisheye",
                "close up", "medium shot", "long shot", "establishing shot",
                "pov", "first person", "third person", "overhead", "aerial",
                "low angle", "high angle", "dutch angle", "tracking shot",
                # ライティング
                "lighting", "natural light", "artificial light", "studio lighting",
                "soft light", "hard light", "rim light", "backlighting",
                "golden hour", "blue hour", "neon", "candlelight", "firelight",
                "dramatic lighting", "moody", "atmospheric", "ambient",
                # 色彩・構図
                "composition", "rule of thirds", "symmetry", "asymmetry",
                "leading lines", "framing", "negative space", "balance",
                "color palette", "monochrome", "black and white", "sepia",
                "vibrant", "muted", "saturated", "desaturated", "contrast",
                # 解像度・品質
                "4k", "8k", "hd", "uhd", "high resolution", "low resolution",
                "pixelated", "blurry", "noise", "grain", "smooth", "crisp"
            ],

            "Objects": [
                # 日用品・道具
                "object", "item", "tool", "weapon", "sword", "gun", "bow",
                "shield", "armor", "helmet", "crown", "jewelry", "ring",
                "necklace", "earrings", "bracelet", "watch", "glasses",
                "hat", "cap", "bag", "backpack", "purse", "wallet",
                "phone", "computer", "laptop", "tablet", "camera", "book",
                "pen", "pencil", "paper", "notebook", "diary", "letter",
                # 食べ物・飲み物
                "food", "drink", "meal", "breakfast", "lunch", "dinner",
                "snack", "dessert", "cake", "cookie", "bread", "rice",
                "noodles", "soup", "salad", "fruit", "vegetable", "meat",
                "coffee", "tea", "juice", "water", "wine", "beer", "sake",
                # 乗り物・機械
                "car", "bike", "motorcycle", "train", "plane", "ship", "boat",
                "robot", "mecha", "android", "cyborg", "machine", "engine",
                # 自然物
                "flower", "tree", "plant", "rock", "stone", "crystal", "gem",
                "fire", "water", "ice", "wind", "earth", "metal", "wood"
            ],

            "Artistic": [
                # 芸術的表現
                "artistic", "creative", "expressive", "abstract", "surreal",
                "impressionistic", "expressionistic", "cubist", "pop art",
                "street art", "graffiti", "mural", "sculpture", "statue",
                "installation", "performance art", "conceptual art",
                # 装飾・パターン
                "pattern", "texture", "ornament", "decoration", "design",
                "geometric", "organic", "floral", "tribal", "celtic",
                "mandala", "fractal", "kaleidoscope", "mosaic", "collage",
                # 象徴・メタファー
                "symbolic", "metaphorical", "allegorical", "mythological",
                "spiritual", "religious", "sacred", "divine", "transcendent",
                "dream", "nightmare", "vision", "hallucination", "trance",
                # 感情・雰囲気
                "emotional", "melancholic", "nostalgic", "romantic", "dramatic",
                "mysterious", "ominous", "peaceful", "chaotic", "serene",
                "intense", "gentle", "bold", "subtle", "elegant", "rustic"
            ]
        }

    def _load_confidence_weights(self) -> Dict[str, float]:
        """信頼度計算用の重み設定"""
        return {
            "exact_match": 1.0,      # 完全一致
            "partial_match": 0.7,    # 部分一致
            "keyword_density": 2.0,   # キーワード密度ボーナス
            "category_specificity": 1.5,  # カテゴリ特異性ボーナス
            "length_penalty": 0.1     # 長いプロンプトのペナルティ
        }

    def classify(self, prompt: str) -> ClassificationResult:
        """
        プロンプトを分類

        Args:
            prompt: 分類するプロンプトテキスト

        Returns:
            ClassificationResult: 分類結果
        """
        if not prompt or not prompt.strip():
            return ClassificationResult("Character", 0.0, [])

        # プロンプトを正規化
        normalized_prompt = self._normalize_prompt(prompt)

        # 各カテゴリのスコアを計算
        category_scores = {}
        category_matches = {}

        for category, keywords in self.category_keywords.items():
            score, matches = self._calculate_category_score(
                normalized_prompt, keywords
            )
            category_scores[category] = score
            category_matches[category] = matches

        # 最高スコアのカテゴリを選択
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        best_matches = category_matches[best_category]

        # 信頼度を正規化（0-1の範囲）
        confidence = min(best_score / 10.0, 1.0)

        return ClassificationResult(
            category=best_category,
            confidence=confidence,
            matched_keywords=best_matches
        )

    def _normalize_prompt(self, prompt: str) -> str:
        """プロンプトを正規化"""
        # 小文字変換
        normalized = prompt.lower()

        # 特殊文字の処理
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # 複数スペースを単一スペースに
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized.strip()

    def _calculate_category_score(self, prompt: str, keywords: List[str]) -> Tuple[float, List[str]]:
        """
        カテゴリスコアを計算

        Args:
            prompt: 正規化されたプロンプト
            keywords: カテゴリのキーワードリスト

        Returns:
            Tuple[float, List[str]]: (スコア, マッチしたキーワード)
        """
        matched_keywords = []
        total_score = 0.0

        prompt_words = set(prompt.split())
        prompt_length = len(prompt_words)

        for keyword in keywords:
            # 完全一致チェック
            if keyword in prompt:
                matched_keywords.append(keyword)

                # スコア計算
                if keyword in prompt_words:
                    # 単語として完全一致
                    total_score += self.confidence_weights["exact_match"]
                else:
                    # 部分文字列として一致
                    total_score += self.confidence_weights["partial_match"]

                # キーワード密度ボーナス
                keyword_count = prompt.count(keyword)
                if keyword_count > 1:
                    total_score += (keyword_count - 1) * self.confidence_weights["keyword_density"]

        # カテゴリ特異性ボーナス（マッチ数に基づく）
        if matched_keywords:
            specificity_bonus = len(matched_keywords) * self.confidence_weights["category_specificity"]
            total_score += specificity_bonus

        # 長いプロンプトにはペナルティ
        if prompt_length > 50:
            length_penalty = (prompt_length - 50) * self.confidence_weights["length_penalty"]
            total_score = max(0, total_score - length_penalty)

        return total_score, matched_keywords

    def classify_batch(self, prompts: List[str]) -> List[ClassificationResult]:
        """
        複数プロンプトをバッチ分類

        Args:
            prompts: プロンプトリスト

        Returns:
            List[ClassificationResult]: 分類結果リスト
        """
        results = []

        for prompt in prompts:
            try:
                result = self.classify(prompt)
                results.append(result)
            except Exception as e:
                logger.error(f"プロンプト分類エラー: {e}")
                # エラー時はデフォルトカテゴリ
                results.append(ClassificationResult("Character", 0.0, []))

        return results

    def get_category_distribution(self, prompts: List[str]) -> Dict[str, int]:
        """
        プロンプトリストのカテゴリ分布を取得

        Args:
            prompts: プロンプトリスト

        Returns:
            Dict[str, int]: カテゴリ別件数
        """
        # 実際に使用するカテゴリで初期化
        used_categories = list(self.category_keywords.keys())
        distribution = {category: 0 for category in used_categories}

        results = self.classify_batch(prompts)

        for result in results:
            if result.category in distribution:
                distribution[result.category] += 1
            else:
                # 未知のカテゴリの場合は追加
                distribution[result.category] = 1

        return distribution

    def get_low_confidence_prompts(self, prompts: List[str], threshold: float = 0.3) -> List[Tuple[str, ClassificationResult]]:
        """
        低信頼度プロンプトを取得（手動確認用）

        Args:
            prompts: プロンプトリスト
            threshold: 信頼度閾値

        Returns:
            List[Tuple[str, ClassificationResult]]: 低信頼度プロンプトと分類結果
        """
        low_confidence = []

        for prompt in prompts:
            result = self.classify(prompt)
            if result.confidence < threshold:
                low_confidence.append((prompt, result))

        return low_confidence

# 使用例・テスト用の関数
def test_categorizer():
    """categorizer.pyのテスト関数"""
    categorizer = PromptCategorizer()

    test_prompts = [
        "beautiful anime girl with long hair",
        "photorealistic portrait photography",
        "cyberpunk city at night with neon lights",
        "professional camera settings, 4k resolution",
        "magical sword with glowing crystals",
        "abstract art with vibrant colors"
    ]

    print("=== プロンプト分類テスト ===")
    for prompt in test_prompts:
        result = categorizer.classify(prompt)
        print(f"プロンプト: {prompt}")
        print(f"カテゴリ: {result.category}")
        print(f"信頼度: {result.confidence:.2f}")
        print(f"マッチキーワード: {result.matched_keywords[:5]}")  # 最初の5個
        print("-" * 50)

    print("\n=== カテゴリ分布 ===")
    distribution = categorizer.get_category_distribution(test_prompts)
    for category, count in distribution.items():
        print(f"{category}: {count}件")

if __name__ == "__main__":
    test_categorizer()
