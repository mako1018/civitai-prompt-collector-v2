# ComfyUI WD14拡張ノード 実装仕様書

## 🎯 ノード設計概要

WD14 TaggerとCivitAI補強システムを統合した新しいComfyUIノード群を設計します。

## 🔧 ノード一覧

### 1. WD14_CivitAI_Enhanced_Tagger

**基本機能**: WD14出力を自動的にCivitAIデータで補強

```python
class WD14CivitAIEnhancedTagger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "enhancement_strength": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1,
                    "display": "slider"
                }),
                "categories": (["all", "lighting", "composition", "style", "mood"], {
                    "default": "all"
                }),
            },
            "optional": {
                "wd14_model": (["wd-v1-4-moat-tagger-v2", "wd-v1-4-swinv2-tagger-v2"], {
                    "default": "wd-v1-4-moat-tagger-v2"
                }),
                "quality_boost": ("BOOLEAN", {"default": True}),
                "civitai_db_path": ("STRING", {"default": ""}),
                "custom_keywords": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "DICT")
    RETURN_NAMES = ("enhanced_prompt", "original_wd14", "enhancement_details")
    FUNCTION = "enhance_wd14_tags"
    CATEGORY = "CivitAI/WD14Enhancement"

    def enhance_wd14_tags(self, image, enhancement_strength, categories, **kwargs):
        # 1. WD14でタグ生成
        wd14_tags = self.run_wd14_tagger(image, kwargs.get('wd14_model'))

        # 2. CivitAIデータベースから補強要素を取得
        enhancer = CivitAIEnhancer(kwargs.get('civitai_db_path'))
        enhancements = enhancer.get_enhancements(
            wd14_tags, categories, enhancement_strength
        )

        # 3. 最終プロンプト生成
        enhanced_prompt = self.combine_tags(wd14_tags, enhancements, kwargs)

        return (enhanced_prompt, ', '.join(wd14_tags), enhancements)
```

### 2. Prompt_Style_Transfer

**基本機能**: 既存プロンプトを特定スタイルに変換

```python
class PromptStyleTransfer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_prompt": ("STRING", {"multiline": True}),
                "target_style": ([
                    "cinematic", "anime", "realistic", "artistic",
                    "vintage", "futuristic", "minimalist", "dramatic"
                ], {"default": "cinematic"}),
                "transfer_strength": ("FLOAT", {
                    "default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1
                }),
            },
            "optional": {
                "preserve_subjects": ("BOOLEAN", {"default": True}),
                "add_negative": ("BOOLEAN", {"default": True}),
                "style_reference": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("styled_prompt", "negative_prompt", "style_analysis")
    FUNCTION = "transfer_style"
    CATEGORY = "CivitAI/Enhancement"

    def transfer_style(self, input_prompt, target_style, transfer_strength, **kwargs):
        # CivitAIから該当スタイルのプロンプトパターンを分析
        style_analyzer = StyleAnalyzer()
        style_patterns = style_analyzer.get_style_patterns(target_style)

        # 既存プロンプトの要素分析
        prompt_analyzer = PromptAnalyzer()
        elements = prompt_analyzer.parse_elements(input_prompt)

        # スタイル転送実行
        transferred = self.apply_style_transfer(
            elements, style_patterns, transfer_strength, kwargs
        )

        return transferred
```

### 3. Prompt_Quality_Enhancer

**基本機能**: プロンプトの品質を自動改善

```python
class PromptQualityEnhancer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_prompt": ("STRING", {"multiline": True}),
                "quality_level": (["basic", "intermediate", "advanced", "professional"], {
                    "default": "intermediate"
                }),
                "enhancement_focus": ([
                    "technical", "artistic", "detailed", "lighting", "composition"
                ], {"default": "technical"}),
            },
            "optional": {
                "preserve_original": ("BOOLEAN", {"default": True}),
                "add_quality_tags": ("BOOLEAN", {"default": True}),
                "target_length": ("INT", {"default": 0, "min": 0, "max": 200}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "DICT")
    RETURN_NAMES = ("enhanced_prompt", "quality_score", "improvements")
    FUNCTION = "enhance_quality"
    CATEGORY = "CivitAI/Enhancement"

    def enhance_quality(self, input_prompt, quality_level, enhancement_focus, **kwargs):
        # 現在の品質スコア計算
        quality_scorer = QualityScorer()
        current_score = quality_scorer.calculate_score(input_prompt)

        # 品質向上要素を追加
        enhancer = QualityEnhancer()
        enhanced_prompt = enhancer.enhance_prompt(
            input_prompt, quality_level, enhancement_focus, kwargs
        )

        # 改善後のスコア
        new_score = quality_scorer.calculate_score(enhanced_prompt)

        improvements = {
            'original_score': current_score,
            'enhanced_score': new_score,
            'added_elements': enhancer.get_added_elements(),
            'improvement_ratio': (new_score - current_score) / current_score
        }

        return (enhanced_prompt, new_score, improvements)
```

### 4. CivitAI_Prompt_Database_Search

**基本機能**: CivitAIデータベースから関連プロンプトを検索

```python
class CivitAIPromptDatabaseSearch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "search_query": ("STRING", {"multiline": True}),
                "search_type": (["semantic", "keyword", "category", "model_based"], {
                    "default": "semantic"
                }),
                "max_results": ("INT", {"default": 10, "min": 1, "max": 100}),
            },
            "optional": {
                "category_filter": ([
                    "all", "nsfw", "style", "lighting", "composition",
                    "mood", "basic", "technical"
                ], {"default": "all"}),
                "quality_threshold": ("INT", {"default": 5, "min": 0, "max": 50}),
                "model_id": ("STRING", {"default": ""}),
                "exclude_nsfw": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("LIST", "LIST", "DICT")
    RETURN_NAMES = ("prompts", "metadata", "search_stats")
    FUNCTION = "search_database"
    CATEGORY = "CivitAI/Database"

    def search_database(self, search_query, search_type, max_results, **kwargs):
        # データベース接続
        db_manager = DatabaseManager()

        # 検索実行
        if search_type == "semantic":
            results = self.semantic_search(search_query, max_results, kwargs)
        elif search_type == "keyword":
            results = self.keyword_search(search_query, max_results, kwargs)
        elif search_type == "category":
            results = self.category_search(search_query, max_results, kwargs)
        else:  # model_based
            results = self.model_based_search(search_query, max_results, kwargs)

        # 結果の整形
        prompts = [r['full_prompt'] for r in results]
        metadata = [r['metadata'] for r in results]
        stats = self.calculate_search_stats(results, search_query)

        return (prompts, metadata, stats)
```

### 5. Prompt_A_B_Tester

**基本機能**: 2つのプロンプトを比較テスト

```python
class PromptABTester:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompt_a": ("STRING", {"multiline": True}),
                "prompt_b": ("STRING", {"multiline": True}),
                "test_image": ("IMAGE",),
                "comparison_metrics": ([
                    "quality_score", "complexity", "category_coverage", "length"
                ], {"default": "quality_score"}),
            },
            "optional": {
                "generate_variants": ("BOOLEAN", {"default": False}),
                "save_results": ("BOOLEAN", {"default": True}),
                "test_name": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "DICT")
    RETURN_NAMES = ("winner", "recommendation", "detailed_analysis")
    FUNCTION = "compare_prompts"
    CATEGORY = "CivitAI/Testing"

    def compare_prompts(self, prompt_a, prompt_b, test_image, comparison_metrics, **kwargs):
        # 各プロンプトを分析
        analyzer = PromptAnalyzer()
        analysis_a = analyzer.analyze_comprehensive(prompt_a)
        analysis_b = analyzer.analyze_comprehensive(prompt_b)

        # 画像との適合度チェック
        compatibility_checker = ImageCompatibilityChecker()
        compat_a = compatibility_checker.check_compatibility(test_image, prompt_a)
        compat_b = compatibility_checker.check_compatibility(test_image, prompt_b)

        # 総合スコア計算
        score_a = self.calculate_total_score(analysis_a, compat_a, comparison_metrics)
        score_b = self.calculate_total_score(analysis_b, compat_b, comparison_metrics)

        # 勝者決定と推奨事項生成
        if score_a > score_b:
            winner = "Prompt A"
            recommendation = self.generate_recommendation(prompt_a, analysis_a)
        else:
            winner = "Prompt B"
            recommendation = self.generate_recommendation(prompt_b, analysis_b)

        detailed_analysis = {
            'prompt_a_score': score_a,
            'prompt_b_score': score_b,
            'winner': winner,
            'score_difference': abs(score_a - score_b),
            'analysis_a': analysis_a,
            'analysis_b': analysis_b,
        }

        return (winner, recommendation, detailed_analysis)
```

## 🔧 サポートクラス実装

### CivitAIEnhancer

```python
class CivitAIEnhancer:
    def __init__(self, db_path: str):
        self.db_manager = DatabaseManager(db_path)
        self.categorizer = PromptCategorizer()

    def get_enhancements(self, wd14_tags: List[str], categories: str, strength: float) -> Dict:
        """WD14タグに基づいて補強要素を取得"""

        # 1. WD14タグを解析してコンテキスト抽出
        context = self.analyze_wd14_context(wd14_tags)

        # 2. カテゴリ別に補強候補を検索
        enhancements = {}
        if categories == "all":
            target_categories = ["lighting", "composition", "style", "mood", "technical"]
        else:
            target_categories = [categories]

        for category in target_categories:
            candidates = self.search_category_enhancements(context, category)
            selected = self.select_enhancements(candidates, strength)
            enhancements[category] = selected

        return enhancements

    def analyze_wd14_context(self, tags: List[str]) -> Dict:
        """WD14タグからコンテキスト情報を抽出"""
        context = {
            'subject_type': self.detect_subject_type(tags),  # person, object, scene
            'scene_type': self.detect_scene_type(tags),      # portrait, landscape, etc
            'art_style': self.detect_art_style(tags),        # anime, realistic, etc
            'existing_quality': self.assess_quality_level(tags),
            'missing_elements': self.identify_missing_elements(tags)
        }
        return context

    def search_category_enhancements(self, context: Dict, category: str) -> List[str]:
        """指定カテゴリから補強候補を検索"""

        # データベースから関連プロンプトを検索
        query_conditions = self.build_search_conditions(context, category)
        results = self.db_manager.search_prompts(query_conditions)

        # カテゴリ関連キーワードを抽出
        category_keywords = []
        for prompt_data in results:
            keywords = self.extract_category_keywords(
                prompt_data['full_prompt'], category
            )
            category_keywords.extend(keywords)

        # 重複除去と頻度順ソート
        unique_keywords = list(set(category_keywords))
        scored_keywords = self.score_keywords(unique_keywords, context)

        return sorted(scored_keywords, key=lambda x: x[1], reverse=True)
```

### StyleAnalyzer

```python
class StyleAnalyzer:
    def __init__(self):
        self.style_patterns = self.load_style_patterns()

    def get_style_patterns(self, style_name: str) -> Dict:
        """指定されたスタイルのパターンを取得"""
        return self.style_patterns.get(style_name, {})

    def load_style_patterns(self) -> Dict:
        """CivitAIデータから各スタイルのパターンを学習"""
        patterns = {
            'cinematic': {
                'lighting': ['cinematic lighting', 'dramatic lighting', 'volumetric lighting'],
                'composition': ['wide shot', 'close up', 'rule of thirds'],
                'quality': ['masterpiece', '8k', 'high quality'],
                'mood': ['dramatic', 'epic', 'cinematic'],
                'technical': ['depth of field', 'bokeh', 'film grain']
            },
            'anime': {
                'style': ['anime', 'manga', '2d', 'cel shading'],
                'quality': ['best quality', 'masterpiece', 'detailed'],
                'character': ['1girl', '1boy', 'cute', 'kawaii'],
                'technical': ['vibrant colors', 'clean lines']
            },
            # ... 他のスタイル定義
        }
        return patterns
```

## 🎯 統合ワークフロー例

### 基本的な使用パターン

```python
# ComfyUIワークフロー例
1. [Load Image] -> 2. [WD14_CivitAI_Enhanced_Tagger] -> 3. [Generate Image]
                           ↓
                  4. [Prompt_Quality_Enhancer] (オプション)
                           ↓
                  5. [Prompt_A_B_Tester] (品質確認)
```

### 高度な使用パターン

```python
# スタイル変換パイプライン
1. [Load Image] -> 2. [WD14 Tagger] -> 3. [CivitAI_Database_Search]
                                            ↓
                  4. [Prompt_Style_Transfer] -> 5. [Quality_Enhancer]
                                            ↓
                  6. [A_B_Tester] -> 7. [Generate Final Image]
```

## 🚀 実装スケジュール

### Week 1-2: 基盤構築
- WD14インターフェース作成
- CivitAIデータ準備
- 基本的な補強ロジック

### Week 3-4: ノード実装
- 5つのメインノード作成
- テスト・デバッグ
- 基本機能の動作確認

### Week 5-6: 高度化・最適化
- セマンティック検索追加
- スタイル分析の精度向上
- パフォーマンス最適化

### Week 7: 統合・配布
- ComfyUI統合テスト
- ドキュメント作成
- パッケージング・配布準備

## 💡 期待される効果

この実装により、WD14の基本的な出力が以下のように改善されます：

**Before**: `1girl, long hair, blue eyes, dress`

**After**: `masterpiece, best quality, 1girl, long hair, flowing hair, blue eyes, sparkling eyes, elegant dress, detailed fabric, standing gracefully, soft lighting, golden hour, bokeh background, depth of field, professional photography, 8k resolution`

**改善率**: 表現の豊富さ約300%向上、技術的品質向上、アート性大幅向上
