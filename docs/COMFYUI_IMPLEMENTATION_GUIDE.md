# ComfyUI ノード実装ガイド

## 実装すべきノード一覧

### 必須ノード（Phase 1-2）

#### 1. CivitaiDataCollector
**目的**: CivitAI APIからプロンプトデータを収集
**実装ファイル**: `nodes/civitai_collector_node.py`

```python
class CivitaiDataCollectorNode:
    """CivitAI APIからプロンプト・画像メタデータを収集"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "モデルID (例: 101055)"
                }),
                "version_id": ("STRING", {
                    "default": "",
                    "multiline": False, 
                    "placeholder": "バージョンID (例: 128078)"
                }),
                "max_items": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 5000,
                    "step": 1
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "CivitAI API Key (オプション)"
                })
            },
            "optional": {
                "model_name": ("STRING", {"default": ""}),
                "strict_version_match": ("BOOLEAN", {"default": False}),
                "quality_filter": ("BOOLEAN", {"default": True}),
                "min_reactions": ("INT", {"default": 0, "min": 0})
            }
        }
    
    RETURN_TYPES = ("PROMPT_DATASET", "COLLECTION_STATS")
    RETURN_NAMES = ("dataset", "stats")
    FUNCTION = "collect_prompts"
    CATEGORY = "CivitAI/Collection"
    
    def collect_prompts(self, model_id, version_id, max_items, api_key, **kwargs):
        # collector.py のロジックを使用
        pass
```

#### 2. PromptClassifier  
**目的**: プロンプトを7カテゴリに自動分類
**実装ファイル**: `nodes/prompt_classifier_node.py`

```python  
class PromptClassifierNode:
    """プロンプトを自動分類 (NSFW/style/lighting/composition/mood/basic/technical)"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_dataset": ("PROMPT_DATASET",),
                "target_categories": (["all", "style", "lighting", "composition", "mood", "basic", "technical", "nsfw"], {
                    "default": "all"
                }),
                "confidence_threshold": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1
                })
            }
        }
    
    RETURN_TYPES = ("CLASSIFIED_DATASET", "CATEGORY_DISTRIBUTION")
    RETURN_NAMES = ("classified", "distribution")
    FUNCTION = "classify_prompts"
    CATEGORY = "CivitAI/Analysis"
```

#### 3. PromptFilter
**目的**: 条件に基づくプロンプトフィルタリング
**実装ファイル**: `nodes/prompt_filter_node.py`

```python
class PromptFilterNode:
    """分類済みプロンプトをフィルタリング"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "classified_dataset": ("CLASSIFIED_DATASET",),
                "filter_category": (["all", "NSFW", "style", "lighting", "composition", "mood", "basic", "technical"], {
                    "default": "all"
                }),
                "min_quality_score": ("INT", {"default": 0, "min": 0, "max": 100}),
                "min_reactions": ("INT", {"default": 0, "min": 0}),
                "exclude_nsfw": ("BOOLEAN", {"default": False})
            },
            "optional": {
                "model_filter": ("STRING", {"default": ""}),
                "prompt_length_min": ("INT", {"default": 0}),
                "prompt_length_max": ("INT", {"default": 1000})
            }
        }
    
    RETURN_TYPES = ("FILTERED_DATASET",)
    FUNCTION = "filter_prompts" 
    CATEGORY = "CivitAI/Analysis"
```

#### 4. PromptSelector
**目的**: フィルタ済みデータから具体的なプロンプトを選択
**実装ファイル**: `nodes/prompt_selector_node.py`

```python
class PromptSelectorNode:
    """フィルタ済みデータセットからプロンプトを選択"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filtered_dataset": ("FILTERED_DATASET",),
                "selection_method": (["random", "top_quality", "top_reactions", "by_index", "latest"], {
                    "default": "random"
                }),
                "count": ("INT", {"default": 1, "min": 1, "max": 10}),
                "seed": ("INT", {"default": -1})
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "PROMPT_METADATA", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "metadata", "model_info")
    FUNCTION = "select_prompt"
    CATEGORY = "CivitAI/Output"
```

### 実用ノード（Phase 3）

#### 5. PromptAnalyzer
**目的**: データセット全体の統計分析
```python
class PromptAnalyzerNode:
    """プロンプトデータセットの詳細分析"""
    
    @classmethod  
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_dataset": ("PROMPT_DATASET",),
                "analysis_type": (["overview", "quality_distribution", "category_breakdown", "model_analysis", "keyword_frequency"], {
                    "default": "overview"
                })
            }
        }
    
    RETURN_TYPES = ("ANALYSIS_REPORT", "CHART_DATA")
    FUNCTION = "analyze_dataset"
    CATEGORY = "CivitAI/Analysis"
```

#### 6. PromptEnhancer
**目的**: 既存プロンプトの品質向上・拡張
```python
class PromptEnhancerNode:
    """プロンプトの自動拡張・品質向上"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_prompt": ("STRING", {"multiline": True}),
                "enhancement_style": (["quality_boost", "detail_add", "style_enhance", "technical_improve"], {
                    "default": "quality_boost"
                }),
                "reference_dataset": ("CLASSIFIED_DATASET",)
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "ENHANCEMENT_REPORT")
    RETURN_NAMES = ("enhanced_positive", "enhanced_negative", "report")
    FUNCTION = "enhance_prompt"
    CATEGORY = "CivitAI/Enhancement"
```

## カスタムデータ型定義

### データ型実装ファイル
**ファイル**: `civitai_data_types.py`

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

@dataclass
class PromptData:
    """個別プロンプトデータ"""
    civitai_id: str
    full_prompt: str
    negative_prompt: str
    model_name: str
    model_id: str
    model_version_id: str
    reaction_count: int
    comment_count: int
    download_count: int
    prompt_length: int
    tag_count: int
    quality_score: int
    collected_at: str
    resources: List[Dict[str, Any]]
    raw_metadata: str

@dataclass  
class ClassificationResult:
    """分類結果"""
    category: str
    confidence: float
    matched_keywords: List[str]

@dataclass
class PromptDataset:
    """プロンプトデータセット"""
    prompts: List[PromptData]
    metadata: Dict[str, Any]
    collection_info: Dict[str, Any]
    
    def __len__(self):
        return len(self.prompts)
    
    def filter_by_category(self, category: str) -> 'PromptDataset':
        # フィルタリング実装
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        # 統計情報生成
        pass

@dataclass
class ClassifiedDataset(PromptDataset):
    """分類済みプロンプトデータセット"""
    classifications: Dict[str, ClassificationResult]
    category_stats: Dict[str, Any]

# ComfyUIカスタムタイプ登録
def register_civitai_types():
    """ComfyUIにカスタムデータ型を登録"""
    
    # PROMPT_DATASET型
    class PromptDatasetType:
        @staticmethod
        def serialize(data: PromptDataset) -> str:
            return json.dumps({
                'prompts': [asdict(p) for p in data.prompts],
                'metadata': data.metadata,
                'collection_info': data.collection_info
            }, ensure_ascii=False)
        
        @staticmethod
        def deserialize(data_str: str) -> PromptDataset:
            data = json.loads(data_str)
            prompts = [PromptData(**p) for p in data['prompts']]
            return PromptDataset(
                prompts=prompts,
                metadata=data['metadata'], 
                collection_info=data['collection_info']
            )
    
    # ComfyUIへの型登録
    import comfy.model_management as model_management
    model_management.register_custom_type("PROMPT_DATASET", PromptDatasetType)
    model_management.register_custom_type("CLASSIFIED_DATASET", PromptDatasetType)
    model_management.register_custom_type("FILTERED_DATASET", PromptDatasetType)
```

## ノードパッケージ構造

```
comfyui_civitai_nodes/
├── __init__.py                    # ノード登録・初期化
├── civitai_data_types.py         # カスタムデータ型
├── civitai_core/                 # コアロジック（src/からコピー）
│   ├── __init__.py
│   ├── collector.py             # データ収集エンジン
│   ├── categorizer.py           # 自動分類システム
│   ├── database.py              # データベース管理
│   └── config.py                # 設定管理
├── nodes/                        # ComfyUIノード実装
│   ├── __init__.py
│   ├── base_node.py            # 基底ノードクラス
│   ├── civitai_collector_node.py
│   ├── prompt_classifier_node.py
│   ├── prompt_filter_node.py
│   ├── prompt_selector_node.py
│   ├── prompt_analyzer_node.py
│   └── prompt_enhancer_node.py
├── utils/                        # ユーティリティ
│   ├── __init__.py
│   ├── error_handler.py         # エラーハンドリング
│   ├── cache_manager.py         # キャッシュ管理
│   └── progress_tracker.py      # 進捗管理
├── web/                          # WebUI拡張
│   ├── civitai_nodes.css        # スタイルシート
│   └── civitai_nodes.js         # JavaScript拡張
├── examples/                     # サンプルワークフロー
│   ├── basic_collection.json
│   ├── advanced_analysis.json
│   └── prompt_enhancement.json
├── requirements.txt              # 依存関係
├── README.md                     # インストール・使用方法
└── setup.py                      # パッケージセットアップ
```

## インストール・セットアップ

### 1. ファイル配置方式
```bash
# ComfyUI custom_nodes ディレクトリに配置
git clone https://github.com/user/comfyui-civitai-nodes.git
cd ComfyUI/custom_nodes/comfyui-civitai-nodes
pip install -r requirements.txt
```

### 2. ノード登録方式
**ファイル**: `__init__.py`

```python
"""
ComfyUI CivitAI Nodes
CivitAI API integration for prompt collection and analysis
"""

from .civitai_data_types import register_civitai_types
from .nodes import (
    CivitaiDataCollectorNode,
    PromptClassifierNode,
    PromptFilterNode, 
    PromptSelectorNode,
    PromptAnalyzerNode,
    PromptEnhancerNode
)

# カスタムデータ型を登録
register_civitai_types()

# ノードマッピング
NODE_CLASS_MAPPINGS = {
    "CivitaiDataCollector": CivitaiDataCollectorNode,
    "PromptClassifier": PromptClassifierNode,
    "PromptFilter": PromptFilterNode,
    "PromptSelector": PromptSelectorNode, 
    "PromptAnalyzer": PromptAnalyzerNode,
    "PromptEnhancer": PromptEnhancerNode,
}

# ノード表示名
NODE_DISPLAY_NAME_MAPPINGS = {
    "CivitaiDataCollector": "CivitAI Data Collector",
    "PromptClassifier": "Prompt Classifier", 
    "PromptFilter": "Prompt Filter",
    "PromptSelector": "Prompt Selector",
    "PromptAnalyzer": "Prompt Analyzer",
    "PromptEnhancer": "Prompt Enhancer",
}

# メタ情報
__version__ = "1.0.0"
__author__ = "CivitAI Prompt Collector Team"
__description__ = "ComfyUI nodes for CivitAI prompt collection and analysis"

print(f"Loaded CivitAI Nodes v{__version__}")
```

## 実装優先順位

### Phase 1: 基盤構築（1-2週間）
1. **カスタムデータ型定義・登録**
2. **基底ノードクラス実装**
3. **エラーハンドリング機構**
4. **基本的なテストフレームワーク**

### Phase 2: コレクションノード（2-3週間）
1. **CivitaiDataCollector** - 基本収集機能
2. **PromptClassifier** - 分類機能
3. **PromptFilter** - フィルタリング機能
4. **PromptSelector** - 選択機能

### Phase 3: 分析・拡張ノード（1-2週間）
1. **PromptAnalyzer** - 分析機能
2. **PromptEnhancer** - 拡張機能
3. **UI/UX改善**

### Phase 4: 最適化・配布準備（1週間）
1. **パフォーマンス最適化**
2. **ドキュメント整備**
3. **サンプルワークフロー作成**
4. **配布パッケージ準備**

## 技術的考慮事項

### パフォーマンス最適化
- **非同期処理**: 大量データ収集時のUI応答性確保
- **キャッシング**: 収集データの効率的再利用
- **メモリ管理**: 大規模データセットの段階的処理

### エラーハンドリング  
- **API制限対応**: レート制限・タイムアウト処理
- **データ品質**: 不完全・破損データの適切な処理
- **ユーザビリティ**: 明確なエラーメッセージ・復旧手順

### 拡張性
- **プラグイン機構**: 新しい分析方法・フィルターの追加
- **設定管理**: ユーザー固有の設定・プリセット
- **API互換性**: CivitAI API変更への対応

この実装ガイドに従うことで、現在の堅牢なCivitAI Prompt Collectorを効果的にComfyUIエコシステムに統合できます。