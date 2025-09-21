#!/usr/bin/env python3
"""
CivitAI Prompt Collector - メイン収集ロジック
API呼び出し、データ抽出、品質スコア計算を担当
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from src.config import (
    CIVITAI_API_KEY, USER_AGENT, API_BASE_URL,
    REQUEST_TIMEOUT, RETRY_DELAY, RATE_LIMIT_WAIT,
    QUALITY_KEYWORDS
)


class CivitaiAPIClient:
    """CivitAI API呼び出しを管理するクライアント"""

    def __init__(self, api_key: str = CIVITAI_API_KEY, user_agent: str = USER_AGENT):
        self.api_key = api_key
        self.user_agent = user_agent
        self.base_url = API_BASE_URL

    def _get_headers(self) -> Dict[str, str]:
        """APIリクエスト用ヘッダーを生成"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Latin-1エンコーディング対応
        safe_headers = {}
        for k, v in headers.items():
            try:
                v.encode("latin-1")
                safe_headers[k] = v
            except UnicodeEncodeError:
                safe_headers[k] = v.encode("latin-1", "replace").decode("latin-1")
                print(f"[API] Header {k} contains non-Latin1 characters, sanitized")

        return safe_headers

    def fetch_batch(self, url_or_params, max_retries: int = 3) -> Tuple[List[Dict], Optional[str]]:
        """APIから1ページ分のデータを取得"""
        headers = self._get_headers()

        for attempt in range(1, max_retries + 1):
            try:
                if isinstance(url_or_params, dict):
                    response = requests.get(
                        self.base_url,
                        params=url_or_params,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT
                    )
                else:
                    response = requests.get(
                        url_or_params,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT
                    )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    next_page = data.get("metadata", {}).get("nextPage")
                    return items, next_page

                elif response.status_code == 429:
                    print(f"[API] Rate limited. Waiting {RATE_LIMIT_WAIT}s... (attempt {attempt}/{max_retries})")
                    time.sleep(RATE_LIMIT_WAIT)
                    continue

                else:
                    print(f"[API] HTTP {response.status_code}: {response.text[:200]}")
                    return [], None

            except requests.exceptions.RequestException as e:
                print(f"[API] Attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY * attempt)
                continue

        print(f"[API] All retries failed for: {url_or_params}")
        return [], None


class PromptDataExtractor:
    """APIレスポンスからプロンプトデータを抽出"""

    @staticmethod
    def extract_prompt_data(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """API レスポンス項目から必要フィールドを抽出"""
        try:
            meta = item.get("meta", {}) or {}
            stats = item.get("stats", {}) or {}

            full_prompt = meta.get("prompt") or ""
            negative_prompt = meta.get("negativePrompt") or ""

            prompt_data = {
                "civitai_id": str(item.get("id", "")),
                "full_prompt": full_prompt,
                "negative_prompt": negative_prompt,
                "reaction_count": stats.get("reactionCount", 0),
                "comment_count": stats.get("commentCount", 0),
                "download_count": stats.get("downloadCount", 0),
                "model_name": meta.get("Model") or meta.get("model") or item.get("model") or "",
                "model_id": str(item.get("modelId") or meta.get("ModelId") or ""),
                "raw_metadata": json.dumps(item, ensure_ascii=False)
            }

            # 追加メトリクス計算
            prompt_text = prompt_data["full_prompt"] or ""
            prompt_data["prompt_length"] = len(prompt_text)
            prompt_data["tag_count"] = len([t for t in [s.strip() for s in prompt_text.split(",")] if t])
            prompt_data["quality_score"] = QualityScorer.calculate_quality_score(prompt_text, stats)

            return prompt_data

        except Exception as e:
            print(f"[Extractor] Error extracting data: {e}")
            return None


class QualityScorer:
    """プロンプトの品質スコア計算"""

    @staticmethod
    def calculate_quality_score(prompt: str, stats: Dict[str, Any]) -> int:
        """品質スコア計算（キーワード＋リアクション）"""
        score = 0
        prompt_lower = (prompt or "").lower()

        # 技術的キーワード（重み: 2）
        technical_keywords = QUALITY_KEYWORDS["technical"]
        score += sum(2 for kw in technical_keywords if kw in prompt_lower)

        # 詳細キーワード（重み: 1）
        detail_keywords = QUALITY_KEYWORDS["detail"]
        score += sum(1 for kw in detail_keywords if kw in prompt_lower)

        # リアクション数ボーナス
        reactions = stats.get("reactionCount", 0)
        score += min(reactions // 5, 20)

        # 適切な長さボーナス
        word_count = len((prompt or "").split())
        if 15 <= word_count <= 80:
            score += 3

        return score


class CivitaiPromptCollector:
    """メインのプロンプト収集クラス"""

    def __init__(self, api_client: CivitaiAPIClient = None):
        self.api_client = api_client or CivitaiAPIClient()
        self.extractor = PromptDataExtractor()

    def collect_dataset(
        self,
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        max_items: int = 5000
    ) -> Dict[str, int]:
        """指定されたモデルのプロンプト・画像を収集（modelVersionId指定時は画像APIで全件取得）"""
        print(f"\n=== Collecting: {model_name or 'ALL_MODELS'} (model_id={model_id}) ===")

        collected = 0
        valid_items = []

        # modelVersionIdが数字なら画像API（正しいエンドポイント）で収集
        if model_id and str(model_id).isdigit():
            page = 1
            while collected < max_items:
                api_url = f"https://civitai.com/api/v1/images?modelVersionId={model_id}&limit=100&page={page}"
                print(f"[Collector] Fetching images page {page} (collected: {collected}/{max_items})")
                resp = requests.get(api_url, timeout=15)
                if resp.status_code != 200:
                    print(f"[Collector] API error: {resp.status_code}")
                    break
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    print("[Collector] No more images returned by API")
                    break
                for item in items:
                    if collected >= max_items:
                        break
                    prompt_data = self.extractor.extract_prompt_data(item)
                    if prompt_data:
                        if model_name and not prompt_data.get("model_name"):
                            prompt_data["model_name"] = model_name
                        prompt_data["model_id"] = str(model_id)
                        prompt_data["collected_at"] = datetime.now().isoformat()
                        valid_items.append(prompt_data)
                    collected += 1
                page += 1
                time.sleep(1.2)
        else:
            # 従来通りプロンプトAPIで収集
            params = {"limit": 20, "sort": "Most Reactions"}
            if model_id:
                params["modelVersionId"] = model_id
            next_page_url = None
            page_count = 1
            while collected < max_items:
                if next_page_url:
                    print(f"[Collector] Fetching page via nextPage (collected: {collected}/{max_items})")
                    batch, next_page_url = self.api_client.fetch_batch(next_page_url)
                else:
                    print(f"[Collector] Fetching page {page_count} (collected: {collected}/{max_items})")
                    batch, next_page_url = self.api_client.fetch_batch(params)
                if not batch:
                    print("[Collector] No more items returned by API")
                    break
                for item in batch:
                    if collected >= max_items:
                        break
                    prompt_data = self.extractor.extract_prompt_data(item)
                    if prompt_data and prompt_data.get("full_prompt"):
                        if model_name and not prompt_data.get("model_name"):
                            prompt_data["model_name"] = model_name
                        if model_id and not prompt_data.get("model_id"):
                            prompt_data["model_id"] = str(model_id)
                        prompt_data["collected_at"] = datetime.now().isoformat()
                        valid_items.append(prompt_data)
                    collected += 1
                page_count += 1
                time.sleep(1.2)
                if not next_page_url:
                    break
        print(f"[Collector] Completed: {len(valid_items)} valid items from {collected} total")
        return {
            "collected": collected,
            "valid": len(valid_items),
            "items": valid_items
        }

    def collect_for_models(self, models: Dict[str, str], max_per_model: int = 5000) -> Dict[str, Dict]:
        """複数モデルを順次収集"""
        results = {}
        for name, model_id in models.items():
            result = self.collect_dataset(
                model_id=model_id,
                model_name=name,
                max_items=max_per_model
            )
            results[name] = result
            time.sleep(2)  # モデル間の待機
        return results

def main():
    """テスト実行用メイン関数"""
    try:
        print("🚀 CivitAI Prompt Collector テスト開始")

        # APIキー確認
        from src.config import CIVITAI_API_KEY
        if not CIVITAI_API_KEY or CIVITAI_API_KEY == "your_api_key_here":
            print("❌ APIキーが設定されていません")
            print("config.py の CIVITAI_API_KEY を設定してください")
            return

        print(f"✅ APIキー設定確認完了")

        # コレクター初期化
        collector = CivitaiPromptCollector()

        # テスト収集（少量）
        print("\n📦 テストデータ収集開始（最大50件）")
        result = collector.collect_dataset(max_items=50)

        print(f"\n✅ 収集完了:")
        print(f"  - 総取得数: {result['collected']}件")
        print(f"  - 有効データ: {result['valid']}件")

        if result['valid'] > 0:
            # データベース保存
            try:
                from src.database import DatabaseManager
                db = DatabaseManager()

                saved_count = 0
                for item in result['items']:
                    if db.save_prompt_data(item):
                        saved_count += 1

                print(f"  - データベース保存: {saved_count}件")
                print("\n🎯 次は categorizer.py を実行してください")

            except Exception as e:
                print(f"❌ データベース保存エラー: {e}")

    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
