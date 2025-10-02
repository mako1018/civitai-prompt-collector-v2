# NSFW カテゴリ強化・修正プログラム

## 🎯 目的

NSFWカテゴリの分類精度向上と分類漏れの解消により、WD14補強で必要なNSFW表現を確実に活用できるようにする。

## 🔧 実装内容

### 1. 拡張NSFWキーワード辞書

```python
ENHANCED_NSFW_KEYWORDS = {
    "explicit": [
        "nsfw", "explicit", "nude", "naked", "pussy", "topless", "bottomless",
        "nipples", "breasts", "cleavage", "uncensored", "18+", "adult content",
        "erotic", "sexual", "sex", "blow job", "oral", "penetration"
    ],
    "suggestive": [
        "seductive", "provocative", "suggestive", "sexy", "sensual", "alluring",
        "enticing", "bedroom eyes", "sultry", "flirtatious", "tempting",
        "allure", "charm", "attraction", "desire", "lust", "passion"
    ],
    "clothing": [
        "underwear", "lingerie", "bikini", "swimsuit", "revealing", "exposed",
        "pantyhose", "stockings", "thong", "bra", "panties", "see-through",
        "transparent", "wet clothes", "tight clothes", "short dress",
        "mini skirt", "low cut", "deep neckline", "bare shoulders",
        "midriff", "belly", "navel", "cleavage", "sideboob", "underboob"
    ],
    "poses": [
        "seductive pose", "provocative pose", "sultry pose", "bedroom pose",
        "legs spread", "arched back", "bent over", "leaning forward",
        "hands on hips", "touching self", "caressing", "intimate pose"
    ],
    "expressions": [
        "bedroom eyes", "lustful gaze", "seductive smile", "sultry expression",
        "provocative look", "enticing expression", "alluring gaze",
        "passionate expression", "desire in eyes", "sensual lips"
    ],
    "adult_terms": [
        "adult", "mature", "aged up", "18yo", "20yo", "young adult",
        "mature woman", "adult woman", "grown up", "of age"
    ]
}
```

### 2. 改良された分類アルゴリズム

```python
class EnhancedNSFWCategorizer:
    def __init__(self):
        self.nsfw_patterns = self.load_nsfw_patterns()
        self.confidence_threshold = 0.3  # NSFW判定の閾値を下げる

    def classify_nsfw(self, prompt: str) -> ClassificationResult:
        prompt_lower = prompt.lower()
        nsfw_score = 0
        matched_keywords = []

        # 1. 明示的キーワードチェック（高重み）
        for keyword in self.nsfw_patterns["explicit"]:
            if keyword in prompt_lower:
                nsfw_score += 3.0
                matched_keywords.append(keyword)

        # 2. 示唆的表現チェック（中重み）
        for keyword in self.nsfw_patterns["suggestive"]:
            if keyword in prompt_lower:
                nsfw_score += 2.0
                matched_keywords.append(keyword)

        # 3. 衣装・ポーズ・表情チェック（低重み）
        for category in ["clothing", "poses", "expressions", "adult_terms"]:
            for keyword in self.nsfw_patterns[category]:
                if keyword in prompt_lower:
                    nsfw_score += 1.0
                    matched_keywords.append(keyword)

        # 4. 複合パターン検出
        nsfw_score += self.detect_compound_patterns(prompt_lower)

        # 信頼度計算
        confidence = min(nsfw_score / 10.0, 1.0)

        return ClassificationResult(
            category="NSFW" if confidence >= self.confidence_threshold else None,
            confidence=confidence,
            matched_keywords=matched_keywords
        )

    def detect_compound_patterns(self, prompt: str) -> float:
        """複合的なNSFW表現を検出"""
        compound_score = 0

        # 身体部位 + 形容詞の組み合わせ
        body_parts = ["breasts", "chest", "thighs", "legs", "body"]
        descriptors = ["large", "huge", "curvy", "toned", "perfect", "beautiful"]

        for body in body_parts:
            for desc in descriptors:
                if body in prompt and desc in prompt:
                    compound_score += 0.5

        # 視線・表情 + 誘惑的表現
        gaze_words = ["eyes", "gaze", "look", "stare"]
        seductive_words = ["seductive", "bedroom", "sultry", "enticing"]

        for gaze in gaze_words:
            for seductive in seductive_words:
                if gaze in prompt and seductive in prompt:
                    compound_score += 1.0

        return compound_score
```

### 3. 既存データの再分類

```python
def reclassify_nsfw_prompts():
    """既存のプロンプトをNSFW強化分類器で再分類"""

    db = DatabaseManager()
    categorizer = EnhancedNSFWCategorizer()

    # NSFWキーワードを含むが他カテゴリに分類されているプロンプトを取得
    misclassified_prompts = db.get_misclassified_nsfw_prompts()

    reclassified_count = 0
    for prompt_id, full_prompt in misclassified_prompts:
        result = categorizer.classify_nsfw(full_prompt)

        if result.category == "NSFW":
            # NSFWカテゴリに再分類
            db.update_prompt_category(prompt_id, "NSFW", result.confidence)
            reclassified_count += 1

    print(f"再分類完了: {reclassified_count}件をNSFWカテゴリに移動")
```

### 4. WD14補強での活用強化

```python
class NSFWEnhancedPromptBooster:
    """NSFW表現を重視したWD14補強システム"""

    def enhance_wd14_for_nsfw(self, wd14_tags: List[str], enhancement_level: float = 0.8):
        # 1. NSFW関連の基本タグを検出
        nsfw_context = self.detect_nsfw_context(wd14_tags)

        # 2. CivitAI NSFWデータから適切な補強要素を選択
        nsfw_prompts = self.get_high_quality_nsfw_prompts(nsfw_context)

        # 3. 段階的に表現を追加
        enhanced_prompt = self.apply_nsfw_enhancements(
            wd14_tags, nsfw_prompts, enhancement_level
        )

        return enhanced_prompt

    def get_high_quality_nsfw_prompts(self, context: dict) -> List[str]:
        """高品質なNSFWプロンプトを取得"""
        db = DatabaseManager()

        # NSFW かつ 品質スコア15以上のプロンプトを取得
        query = """
        SELECT full_prompt FROM civitai_prompts cp
        JOIN prompt_categories pc ON cp.id = pc.prompt_id
        WHERE pc.category = 'NSFW'
        AND cp.quality_score >= 15
        AND pc.confidence >= 0.5
        ORDER BY cp.quality_score DESC
        LIMIT 100
        """

        return db.execute_query(query)
```

## 📈 期待される改善効果

### Before（現状）
- NSFW分類率: 96.4%
- 分類漏れ: 79件
- 誤分類: 169件（basicカテゴリ）

### After（改善後）
- NSFW分類率: **99.5%以上**
- 分類漏れ: **5件未満**
- 誤分類: **大幅減少**

### WD14補強での効果
```
Before: "1girl, long hair, blue dress"
After: "masterpiece, best quality, 1girl, long hair, blue dress,
       seductive pose, bedroom eyes, alluring gaze, sensual expression,
       elegant beauty, captivating charm, sophisticated allure"
```

## 🚀 実装手順

1. **Phase 1**: 拡張NSFWキーワード辞書の実装
2. **Phase 2**: 改良分類アルゴリズムの適用
3. **Phase 3**: 既存データの一括再分類
4. **Phase 4**: WD14補強システムへの統合
5. **Phase 5**: 効果測定とファインチューニング

この改善により、NSFWカテゴリの表現が大幅に充実し、WD14の表現不足を効果的に補完できるようになります。
