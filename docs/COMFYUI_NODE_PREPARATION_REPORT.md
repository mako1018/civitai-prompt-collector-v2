# CivitAI Prompt Collector - ComfyUI ノード化準備レポート

## 概要

本プロジェクト「CivitAI Prompt Collector」は、CivitAI APIからプロンプトデータを収集・分析・可視化する包括的なシステムです。ComfyUIノード化に向けて、現在の実装を詳細分析し、ノード設計指針を策定します。

## プロジェクト全体構成

### 1. アーキテクチャ概要

```
civitai-prompt-collector-v2/
├── src/                    # コアロジック
│   ├── collector.py        # データ収集エンジン
│   ├── categorizer.py      # 自動分類システム
│   ├── database.py         # データベース管理
│   ├── config.py           # 設定管理
│   └── visualizer.py       # データ可視化
├── ui/                     # Streamlit WebUI
├── scripts/                # 実行スクリプト群
├── data/                   # SQLiteデータベース
└── logs/                   # ログ管理
```

### 2. データフロー

```
CivitAI API → Collector → Extractor → Database → Categorizer → UI/Visualization
     ↓           ↓           ↓          ↓           ↓            ↓
  画像/プロンプト  構造化     品質評価    SQLite保存   AI分類      ダッシュボード
```

## コアコンポーネント詳細分析

### 1. CivitaiPromptCollector (collector.py)

**責任範囲:**
- CivitAI API v1からのデータ取得
- 画像APIとプロンプトAPIの統合処理
- レート制限・リトライ機構
- メタデータ抽出・正規化

**主要クラス:**

#### `CivitaiAPIClient`
```python
# API呼び出し管理
- _get_headers(): 認証・エンコーディング処理
- get_model_meta(): モデルメタデータ取得
- get_images_page_info(): 画像ページ情報取得
- fetch_batch(): バッチデータ取得（リトライ機構付き）
```

**API エンドポイント対応:**
- `https://civitai.com/api/v1/images` - 画像メタデータ
- `https://civitai.com/api/v1/models/{id}` - モデル情報
- プロンプトAPI（カーソル方式）

#### `PromptDataExtractor`
```python
# データ正規化処理
- extract_prompt_data(): APIレスポンス → 構造化データ
- matches_version(): バージョンマッチング（厳密/柔軟）
- resource パース: civitaiResources の正規化
```

**抽出フィールド:**
```python
prompt_data = {
    "civitai_id": str,           # 一意識別子
    "full_prompt": str,          # メインプロンプト
    "negative_prompt": str,      # ネガティブプロンプト
    "reaction_count": int,       # リアクション数
    "comment_count": int,        # コメント数
    "download_count": int,       # ダウンロード数
    "model_name": str,           # モデル名
    "model_id": str,             # モデルID
    "model_version_id": str,     # バージョンID
    "raw_metadata": str,         # 生JSONメタデータ
    "resources": List[Dict],     # 使用リソース一覧
    "prompt_length": int,        # プロンプト長
    "tag_count": int,            # タグ数
    "quality_score": int,        # 品質スコア
    "collected_at": str          # 収集日時
}
```

#### `QualityScorer`
```python
# 品質評価アルゴリズム
def calculate_quality_score(prompt: str, stats: Dict) -> int:
    score = 0
    # 技術的キーワード（重み: 2）
    # 詳細キーワード（重み: 1）
    # リアクション数ボーナス
    # 適切な長さボーナス（15-80単語）
    return score
```

### 2. PromptCategorizer (categorizer.py)

**責任範囲:**
- 7カテゴリ自動分類（NSFW, style, lighting, composition, mood, basic, technical）
- キーワードベース分類エンジン
- 信頼度計算・マッチングアルゴリズム

**分類カテゴリ詳細:**

#### NSFW (175キーワード)
```python
# 成人向けコンテンツ検出
"nsfw", "explicit", "nude", "naked", "topless", "lingerie", "bikini",
"revealing", "exposed", "erotic", "sexual", "seductive", "provocative"...
```

#### Style (85キーワード)
```python
# アートスタイル・技法
"realistic", "photorealistic", "anime", "manga", "cartoon", "digital art",
"concept art", "watercolor", "oil painting", "3d render", "cinematic"...
```

#### Lighting (67キーワード)
```python
# ライティング・照明
"lighting", "natural light", "studio lighting", "soft light", "rim light",
"golden hour", "candlelight", "dramatic lighting", "volumetric lighting"...
```

#### Composition (58キーワード)
```python
# 構図・カメラアングル
"composition", "framing", "close up", "wide shot", "bird's eye view",
"rule of thirds", "depth of field", "portrait", "landscape"...
```

#### Mood (72キーワード)
```python
# 雰囲気・感情・トーン
"mood", "atmosphere", "happy", "sad", "mysterious", "scary", "romantic",
"dramatic", "nostalgic", "dreamy", "dark", "bright"...
```

#### Basic (45キーワード)
```python
# 基本品質用語
"masterpiece", "best quality", "detailed", "ultra detailed", "perfect",
"beautiful", "stunning", "professional", "award winning"...
```

#### Technical (89キーワード)
```python
# 技術仕様
"4k", "8k", "high resolution", "aspect ratio", "camera", "lens", "aperture",
"iso", "canon", "nikon", "dslr", "raw", "hdr"...
```

**分類アルゴリズム:**
```python
def classify(self, prompt: str) -> ClassificationResult:
    # 1. 前処理（クリーニング・正規化）
    # 2. カテゴリ別スコア計算
    # 3. 信頼度評価
    # 4. 最高スコアカテゴリ選択
    return ClassificationResult(category, confidence, matched_keywords)
```

### 3. DatabaseManager (database.py)

**責任範囲:**
- SQLiteデータベース管理
- CRUD操作・マイグレーション
- インデックス・制約管理

**テーブル設計:**

#### `civitai_prompts`（メインテーブル）
```sql
CREATE TABLE civitai_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civitai_id TEXT UNIQUE NOT NULL,
    full_prompt TEXT,
    negative_prompt TEXT,
    reaction_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    model_name TEXT,
    model_id TEXT,
    model_version_id TEXT,
    prompt_length INTEGER DEFAULT 0,
    tag_count INTEGER DEFAULT 0,
    quality_score INTEGER DEFAULT 0,
    raw_metadata TEXT,
    collected_at TEXT
)
```

#### `prompt_categories`（分類結果）
```sql
CREATE TABLE prompt_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    matched_keywords TEXT,
    FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
)
```

#### `prompt_resources`（リソース情報）
```sql
CREATE TABLE prompt_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    resource_index INTEGER,
    resource_type TEXT,
    resource_name TEXT,
    model_id TEXT,
    model_version_id TEXT,
    resource_id TEXT,
    raw_data TEXT,
    FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
)
```

#### `collection_state`（収集状態管理）
```sql
CREATE TABLE collection_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id TEXT UNIQUE,
    status TEXT DEFAULT 'idle',
    total_collected INTEGER DEFAULT 0,
    planned_total INTEGER,
    last_update TEXT,
    last_cursor TEXT,
    metadata TEXT
)
```

## ComfyUI ノード設計指針

### 1. ノード分割戦略

#### Core Collection Nodes

**A. CivitaiDataCollector**
```python
INPUT_TYPES = {
    "required": {
        "model_id": ("STRING", {"default": ""}),
        "version_id": ("STRING", {"default": ""}),
        "max_items": ("INT", {"default": 100, "min": 1, "max": 10000}),
        "api_key": ("STRING", {"default": ""}),
        "strict_version_match": ("BOOLEAN", {"default": False}),
    }
}
RETURN_TYPES = ("PROMPT_DATASET",)
FUNCTION = "collect_prompts"
```

**B. PromptClassifier**
```python
INPUT_TYPES = {
    "required": {
        "prompt_dataset": ("PROMPT_DATASET",),
        "target_categories": ("STRING", {"default": "all"}),
        "confidence_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
    }
}
RETURN_TYPES = ("CLASSIFIED_DATASET", "CATEGORY_STATS")
FUNCTION = "classify_prompts"
```

**C. PromptFilter**
```python
INPUT_TYPES = {
    "required": {
        "classified_dataset": ("CLASSIFIED_DATASET",),
        "filter_category": ("STRING", {"default": "all"}),
        "min_quality_score": ("INT", {"default": 0, "min": 0, "max": 100}),
        "min_reactions": ("INT", {"default": 0, "min": 0}),
        "exclude_nsfw": ("BOOLEAN", {"default": False}),
    }
}
RETURN_TYPES = ("FILTERED_DATASET",)
FUNCTION = "filter_prompts"
```

#### Analysis & Utility Nodes

**D. PromptAnalyzer**
```python
INPUT_TYPES = {
    "required": {
        "prompt_dataset": ("PROMPT_DATASET",),
        "analysis_type": (["quality", "categories", "models", "keywords"], {"default": "quality"}),
    }
}
RETURN_TYPES = ("ANALYSIS_RESULT", "STATISTICS")
FUNCTION = "analyze_dataset"
```

**E. PromptSelector**
```python
INPUT_TYPES = {
    "required": {
        "filtered_dataset": ("FILTERED_DATASET",),
        "selection_method": (["random", "top_quality", "top_reactions", "by_index"], {"default": "random"}),
        "count": ("INT", {"default": 1, "min": 1, "max": 100}),
        "seed": ("INT", {"default": 42}),
    }
}
RETURN_TYPES = ("STRING", "STRING", "PROMPT_DATA")  # positive, negative, metadata
FUNCTION = "select_prompt"
```

**F. PromptProcessor**
```python
INPUT_TYPES = {
    "required": {
        "prompt_text": ("STRING", {"multiline": True}),
        "operation": (["clean", "enhance", "extract_tags", "calculate_quality"], {"default": "clean"}),
        "enhancement_style": ("STRING", {"default": ""}),
    }
}
RETURN_TYPES = ("STRING", "FLOAT", "INT")  # processed_prompt, confidence, quality_score
FUNCTION = "process_prompt"
```

### 2. データ構造設計

#### Custom Data Types

**PROMPT_DATASET**
```python
class PromptDataset:
    def __init__(self):
        self.prompts: List[PromptData] = []
        self.metadata: Dict[str, Any] = {}
        self.collection_info: Dict[str, Any] = {}

class PromptData:
    civitai_id: str
    full_prompt: str
    negative_prompt: str
    model_info: ModelInfo
    stats: PromptStats
    quality_score: int
    resources: List[ResourceInfo]
    collected_at: datetime
```

**CLASSIFIED_DATASET**
```python
class ClassifiedDataset(PromptDataset):
    def __init__(self):
        super().__init__()
        self.classifications: Dict[str, ClassificationResult] = {}
        self.category_stats: Dict[str, CategoryStats] = {}
```

### 3. 実装アーキテクチャ

#### Node Base Class
```python
class CivitaiNodeBase:
    """全CivitAIノードの基底クラス"""
    
    @classmethod
    def INPUT_TYPES(cls):
        raise NotImplementedError
    
    @classmethod  
    def IS_CHANGED(cls, **kwargs):
        # キャッシュ制御
        return hash(str(kwargs))
    
    def __init__(self):
        self.collector = None
        self.categorizer = None
        self.db_manager = None
        
    def _init_components(self):
        """遅延初期化"""
        if not self.collector:
            from .civitai_core import CivitaiPromptCollector, PromptCategorizer, DatabaseManager
            self.collector = CivitaiPromptCollector()
            self.categorizer = PromptCategorizer() 
            self.db_manager = DatabaseManager()
```

#### Error Handling Strategy
```python
class CivitaiError(Exception):
    """CivitAI関連エラーの基底クラス"""
    pass

class APIRateLimitError(CivitaiError):
    """レート制限エラー"""
    pass

class DataExtractionError(CivitaiError):
    """データ抽出エラー"""
    pass

def safe_execute(func):
    """エラーハンドリングデコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CivitaiError as e:
            return {"error": str(e), "data": None}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "data": None}
    return wrapper
```

### 4. 最適化戦略

#### Performance Optimizations
- **キャッシング**: 収集データのローカルキャッシュ
- **バッチ処理**: 大量データの効率的処理
- **非同期処理**: APIコール・DB操作の並列化
- **インクリメンタル更新**: 差分収集機能

#### Memory Management
- **ジェネレータ使用**: 大量データの段階的処理
- **データページング**: メモリ効率的なデータローディング
- **キャッシュ制限**: LRU/TTLキャッシュによる制御

#### User Experience
- **プログレス表示**: 長時間処理の進捗可視化
- **エラーリカバリ**: 部分失敗からの復旧機能
- **プリセット管理**: 一般的設定の保存・復元

## 実装ロードマップ

### Phase 1: Core Infrastructure
1. **基底ノードクラス実装**
2. **データ型定義・シリアライゼーション**
3. **エラーハンドリング機構**

### Phase 2: Essential Collection Nodes
1. **CivitaiDataCollector** - 基本収集機能
2. **PromptClassifier** - 分類機能
3. **PromptFilter** - フィルタリング機能

### Phase 3: Analysis & Utility Nodes
1. **PromptAnalyzer** - 分析機能
2. **PromptSelector** - 選択機能
3. **PromptProcessor** - 処理機能

### Phase 4: Advanced Features
1. **BatchCollector** - バッチ処理ノード
2. **DataExporter** - エクスポート機能
3. **ModelComparator** - モデル比較機能

### Phase 5: Integration & Polish
1. **UI/UX最適化**
2. **パフォーマンス最適化**
3. **ドキュメント・例完備**

## 技術的制約・考慮事項

### API制限
- **レート制限**: 1000req/hour (推定)
- **データ制限**: 大量収集時のタイムアウト
- **認証**: API Key必須（オプション機能向上）

### データ品質
- **不完全データ**: APIレスポンスの欠損対応
- **ノイズ除去**: 低品質プロンプトのフィルタリング
- **重複除去**: civitai_id での重複検出

### ComfyUI Integration
- **ノード間通信**: カスタムデータ型の適切な伝達
- **UI互換性**: 既存ComfyUIワークフローとの親和性
- **パッケージング**: インストール・配布の簡素化

## 結論

現在のCivitAI Prompt Collectorは、堅牢なデータ収集・分析・分類システムとして完成しています。ComfyUIノード化により、AI画像生成ワークフローへの直接統合が可能になり、以下の価値を提供します：

1. **リアルタイムプロンプト収集**: 最新トレンドの即座な取得
2. **インテリジェント分類**: 自動カテゴライゼーション
3. **品質ベース選択**: 高品質プロンプトの自動選出
4. **ワークフロー統合**: 既存ComfyUI環境でのシームレス利用

この基盤により、AI画像生成コミュニティに対して包括的で使いやすいプロンプト管理ソリューションを提供できます。

---
*Report generated: 2025-10-01*
*Project: CivitAI Prompt Collector v2*