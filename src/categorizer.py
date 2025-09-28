"""
プロンプト自動分類モジュール
CivitAIから収集したプロンプトを正しい6カテゴリに自動分類
NSFW, style, lighting, composition, mood, basic, technical
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
        from config import CATEGORIES
    except ImportError:
        # config.pyが存在しない場合の暫定対応
        CATEGORIES = [
            "NSFW",
            "style",
            "lighting",
            "composition",
            "mood",
            "basic",
            "technical"
        ]

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """分類結果を格納するデータクラス"""
    category: str
    confidence: float
    matched_keywords: List[str]

class PromptCategorizer:
    """プロンプト分類器 - 正しいカテゴリ定義版"""

    def __init__(self):
        """初期化: カテゴリ別キーワード定義を読み込み"""
        self.category_keywords = self._load_category_keywords()
        self.confidence_weights = self._load_confidence_weights()

    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """正しいカテゴリ別キーワードを定義"""
        return {
            "NSFW": [
                # 成人向けコンテンツ
                "nsfw", "explicit", "nude", "naked", "pussy", "topless", "bottomless",
                "nipples", "breasts", "cleavage", "underwear", "lingerie", "bikini",
                "swimsuit", "revealing", "exposed", "uncensored", "18+", "adult",
                "erotic", "sexual", "sex",  "blow job","seductive", "provocative", "suggestive",
                "pantyhose", "stockings", "thong", "bra", "panties", "see-through",
                "transparent", "wet clothes", "tight clothes", "short dress",
                "mini skirt", "low cut", "deep neckline", "bare shoulders",
                "midriff", "belly", "navel", "partial nudity", "sideboob",
                "underboob", "cameltoe", "upskirt", "downblouse", "wardrobe malfunction"
            ],

            "style": [
                # アートスタイル・技法
                "realistic", "photorealistic", "hyperrealistic", "photography",
                "anime", "manga", "cartoon", "illustration", "painting",
                "digital art", "concept art", "sketch", "line art", "cel shading",
                "watercolor", "oil painting", "acrylic", "pencil drawing", "charcoal",
                "3d render", "cgi", "unreal engine", "blender", "maya",
                "studio ghibli", "pixar", "disney", "makoto shinkai",
                "hayao miyazaki", "artstation", "deviantart", "pixiv",
                "cinematic", "film", "movie", "documentary", "vintage",
                "retro", "modern", "futuristic", "cyberpunk", "steampunk",
                "gothic", "baroque", "renaissance", "impressionist", "abstract",
                "surreal", "pop art", "minimalist", "maximalist", "grunge"
            ],

            "lighting": [
                # ライティング・照明
                "lighting", "light", "illumination", "brightness", "darkness",
                "natural light", "artificial light", "studio lighting", "professional lighting",
                "soft light", "hard light", "diffused light", "directional light",
                "rim light", "backlighting", "front lighting", "side lighting",
                "top lighting", "bottom lighting", "ambient light", "fill light",
                "key light", "bounce light", "reflected light", "harsh light",
                "gentle light", "warm light", "cool light", "colored light",
                "golden hour", "blue hour", "magic hour", "sunset lighting",
                "sunrise lighting", "noon lighting", "twilight", "dusk", "dawn",
                "candlelight", "firelight", "moonlight", "starlight", "neon light",
                "led light", "fluorescent", "incandescent", "spotlight", "floodlight",
                "dramatic lighting", "moody lighting", "atmospheric lighting",
                "cinematic lighting", "volumetric lighting", "god rays", "lens flare",
                "shadow", "shadows", "cast shadow", "drop shadow", "silhouette",
                "contrast", "high contrast", "low contrast", "chiaroscuro"
            ],

            "composition": [
                # 構図・カメラアングル・フレーミング
                "composition", "framing", "frame", "angle", "perspective", "viewpoint",
                "camera angle", "shot", "view", "position", "placement",
                "close up", "close-up", "macro", "extreme close up", "medium shot",
                "medium close up", "long shot", "wide shot", "full shot",
                "establishing shot", "master shot", "two shot", "over shoulder",
                "point of view", "pov", "first person", "third person",
                "bird's eye view", "aerial view", "overhead view", "top view",
                "worm's eye view", "low angle", "high angle", "eye level",
                "dutch angle", "tilted", "canted", "diagonal", "straight",
                "centered", "off-center", "symmetrical", "asymmetrical",
                "rule of thirds", "golden ratio", "leading lines", "vanishing point",
                "foreground", "middle ground", "background", "depth of field",
                "shallow focus", "deep focus", "bokeh", "blur", "sharp focus",
                "negative space", "positive space", "balance", "imbalance",
                "cropped", "full body", "half body", "head and shoulders",
                "portrait", "landscape", "square", "panoramic", "wide angle",
                "telephoto", "fisheye", "tilt shift"
            ],

            "mood": [
                # 雰囲気・感情・トーン
                "mood", "atmosphere", "feeling", "emotion", "tone", "vibe",
                "ambience", "ambiance", "aura", "energy", "spirit",
                "happy", "joyful", "cheerful", "upbeat", "positive", "optimistic",
                "sad", "melancholic", "sorrowful", "depressing", "gloomy", "somber",
                "angry", "aggressive", "fierce", "intense", "violent", "rage",
                "calm", "peaceful", "serene", "tranquil", "relaxed", "zen",
                "mysterious", "enigmatic", "cryptic", "secretive", "hidden",
                "scary", "frightening", "terrifying", "horrifying", "spooky", "eerie",
                "romantic", "loving", "passionate", "intimate", "tender", "sweet",
                "dramatic", "theatrical", "epic", "grand", "majestic", "powerful",
                "nostalgic", "wistful", "longing", "reminiscent", "bittersweet",
                "dreamy", "ethereal", "surreal", "fantastical", "whimsical",
                "dark", "moody", "brooding", "ominous", "foreboding", "sinister",
                "bright", "vibrant", "lively", "energetic", "dynamic", "explosive",
                "soft", "gentle", "delicate", "subtle", "muted", "understated",
                "bold", "striking", "dramatic", "vivid", "saturated", "intense"
            ],

            "basic": [
                # 基本的な品質・技術用語
                "masterpiece", "best quality", "high quality", "ultra quality",
                "highest quality", "premium quality", "professional quality",
                "detailed", "ultra detailed", "extremely detailed", "highly detailed",
                "intricate", "complex", "elaborate", "sophisticated", "refined",
                "sharp", "crisp", "clear", "clean", "smooth", "polished",
                "perfect", "flawless", "immaculate", "pristine", "impeccable",
                "beautiful", "gorgeous", "stunning", "amazing", "incredible",
                "spectacular", "breathtaking", "magnificent", "excellent",
                "outstanding", "exceptional", "remarkable", "impressive",
                "vivid", "vibrant", "rich", "deep", "intense", "saturated",
                "realistic", "lifelike", "natural", "authentic", "genuine",
                "award winning", "professional", "expert", "skillful", "masterful",
                "artistic", "creative", "original", "unique", "innovative",
                "stylish", "elegant", "graceful", "sophisticated", "classy"
            ],

            "technical": [
                # 技術仕様・解像度・カメラ設定
                "4k", "8k", "16k", "32k", "hd", "uhd", "full hd", "2k",
                "high resolution", "ultra high resolution", "high res", "ultra high res",
                "low resolution", "low res", "pixelated", "pixel art", "retro pixel",
                "resolution", "dpi", "ppi", "pixel", "megapixel", "mp",
                "aspect ratio", "16:9", "4:3", "1:1", "21:9", "ultrawide",
                "vertical", "horizontal", "square", "panoramic", "widescreen",
                "camera", "lens", "focal length", "aperture", "f-stop", "f/1.4", "f/2.8",
                "iso", "shutter speed", "exposure", "overexposed", "underexposed",
                "white balance", "color temperature", "kelvin", "daylight", "tungsten",
                "macro lens", "wide angle lens", "telephoto lens", "prime lens",
                "zoom lens", "fisheye lens", "tilt-shift lens", "portrait lens",
                "canon", "nikon", "sony", "fujifilm", "leica", "pentax", "olympus",
                "dslr", "mirrorless", "film camera", "digital camera", "medium format",
                "35mm", "full frame", "crop sensor", "aps-c", "micro four thirds",
                "raw", "jpeg", "tiff", "png", "bmp", "gif", "webp",
                "noise", "grain", "chromatic aberration", "vignetting", "distortion",
                "sharpness", "contrast", "saturation", "vibrance", "clarity",
                "highlights", "shadows", "midtones", "blacks", "whites",
                "hdr", "dynamic range", "tone mapping", "exposure bracketing"
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
            return ClassificationResult("basic", 0.0, [])

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
                results.append(ClassificationResult("basic", 0.0, []))

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
        "masterpiece, best quality, 1girl, beautiful",
        "nsfw, nude, explicit content, adult",
        "cinematic lighting, dramatic shadows, golden hour",
        "close up portrait, rule of thirds, shallow depth of field",
        "dark moody atmosphere, mysterious, gothic",
        "oil painting style, realistic, detailed brushwork",
        "4k resolution, high quality, professional photography"
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

def process_database_prompts():
    """データベースから実際のプロンプトを取得して分類"""
    try:
        # データベース接続
        try:
            from src.database import DatabaseManager
        except ImportError:
            from .database import DatabaseManager

        db = DatabaseManager()
        categorizer = PromptCategorizer()

        # データベースからプロンプトを取得
        prompts_data = db.get_all_prompts()

        if not prompts_data:
            print("データベースにプロンプトが見つかりません")
            print("先に collector.py を実行してデータを収集してください")
            return

        from datetime import datetime, timedelta, timezone
        JST = timezone(timedelta(hours=9))
        now_jst = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[JST:{now_jst}] データベースから {len(prompts_data)} 件のプロンプトを取得")
        print("正しいカテゴリ(NSFW, style, lighting, composition, mood, basic, technical)で再分類中...")

        # 全件再分類オプション（Trueなら従来通り全件DELETE→再分類、Falseなら新規のみ分類）
        FULL_RECLASSIFY = False  # 必要ならTrueに
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        if FULL_RECLASSIFY:
            cursor.execute('DELETE FROM prompt_categories')
            conn.commit()
            print("既存の分類データをクリア完了（全件再分類）")
        # 既存分類済みプロンプトIDを取得
        cursor.execute('SELECT prompt_id FROM prompt_categories')
        already_classified = set(row[0] for row in cursor.fetchall())
        conn.close()

        # プロンプト分類
        classified_count = 0
        for prompt_data in prompts_data:
            full_prompt = prompt_data.get('full_prompt', '')
            prompt_id = prompt_data.get('id')
            if not full_prompt or not prompt_id:
                continue
            # FULL_RECLASSIFYなら全件、そうでなければ未分類のみ
            if FULL_RECLASSIFY or prompt_id not in already_classified:
                result = categorizer.classify(full_prompt)
                categories_data = {
                    result.category: {
                        "keywords": result.matched_keywords,
                        "confidence": result.confidence
                    }
                }
                if db.save_prompt_categories(prompt_id, categories_data):
                    classified_count += 1
        now_jst = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[JST:{now_jst}] 分類完了: {classified_count} 件（新規分類のみ。全件再分類はFULL_RECLASSIFY=Trueで実行）")

        # 分布統計表示
        prompts_text = [p.get('full_prompt', '') for p in prompts_data if p.get('full_prompt')]
        distribution = categorizer.get_category_distribution(prompts_text)

        print("\n=== 正しいカテゴリ分布 ===")
        for category, count in distribution.items():
            print(f"{category}: {count}件")

        print(f"\n次は python main.py --visualize-only を実行してグラフを生成してください")

    except Exception as e:
        print(f"エラー: {e}")

def main():
    """メイン関数"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # テストモード
        test_categorizer()
    else:
        # 実データ処理モード
        process_database_prompts()

if __name__ == "__main__":
    main()
