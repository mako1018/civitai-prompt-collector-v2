# ComfyUI CivitAI Nodes 技術仕様書

## 1. ノード実装詳細例

### CivitaiDataCollectorNode 完全実装例

```python
# nodes/civitai_collector_node.py

import asyncio
import threading
from typing import Dict, Any, Tuple, Optional
import json
from pathlib import Path

from ..civitai_core.collector import CivitaiPromptCollector, CivitaiAPIClient
from ..civitai_core.database import DatabaseManager
from ..civitai_data_types import PromptDataset, PromptData
from .base_node import CivitaiNodeBase

class CivitaiDataCollectorNode(CivitaiNodeBase):
    """
    CivitAI APIからプロンプトデータを収集するメインノード

    機能:
    - モデルID/バージョンID指定での収集
    - リアルタイム進捗表示
    - 品質フィルタリング
    - 自動リトライ機構
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "モデルID (例: 101055) または空文字"
                }),
                "version_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "バージョンID (例: 128078) - 推奨"
                }),
                "max_items": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 5000,
                    "step": 1,
                    "tooltip": "収集する最大アイテム数"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "CivitAI API Key (オプション - 制限緩和)"
                })
            },
            "optional": {
                "model_name": ("STRING", {
                    "default": "",
                    "placeholder": "モデル名（表示用）"
                }),
                "strict_version_match": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "厳密なバージョンマッチング（checkpointのみ）"
                }),
                "quality_filter": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "低品質プロンプトを除外"
                }),
                "min_reactions": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100,
                    "tooltip": "最小リアクション数"
                }),
                "use_cache": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "ローカルキャッシュを使用"
                })
            }
        }

    RETURN_TYPES = ("PROMPT_DATASET", "COLLECTION_STATS", "STRING")
    RETURN_NAMES = ("dataset", "stats", "summary")
    OUTPUT_NODE = False

    FUNCTION = "collect_prompts"
    CATEGORY = "CivitAI/Collection"

    DESCRIPTION = """
    CivitAI APIからプロンプトデータを収集します。

    使用方法:
    1. version_id を指定（推奨）
    2. max_items で収集数を制限
    3. API Key で制限緩和（オプション）

    注意: 大量収集は時間がかかります
    """

    def __init__(self):
        super().__init__()
        self.collector = None
        self.db_manager = None
        self._progress_callback = None

    def _init_components(self, api_key: str = ""):
        """コンポーネントの遅延初期化"""
        if not self.collector:
            api_client = CivitaiAPIClient(api_key=api_key if api_key else None)
            self.collector = CivitaiPromptCollector(api_client)
        if not self.db_manager:
            self.db_manager = DatabaseManager()

    def _validate_inputs(self, model_id: str, version_id: str, max_items: int) -> Tuple[bool, str]:
        """入力パラメータの検証"""

        # 少なくともmodel_id または version_id が必要
        if not model_id.strip() and not version_id.strip():
            return False, "model_id または version_id のいずれかを指定してください"

        # max_items の範囲チェック
        if not (1 <= max_items <= 5000):
            return False, f"max_items は 1-5000 の範囲で指定してください (現在: {max_items})"

        # version_id の形式チェック（数値推奨）
        if version_id.strip() and not version_id.strip().isdigit():
            return True, f"警告: version_id '{version_id}' は数値ではありません"

        return True, "OK"

    def _estimate_collection_time(self, max_items: int) -> str:
        """収集時間の概算"""
        # API制限を考慮した概算（1.2秒/ページ, 100アイテム/ページ）
        pages = (max_items + 99) // 100
        estimated_seconds = pages * 1.2

        if estimated_seconds < 60:
            return f"約 {int(estimated_seconds)} 秒"
        else:
            return f"約 {int(estimated_seconds / 60)} 分"

    def collect_prompts(
        self,
        model_id: str,
        version_id: str,
        max_items: int,
        api_key: str,
        model_name: str = "",
        strict_version_match: bool = False,
        quality_filter: bool = True,
        min_reactions: int = 0,
        use_cache: bool = True
    ) -> Tuple[PromptDataset, Dict[str, Any], str]:
        """
        メインの収集処理

        Returns:
            Tuple[PromptDataset, Dict[str, Any], str]: データセット, 統計情報, サマリー文字列
        """

        # 1. 入力検証
        is_valid, message = self._validate_inputs(model_id, version_id, max_items)
        if not is_valid:
            raise ValueError(message)

        # 2. コンポーネント初期化
        self._init_components(api_key)

        # 3. 収集前の準備
        target_id = version_id.strip() if version_id.strip() else model_id.strip()
        collection_target = "version" if version_id.strip() else "model"
        estimated_time = self._estimate_collection_time(max_items)

        print(f"[CivitAI] 収集開始: {collection_target}={target_id}, max={max_items} ({estimated_time})")

        try:
            # 4. データ収集実行
            collection_result = self.collector.collect_dataset(
                model_id=target_id,
                model_name=model_name if model_name else None,
                max_items=max_items
            )

            # 5. 品質フィルタリング（オプション）
            valid_prompts = []
            for prompt_data in collection_result["items"]:
                # 品質フィルター適用
                if quality_filter:
                    if prompt_data.get("quality_score", 0) < 5:
                        continue
                    if not prompt_data.get("full_prompt", "").strip():
                        continue

                # リアクション数フィルター
                if prompt_data.get("reaction_count", 0) < min_reactions:
                    continue

                # PromptData オブジェクト作成
                prompt_obj = PromptData(
                    civitai_id=prompt_data.get("civitai_id", ""),
                    full_prompt=prompt_data.get("full_prompt", ""),
                    negative_prompt=prompt_data.get("negative_prompt", ""),
                    model_name=prompt_data.get("model_name", ""),
                    model_id=prompt_data.get("model_id", ""),
                    model_version_id=prompt_data.get("model_version_id", ""),
                    reaction_count=prompt_data.get("reaction_count", 0),
                    comment_count=prompt_data.get("comment_count", 0),
                    download_count=prompt_data.get("download_count", 0),
                    prompt_length=prompt_data.get("prompt_length", 0),
                    tag_count=prompt_data.get("tag_count", 0),
                    quality_score=prompt_data.get("quality_score", 0),
                    collected_at=prompt_data.get("collected_at", ""),
                    resources=prompt_data.get("resources", []),
                    raw_metadata=prompt_data.get("raw_metadata", "{}")
                )
                valid_prompts.append(prompt_obj)

            # 6. データセット構築
            dataset = PromptDataset(
                prompts=valid_prompts,
                metadata={
                    "collection_target": collection_target,
                    "target_id": target_id,
                    "model_name": model_name,
                    "collection_timestamp": collection_result.get("timestamp"),
                    "filters_applied": {
                        "quality_filter": quality_filter,
                        "min_reactions": min_reactions,
                        "strict_version_match": strict_version_match
                    }
                },
                collection_info={
                    "total_fetched": collection_result.get("collected", 0),
                    "total_valid": len(valid_prompts),
                    "estimated_time": estimated_time,
                    "actual_time": collection_result.get("elapsed_time"),
                    "api_source": "CivitAI v1"
                }
            )

            # 7. 統計情報生成
            stats = self._generate_collection_stats(dataset, collection_result)

            # 8. サマリー文字列生成
            summary = self._generate_summary(dataset, stats)

            print(f"[CivitAI] 収集完了: {len(valid_prompts)} 件のプロンプトを取得")

            return (dataset, stats, summary)

        except Exception as e:
            error_msg = f"収集エラー: {str(e)}"
            print(f"[CivitAI] {error_msg}")

            # エラー時も空のデータセットを返す
            empty_dataset = PromptDataset(
                prompts=[],
                metadata={"error": error_msg},
                collection_info={"status": "failed"}
            )
            error_stats = {"status": "error", "message": error_msg}

            return (empty_dataset, error_stats, error_msg)

    def _generate_collection_stats(self, dataset: PromptDataset, raw_result: Dict) -> Dict[str, Any]:
        """収集統計情報を生成"""

        prompts = dataset.prompts

        if not prompts:
            return {
                "total_prompts": 0,
                "status": "no_data"
            }

        # 品質スコア分布
        quality_scores = [p.quality_score for p in prompts]

        # モデル分布
        models = {}
        for p in prompts:
            model = p.model_name or "Unknown"
            models[model] = models.get(model, 0) + 1

        # プロンプト長分布
        lengths = [p.prompt_length for p in prompts]

        return {
            "total_prompts": len(prompts),
            "quality_stats": {
                "min": min(quality_scores),
                "max": max(quality_scores),
                "avg": sum(quality_scores) / len(quality_scores)
            },
            "length_stats": {
                "min": min(lengths),
                "max": max(lengths),
                "avg": sum(lengths) / len(lengths)
            },
            "model_distribution": models,
            "collection_efficiency": len(prompts) / raw_result.get("collected", 1),
            "status": "success"
        }

    def _generate_summary(self, dataset: PromptDataset, stats: Dict[str, Any]) -> str:
        """人間向けサマリー文字列を生成"""

        if stats.get("status") == "error":
            return f"❌ 収集失敗: {stats.get('message', 'Unknown error')}"

        if stats.get("status") == "no_data":
            return "⚠️ データが収集されませんでした"

        total = stats.get("total_prompts", 0)
        avg_quality = stats.get("quality_stats", {}).get("avg", 0)
        models = len(stats.get("model_distribution", {}))

        summary = f"✅ 収集完了: {total} 件のプロンプト\n"
        summary += f"📊 平均品質スコア: {avg_quality:.1f}\n"
        summary += f"🎨 モデル数: {models}\n"

        if dataset.metadata.get("filters_applied"):
            filters = dataset.metadata["filters_applied"]
            if filters.get("quality_filter"):
                summary += "🔍 品質フィルター: 有効\n"
            if filters.get("min_reactions", 0) > 0:
                summary += f"👍 最小リアクション: {filters['min_reactions']}\n"

        return summary.strip()

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """キャッシュ制御 - 入力パラメータが変わった場合のみ再実行"""
        cache_key = f"{kwargs.get('model_id', '')}_{kwargs.get('version_id', '')}_{kwargs.get('max_items', 0)}"
        return hash(cache_key)


# 使用例ワークフロー JSON
EXAMPLE_WORKFLOW = {
    "nodes": {
        "1": {
            "id": 1,
            "type": "CivitaiDataCollector",
            "pos": [100, 100],
            "size": [400, 300],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {"name": "dataset", "type": "PROMPT_DATASET", "links": [1]},
                {"name": "stats", "type": "COLLECTION_STATS", "links": [2]},
                {"name": "summary", "type": "STRING", "links": [3]}
            ],
            "properties": {},
            "widgets_values": [
                "",        # model_id
                "128078",  # version_id
                100,       # max_items
                "",        # api_key
                "Realistic Vision",  # model_name
                False,     # strict_version_match
                True,      # quality_filter
                5,         # min_reactions
                True       # use_cache
            ]
        }
    },
    "links": [
        [1, 1, 0, 2, 0, "PROMPT_DATASET"],
        [2, 1, 1, 3, 0, "COLLECTION_STATS"],
        [3, 1, 2, 4, 0, "STRING"]
    ],
    "groups": [],
    "config": {},
    "extra": {},
    "version": 0.4
}
```

## 2. データ型シリアライゼーション実装

```python
# civitai_data_types.py

import json
import pickle
import base64
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime

@dataclass
class PromptData:
    """個別プロンプトデータ - ComfyUI間の効率的な転送を考慮"""

    # Core identification
    civitai_id: str
    full_prompt: str
    negative_prompt: str = ""

    # Model information
    model_name: str = ""
    model_id: str = ""
    model_version_id: str = ""

    # Engagement metrics
    reaction_count: int = 0
    comment_count: int = 0
    download_count: int = 0

    # Derived metrics
    prompt_length: int = 0
    tag_count: int = 0
    quality_score: int = 0

    # Metadata
    collected_at: str = ""
    resources: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: str = "{}"

    def __post_init__(self):
        """自動計算フィールドの設定"""
        if not self.prompt_length:
            self.prompt_length = len(self.full_prompt)
        if not self.tag_count and self.full_prompt:
            self.tag_count = len([t for t in self.full_prompt.split(',') if t.strip()])

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON serializable）"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptData':
        """辞書から復元"""
        return cls(**data)

    def get_tags(self) -> List[str]:
        """プロンプトからタグリストを抽出"""
        return [tag.strip() for tag in self.full_prompt.split(',') if tag.strip()]

    def matches_keywords(self, keywords: List[str]) -> bool:
        """指定キーワードとのマッチング判定"""
        text = (self.full_prompt + " " + self.negative_prompt).lower()
        return any(keyword.lower() in text for keyword in keywords)


class PromptDataset:
    """プロンプトデータセット - ComfyUIでの効率的な処理を考慮"""

    def __init__(
        self,
        prompts: List[PromptData] = None,
        metadata: Dict[str, Any] = None,
        collection_info: Dict[str, Any] = None
    ):
        self.prompts = prompts or []
        self.metadata = metadata or {}
        self.collection_info = collection_info or {}
        self._cache = {}  # 計算結果キャッシュ

    def __len__(self) -> int:
        return len(self.prompts)

    def __iter__(self):
        return iter(self.prompts)

    def __getitem__(self, index: Union[int, slice]) -> Union[PromptData, 'PromptDataset']:
        if isinstance(index, slice):
            return PromptDataset(
                prompts=self.prompts[index],
                metadata=self.metadata.copy(),
                collection_info=self.collection_info.copy()
            )
        return self.prompts[index]

    # ComfyUI シリアライゼーション
    def serialize(self) -> str:
        """ComfyUI間転送用のシリアライゼーション"""
        data = {
            'prompts': [p.to_dict() for p in self.prompts],
            'metadata': self.metadata,
            'collection_info': self.collection_info,
            'version': '1.0'
        }
        return base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('ascii')

    @classmethod
    def deserialize(cls, data_str: str) -> 'PromptDataset':
        """シリアライズされたデータからの復元"""
        try:
            json_str = base64.b64decode(data_str.encode('ascii')).decode('utf-8')
            data = json.loads(json_str)

            prompts = [PromptData.from_dict(p) for p in data.get('prompts', [])]
            return cls(
                prompts=prompts,
                metadata=data.get('metadata', {}),
                collection_info=data.get('collection_info', {})
            )
        except Exception as e:
            print(f"[CivitAI] デシリアライゼーションエラー: {e}")
            return cls()  # 空のデータセット返却

    # データ操作メソッド
    def filter_by_quality(self, min_score: int) -> 'PromptDataset':
        """品質スコアによるフィルタリング"""
        filtered_prompts = [p for p in self.prompts if p.quality_score >= min_score]
        return PromptDataset(
            prompts=filtered_prompts,
            metadata=self._add_filter_metadata("quality_filter", {"min_score": min_score}),
            collection_info=self.collection_info.copy()
        )

    def filter_by_reactions(self, min_reactions: int) -> 'PromptDataset':
        """リアクション数によるフィルタリング"""
        filtered_prompts = [p for p in self.prompts if p.reaction_count >= min_reactions]
        return PromptDataset(
            prompts=filtered_prompts,
            metadata=self._add_filter_metadata("reaction_filter", {"min_reactions": min_reactions}),
            collection_info=self.collection_info.copy()
        )

    def filter_by_keywords(self, keywords: List[str], exclude: bool = False) -> 'PromptDataset':
        """キーワードによるフィルタリング"""
        if exclude:
            filtered_prompts = [p for p in self.prompts if not p.matches_keywords(keywords)]
        else:
            filtered_prompts = [p for p in self.prompts if p.matches_keywords(keywords)]

        return PromptDataset(
            prompts=filtered_prompts,
            metadata=self._add_filter_metadata("keyword_filter", {"keywords": keywords, "exclude": exclude}),
            collection_info=self.collection_info.copy()
        )

    def sample(self, count: int, method: str = "random", seed: int = None) -> 'PromptDataset':
        """データサンプリング"""
        import random

        if seed is not None:
            random.seed(seed)

        if method == "random":
            sampled = random.sample(self.prompts, min(count, len(self.prompts)))
        elif method == "top_quality":
            sampled = sorted(self.prompts, key=lambda p: p.quality_score, reverse=True)[:count]
        elif method == "top_reactions":
            sampled = sorted(self.prompts, key=lambda p: p.reaction_count, reverse=True)[:count]
        else:
            sampled = self.prompts[:count]

        return PromptDataset(
            prompts=sampled,
            metadata=self._add_filter_metadata("sample", {"count": count, "method": method, "seed": seed}),
            collection_info=self.collection_info.copy()
        )

    def get_statistics(self) -> Dict[str, Any]:
        """データセット統計情報を取得（キャッシュ付き）"""
        cache_key = "statistics"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.prompts:
            stats = {"total": 0, "status": "empty"}
        else:
            quality_scores = [p.quality_score for p in self.prompts]
            reaction_counts = [p.reaction_count for p in self.prompts]
            prompt_lengths = [p.prompt_length for p in self.prompts]

            # モデル分布
            model_dist = {}
            for p in self.prompts:
                model = p.model_name or "Unknown"
                model_dist[model] = model_dist.get(model, 0) + 1

            stats = {
                "total": len(self.prompts),
                "quality_stats": {
                    "min": min(quality_scores),
                    "max": max(quality_scores),
                    "avg": sum(quality_scores) / len(quality_scores),
                    "distribution": self._get_distribution(quality_scores, bins=10)
                },
                "reaction_stats": {
                    "min": min(reaction_counts),
                    "max": max(reaction_counts),
                    "avg": sum(reaction_counts) / len(reaction_counts),
                    "distribution": self._get_distribution(reaction_counts, bins=10)
                },
                "length_stats": {
                    "min": min(prompt_lengths),
                    "max": max(prompt_lengths),
                    "avg": sum(prompt_lengths) / len(prompt_lengths)
                },
                "model_distribution": model_dist,
                "status": "complete"
            }

        self._cache[cache_key] = stats
        return stats

    def _add_filter_metadata(self, filter_name: str, filter_params: Dict[str, Any]) -> Dict[str, Any]:
        """フィルター適用履歴をメタデータに追加"""
        new_metadata = self.metadata.copy()
        filters = new_metadata.setdefault("applied_filters", [])
        filters.append({
            "filter": filter_name,
            "params": filter_params,
            "timestamp": datetime.now().isoformat()
        })
        return new_metadata

    def _get_distribution(self, values: List[int], bins: int = 10) -> Dict[str, int]:
        """値の分布を計算"""
        if not values:
            return {}

        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {str(min_val): len(values)}

        bin_size = (max_val - min_val) / bins
        distribution = {}

        for i in range(bins):
            bin_min = min_val + i * bin_size
            bin_max = min_val + (i + 1) * bin_size
            bin_key = f"{int(bin_min)}-{int(bin_max)}"

            if i == bins - 1:  # 最後のビン
                count = len([v for v in values if bin_min <= v <= bin_max])
            else:
                count = len([v for v in values if bin_min <= v < bin_max])

            if count > 0:
                distribution[bin_key] = count

        return distribution


# ComfyUI カスタム型登録
def register_civitai_types():
    """ComfyUIにカスタムデータ型を登録"""

    try:
        # ComfyUI の型システムに登録
        import comfy.model_management as mm

        # PROMPT_DATASET 型の定義
        class PromptDatasetType:
            @staticmethod
            def serialize(obj: PromptDataset) -> str:
                return obj.serialize()

            @staticmethod
            def deserialize(data: str) -> PromptDataset:
                return PromptDataset.deserialize(data)

            @staticmethod
            def validate(obj) -> bool:
                return isinstance(obj, PromptDataset)

        # 型登録
        mm.register_custom_type("PROMPT_DATASET", PromptDatasetType)
        mm.register_custom_type("CLASSIFIED_DATASET", PromptDatasetType)  # 同じ基底クラス
        mm.register_custom_type("FILTERED_DATASET", PromptDatasetType)   # 同じ基底クラス

        print("[CivitAI] カスタムデータ型を登録しました")

    except ImportError:
        print("[CivitAI] 警告: ComfyUI環境外での実行 - 型登録をスキップ")
    except Exception as e:
        print(f"[CivitAI] 型登録エラー: {e}")


# 型登録を実行
register_civitai_types()
```

## 3. エラーハンドリング・ロバストネス実装

```python
# utils/error_handler.py

import functools
import time
import logging
from typing import Any, Callable, Optional, Dict
from enum import Enum

class CivitaiErrorType(Enum):
    """エラー種別"""
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    API_AUTH = "api_auth"
    API_NOT_FOUND = "api_not_found"
    DATA_INVALID = "data_invalid"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"

class CivitaiError(Exception):
    """CivitAI関連エラーの基底クラス"""

    def __init__(self, message: str, error_type: CivitaiErrorType, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.timestamp = time.time()

class APIRateLimitError(CivitaiError):
    """API制限エラー"""
    def __init__(self, message: str = "API rate limit exceeded", retry_after: int = None):
        super().__init__(message, CivitaiErrorType.API_RATE_LIMIT, {"retry_after": retry_after})

class APITimeoutError(CivitaiError):
    """API timeout エラー"""
    def __init__(self, message: str = "API request timed out", timeout: float = None):
        super().__init__(message, CivitaiErrorType.API_TIMEOUT, {"timeout": timeout})

class DataValidationError(CivitaiError):
    """データ検証エラー"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, CivitaiErrorType.DATA_INVALID, {"field": field, "value": value})

def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """リトライ機構付きデコレータ"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        # 最後の試行でも失敗
                        break

                    # レート制限の場合は待機時間を調整
                    if isinstance(e, APIRateLimitError):
                        wait_time = e.details.get("retry_after", delay * (backoff ** attempt))
                    else:
                        wait_time = delay * (backoff ** attempt)

                    print(f"[Retry] Attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                    print(f"[Retry] Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)

            # すべての試行が失敗
            raise last_exception

        return wrapper
    return decorator

def safe_execute(default_return: Any = None, log_errors: bool = True):
    """安全実行デコレータ - エラー時にデフォルト値を返す"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logging.error(f"Error in {func.__name__}: {e}", exc_info=True)

                # ComfyUI ノード用のエラー戻り値
                if isinstance(default_return, tuple):
                    return default_return
                else:
                    return (default_return, {"error": str(e), "function": func.__name__})

        return wrapper
    return decorator

class CivitaiErrorHandler:
    """統合エラーハンドラー"""

    def __init__(self):
        self.error_history = []
        self.max_history = 100

    def handle_api_error(self, response_code: int, response_text: str = "") -> CivitaiError:
        """API レスポンスエラーの処理"""

        if response_code == 429:
            # Rate limit
            retry_after = self._extract_retry_after(response_text)
            error = APIRateLimitError(retry_after=retry_after)
        elif response_code == 401:
            # Authentication
            error = CivitaiError("API authentication failed", CivitaiErrorType.API_AUTH)
        elif response_code == 404:
            # Not found
            error = CivitaiError("Resource not found", CivitaiErrorType.API_NOT_FOUND)
        elif response_code >= 500:
            # Server error
            error = CivitaiError(f"Server error: {response_code}", CivitaiErrorType.API_TIMEOUT)
        else:
            # Unknown error
            error = CivitaiError(f"API error: {response_code}", CivitaiErrorType.UNKNOWN_ERROR)

        self._log_error(error)
        return error

    def handle_network_error(self, original_error: Exception) -> CivitaiError:
        """ネットワークエラーの処理"""

        error_msg = str(original_error)

        if "timeout" in error_msg.lower():
            error = APITimeoutError()
        elif "connection" in error_msg.lower():
            error = CivitaiError("Network connection error", CivitaiErrorType.NETWORK_ERROR)
        else:
            error = CivitaiError(f"Network error: {error_msg}", CivitaiErrorType.NETWORK_ERROR)

        self._log_error(error)
        return error

    def validate_input(self, value: Any, field_name: str, validator: Callable[[Any], bool], error_message: str = None) -> None:
        """入力値検証"""

        if not validator(value):
            message = error_message or f"Invalid value for {field_name}: {value}"
            raise DataValidationError(message, field=field_name, value=value)

    def get_user_friendly_message(self, error: CivitaiError) -> str:
        """ユーザー向けエラーメッセージ生成"""

        if error.error_type == CivitaiErrorType.API_RATE_LIMIT:
            retry_after = error.details.get("retry_after")
            if retry_after:
                return f"⏳ API制限に達しました。{retry_after}秒後に再試行してください。"
            else:
                return "⏳ API制限に達しました。しばらく待ってから再試行してください。"

        elif error.error_type == CivitaiErrorType.API_AUTH:
            return "🔑 API認証に失敗しました。APIキーを確認してください。"

        elif error.error_type == CivitaiErrorType.API_NOT_FOUND:
            return "❓ 指定されたリソースが見つかりません。IDを確認してください。"

        elif error.error_type == CivitaiErrorType.API_TIMEOUT:
            return "⏱️ API接続がタイムアウトしました。ネット接続を確認してください。"

        elif error.error_type == CivitaiErrorType.DATA_INVALID:
            field = error.details.get("field", "不明なフィールド")
            return f"📝 入力エラー: {field} の値が無効です。"

        elif error.error_type == CivitaiErrorType.NETWORK_ERROR:
            return "🌐 ネットワークエラーが発生しました。接続を確認してください。"

        else:
            return f"❌ エラーが発生しました: {str(error)}"

    def _extract_retry_after(self, response_text: str) -> Optional[int]:
        """レスポンスから retry-after 値を抽出"""
        # 実装: ヘッダーまたはレスポンスボディから抽出
        return None

    def _log_error(self, error: CivitaiError) -> None:
        """エラーログ記録"""
        self.error_history.append({
            "error": error,
            "timestamp": error.timestamp,
            "type": error.error_type.value,
            "message": str(error)
        })

        # 履歴サイズ制限
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]

# グローバルエラーハンドラーインスタンス
error_handler = CivitaiErrorHandler()

# 便利なデコレータ
def robust_api_call(func: Callable) -> Callable:
    """API コール用のロバストデコレータ"""

    @with_retry(max_retries=3, delay=2.0, exceptions=(APIRateLimitError, APITimeoutError))
    @safe_execute(default_return=(None, {"error": "API call failed"}))
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
```

この技術仕様書により、現在のCivitAI Prompt Collectorを効率的かつ堅牢なComfyUIノードとして実装するための具体的なガイドラインが提供されます。実装時は、段階的なアプローチを取り、各フェーズでテストとユーザーフィードバックを重視することが重要です。
