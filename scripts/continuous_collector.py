#!/usr/bin/env python3
"""
CivitAI Prompt Collector - 連続収集対応版
オフセット管理で累積的にデータを取得
"""

import requests
import json
import time
import sqlite3
from datetime import datetime, timezone, timedelta
def now_jst():
    return datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from src.config import (
    CIVITAI_API_KEY, USER_AGENT, API_BASE_URL,
    REQUEST_TIMEOUT, RETRY_DELAY, RATE_LIMIT_WAIT,
    QUALITY_KEYWORDS, DEFAULT_DB_PATH
)


class ContinuousCivitaiCollector:
    """連続収集に対応したCivitAIコレクター"""

    def __init__(self, api_key: str = CIVITAI_API_KEY, user_agent: str = USER_AGENT):
        self.api_key = api_key
        self.user_agent = user_agent
        self.db_path = DEFAULT_DB_PATH

    def _get_headers(self) -> Dict[str, str]:
        """APIリクエスト用ヘッダーを生成"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Connection": "close",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_collection_state(self, model_id: str, version_id: str = "") -> Dict[str, Any]:
        """指定されたモデル/バージョンの収集状態を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 収集状態テーブルの作成（存在しない場合）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    version_id TEXT DEFAULT '',
                    last_offset INTEGER DEFAULT 0,
                    total_collected INTEGER DEFAULT 0,
                    next_page_cursor TEXT DEFAULT NULL,
                    status TEXT DEFAULT 'idle',
                    planned_total INTEGER DEFAULT NULL,
                    attempted INTEGER DEFAULT 0,
                    duplicates INTEGER DEFAULT 0,
                    saved INTEGER DEFAULT 0,
                    summary_json TEXT DEFAULT NULL,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_id, version_id)
                )
            """)
            # Ensure 'next_page_cursor' column exists for older DBs
            try:
                cursor.execute("PRAGMA table_info(collection_state)")
                cols = [r[1] for r in cursor.fetchall()]
                # Add any missing columns (migrate older DBs)
                migrations = [
                    ("next_page_cursor", "TEXT DEFAULT NULL"),
                    ("status", "TEXT DEFAULT 'idle'"),
                    ("planned_total", "INTEGER DEFAULT NULL"),
                    ("attempted", "INTEGER DEFAULT 0"),
                    ("duplicates", "INTEGER DEFAULT 0"),
                    ("saved", "INTEGER DEFAULT 0"),
                    ("summary_json", "TEXT DEFAULT NULL")
                ]
                for col_name, col_def in migrations:
                    if col_name not in cols:
                        try:
                            cursor.execute(f"ALTER TABLE collection_state ADD COLUMN {col_name} {col_def}")
                            conn.commit()
                            print(f"[State] Migrated collection_state: added {col_name} column")
                        except Exception as _e:
                            print(f"[State] Failed to add {col_name} column: {_e}")
            except Exception:
                pass

            # 既存状態の取得 (next_page_cursor を含める)
            cursor.execute(
                "SELECT last_offset, total_collected, next_page_cursor FROM collection_state WHERE model_id = ? AND version_id = ?",
                (model_id, version_id or "")
            )
            row = cursor.fetchone()

            if row:
                state = {
                    "last_offset": row[0],
                    "total_collected": row[1],
                    "next_page_cursor": row[2],
                    "exists": True
                }
            else:
                state = {
                    "last_offset": 0,
                    "total_collected": 0,
                    "next_page_cursor": None,
                    "exists": False
                }

            conn.close()
            return state

        except Exception as e:
            print(f"[State] Failed to get collection state: {e}")
            return {"last_offset": 0, "total_collected": 0, "next_page_cursor": None, "exists": False}

    def _update_collection_state(self, model_id: str, version_id: str = "",
                                new_items: int = 0, new_offset: int = 0, next_page_cursor: Optional[str] = None):
        """収集状態を更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # If next_page_cursor is provided, store it; otherwise leave as-is
            cursor.execute("""
                INSERT OR REPLACE INTO collection_state
                (id, model_id, version_id, last_offset, total_collected, next_page_cursor, last_update)
                VALUES (
                    COALESCE((SELECT id FROM collection_state WHERE model_id = ? AND version_id = ?), NULL),
                    ?, ?, ?,
                    COALESCE((SELECT total_collected FROM collection_state
                             WHERE model_id = ? AND version_id = ?), 0) + ?,
                    ?,
                    CURRENT_TIMESTAMP)
            """, (model_id, version_id or "", model_id, version_id or "", new_offset, model_id, version_id or "", new_items, next_page_cursor))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[State] Failed to update collection state: {e}")

    def collect_continuous(
        self,
        model_id: Optional[str] = None,
        version_id: Optional[str] = None,
        model_name: Optional[str] = None,
        max_items: int = 50,
        use_version_api: bool = True,
        strict_version_match: bool = False
    ) -> Dict[str, Any]:
        """連続的にデータを収集（前回の続きから開始）"""

        target_id = version_id if version_id else model_id
        if not target_id:
            return {"error": "model_id or version_id is required", "collected": 0, "valid": 0, "items": []}

        print(f"{now_jst()} === Continuous Collection: {model_name or target_id} ===")
        # 収集ジョブ開始時にDBの状態をrunningへ
        self.set_job_status(model_id or '', version_id or '', status='running', planned_total=max_items)

        # 収集状態の取得
        state = self._get_collection_state(model_id or "", version_id or "")
        start_offset = state["last_offset"]

        print(f"{now_jst()} [Collector] Previous total: {state['total_collected']}, Starting from offset: {start_offset}")

        collected = 0
        valid_items = []
        page_size = 50

        # ページ番号とページ内スキップ数を計算
        current_page = (start_offset // page_size) + 1
        items_processed_in_current_page = start_offset % page_size

        # APIエンドポイントの決定
        if use_version_api and version_id:
            base_url = "https://civitai.com/api/v1/images"
            param_key = "modelVersionId"
            param_value = version_id
        elif model_id:
            base_url = "https://civitai.com/api/v1/images"
            param_key = "modelId"
            param_value = model_id
        else:
            return {"error": "Invalid parameters", "collected": 0, "valid": 0, "items": []}

        headers = self._get_headers()
        next_page_url = state.get('next_page_cursor')

        while collected < max_items:
            # 停止フラグチェック
            stop_flag = Path(__file__).resolve().parent / 'collect_stop.flag'
            if stop_flag.exists():
                print(f"{now_jst()} [Info] Stop flag detected — stopping collection gracefully")
                try:
                    stop_flag.unlink()
                except Exception:
                    pass
                break

            # リクエスト構築
            if next_page_url:
                req_url = next_page_url
                req_params = None
                log_desc = f"cursor page (from offset {start_offset + collected})"
            else:
                req_url = base_url
                req_params = {
                    param_key: param_value,
                    "limit": page_size,
                    "page": current_page,
                    "sort": "Newest"
                }
                log_desc = f"page {current_page}"

            print(f"{now_jst()} [Collector] Fetching {log_desc} (collected: {collected}/{max_items})")

            try:
                if req_params is not None:
                    resp = requests.get(req_url, params=req_params, headers=headers, timeout=REQUEST_TIMEOUT)
                else:
                    resp = requests.get(req_url, headers=headers, timeout=REQUEST_TIMEOUT)

                if resp.status_code != 200:
                    if resp.status_code == 429:
                        print(f"{now_jst()} [Collector] Rate limited, waiting {RATE_LIMIT_WAIT}s")
                        time.sleep(RATE_LIMIT_WAIT)
                        continue
                    print(f"{now_jst()} [Collector] API error: {resp.status_code} - {resp.text[:200]}")
                    break

                data = resp.json()
                items = data.get("items", [])

                if not items:
                    print(f"{now_jst()} [Collector] No more items available")
                    break

                # 次ページカーソル取得
                meta_next = (data.get("metadata") or {}).get("nextPage")
                next_page_url = meta_next

                # 現在のページで処理すべきアイテムを決定
                if items_processed_in_current_page > 0:
                    # 最初のページで一部スキップが必要
                    items_to_process = items[items_processed_in_current_page:]
                    items_processed_in_current_page = 0  # 次のページからは全処理
                else:
                    # 全アイテムを処理
                    items_to_process = items

                batch_valid = 0
                for i, item in enumerate(items_to_process):
                    if collected >= max_items:
                        break

                    try:
                        # strict_version_match チェック
                        if strict_version_match and version_id:
                            civres = (item.get('meta') or {}).get('civitaiResources') or item.get('civitaiResources') or []
                            matched = False
                            if isinstance(civres, list):
                                for r in civres:
                                    if isinstance(r, dict) and str((r.get('type') or r.get('resourceType') or '').lower()) == 'checkpoint':
                                        cand = r.get('modelVersionId') or r.get('id')
                                        if cand and str(cand) == str(version_id):
                                            matched = True
                                            break
                            if not matched:
                                collected += 1
                                continue

                        prompt_data = self._extract_prompt_data(item, model_name, target_id)
                        if prompt_data and prompt_data.get("full_prompt"):
                            valid_items.append(prompt_data)
                            batch_valid += 1

                    except Exception as e:
                        print(f"{now_jst()} [Collector] Failed to extract item {i}: {e}")

                    collected += 1

                print(f"{now_jst()} [Collector] {log_desc}: {batch_valid}/{len(items_to_process)} valid items")

                # 次のページに進む
                if not next_page_url:
                    current_page += 1
                    # もしこのページが満杯でない場合は終了
                    if len(items) < page_size:
                        break

                time.sleep(3.0)

            except Exception as e:
                print(f"{now_jst()} [Collector] Error fetching page: {e}")
                break

        # バッチ内重複除去
        unique_map = {}
        for it in valid_items:
            cid = it.get('civitai_id')
            if cid and cid not in unique_map:
                unique_map[cid] = it

        deduped_items = list(unique_map.values())
        duplicates_removed = len(valid_items) - len(deduped_items)
        if duplicates_removed:
            print(f"{now_jst()} [Collector] Deduped {duplicates_removed} duplicate items within current batch")

        # 正しい次回開始オフセットの計算
        next_offset = start_offset + collected

        print(f"{now_jst()} [Collector] Continuous collection completed: {len(deduped_items)} unique valid items from {collected} total")
        print(f"{now_jst()} [Collector] Next collection will start from offset: {next_offset}")
        # 収集完了時にDBの状態をcompletedへ
        self.set_job_status(model_id or '', version_id or '', status='completed')

        return {
            "collected": collected,
            "valid": len(deduped_items),
            "items": deduped_items,
            "next_offset": next_offset,
            "total_ever_collected": state["total_collected"],
            "next_page_cursor": next_page_url
        }

    def _extract_prompt_data(self, item: Dict[str, Any], model_name: str = "", model_id: str = "") -> Optional[Dict[str, Any]]:
        """プロンプトデータ抽出"""
        try:
            meta = item.get("meta", {}) or {}
            stats = item.get("stats", {}) or {}

            full_prompt = meta.get("prompt") or ""
            if not full_prompt:
                return None

            return {
                "civitai_id": str(item.get("id", "")),
                "full_prompt": full_prompt,
                "negative_prompt": meta.get("negativePrompt") or "",
                "reaction_count": stats.get("reactionCount", 0),
                "comment_count": stats.get("commentCount", 0),
                "download_count": stats.get("downloadCount", 0),
                "model_name": model_name or meta.get("Model") or meta.get("model") or "",
                "model_id": model_id or str(item.get("modelId", "")),
                "prompt_length": len(full_prompt),
                "tag_count": len([t.strip() for t in full_prompt.split(",") if t.strip()]),
                "quality_score": self._calculate_quality_score(full_prompt, stats),
                "collected_at": datetime.now().isoformat(),
                "raw_metadata": json.dumps(item, ensure_ascii=False)
            }
        except Exception as e:
            print(f"[Extractor] Error: {e}")
            return None

    def _calculate_quality_score(self, prompt: str, stats: Dict[str, Any]) -> int:
        """簡易品質スコア計算"""
        score = 0
        prompt_lower = prompt.lower()

        # 基本的なキーワードチェック
        technical_keywords = ["realistic", "detailed", "highres", "masterpiece", "best quality"]
        score += sum(2 for kw in technical_keywords if kw in prompt_lower)

        # リアクション数
        reactions = stats.get("reactionCount", 0)
        score += min(reactions // 5, 20)

        # 長さボーナス
        word_count = len(prompt.split())
        if 15 <= word_count <= 80:
            score += 3

        return score

    def reset_collection_state(self, model_id: str, version_id: str = ""):
        """収集状態をリセット（最初から収集し直す場合）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM collection_state WHERE model_id = ? AND version_id = ?",
                (model_id, version_id or "")
            )
            conn.commit()
            conn.close()
            print(f"{now_jst()} [State] Reset collection state for {model_id}/{version_id}")
        except Exception as e:
            print(f"{now_jst()} [State] Failed to reset state: {e}")

    def set_collection_state(self, model_id: str, version_id: str = "", last_offset: int = 0, total_collected: int = 0, next_page_cursor: str = ""):
        """指定した値で collection_state を上書き・設定する（絶対値）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO collection_state
                (id, model_id, version_id, last_offset, total_collected, next_page_cursor, last_update)
                VALUES (
                    COALESCE((SELECT id FROM collection_state WHERE model_id = ? AND version_id = ?), NULL),
                    ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
            """, (model_id, version_id or "", model_id, version_id or "", last_offset, total_collected, next_page_cursor))

            conn.commit()
            conn.close()
            print(f"{now_jst()} [State] Set collection_state for {model_id}/{version_id}: last_offset={last_offset}, total_collected={total_collected}")
        except Exception as e:
            print(f"{now_jst()} [State] Failed to get collection state: {e}")
            # set_collection_state does not return a value
            pass
    def get_collection_summary(self) -> List[Dict[str, Any]]:
        """全ての収集状態のサマリを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_id, version_id, last_offset, total_collected, last_update
                FROM collection_state
                ORDER BY last_update DESC
            """)

            summary = []
            for row in cursor.fetchall():
                summary.append({
                    "model_id": row[0],
                    "version_id": row[1] or "",
                    "last_offset": row[2],
                    "total_collected": row[3],
                    "last_update": row[4]
                })

            conn.close()
            return summary

        except Exception as e:
            print(f"{now_jst()} [State] Failed to get summary: {e}")
            return []

    def set_job_status(self, model_id: str, version_id: str, status: str, planned_total: Optional[int] = None):
        """Set the job status (running/completed/idle) and optional planned total."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Build params and upsert status/planned_total
            params = (
                model_id, version_id or "",
                model_id, version_id or "",
                model_id, version_id or "",
                model_id, version_id or "",
                status, planned_total
            )
            cursor.execute("""
                INSERT OR REPLACE INTO collection_state
                (id, model_id, version_id, last_offset, total_collected, status, planned_total, last_update)
                VALUES (
                    COALESCE((SELECT id FROM collection_state WHERE model_id = ? AND version_id = ?), NULL),
                    ?, ?, COALESCE((SELECT last_offset FROM collection_state WHERE model_id = ? AND version_id = ?), 0),
                    COALESCE((SELECT total_collected FROM collection_state WHERE model_id = ? AND version_id = ?), 0), ?, ?, CURRENT_TIMESTAMP
                )
            """, params)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"{now_jst()} [State] Failed to set job status: {e}")

    def write_job_summary(self, model_id: str, version_id: str, summary: Dict[str, Any]):
        """Write JSON summary for a job into collection_state.summary_json and update numeric columns."""
        try:
            import json as _json
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Upsert summary_json and numeric aggregates
            params = (
                model_id, version_id or "",
                model_id, version_id or "",
                model_id, version_id or "",
                model_id, version_id or "",
                summary.get('attempted', 0),
                summary.get('duplicates_total', 0),
                summary.get('new_saved', 0),
                _json.dumps(summary, ensure_ascii=False)
            )
            cursor.execute("""
                INSERT OR REPLACE INTO collection_state
                (id, model_id, version_id, last_offset, total_collected, attempted, duplicates, saved, summary_json, last_update)
                VALUES (
                    COALESCE((SELECT id FROM collection_state WHERE model_id = ? AND version_id = ?), NULL),
                    ?, ?, COALESCE((SELECT last_offset FROM collection_state WHERE model_id = ? AND version_id = ?), 0),
                    COALESCE((SELECT total_collected FROM collection_state WHERE model_id = ? AND version_id = ?), 0), ?, ?, ?, ?, CURRENT_TIMESTAMP
                )
            """, params)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"{now_jst()} [State] Failed to write job summary: {e}")


def main():
    """テスト実行"""
    collector = ContinuousCivitaiCollector()

    # 初回収集：50件
    print("=== First collection (50 items) ===")
    result1 = collector.collect_continuous(
        version_id="128078",
        model_name="TestModel",
        max_items=50
    )
    print(f"Result 1: {result1['valid']} valid items")

    # 2回目収集：50件追加（続きから）
    print("\n=== Second collection (50 more items) ===")
    result2 = collector.collect_continuous(
        version_id="128078",
        model_name="TestModel",
        max_items=50
    )
    print(f"Result 2: {result2['valid']} valid items")

    def set_job_status(self, model_id: str, version_id: str = "", status: str = "idle", planned_total: Optional[int] = None):
        """Set the job status for a model/version in collection_state."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO collection_state
                (model_id, version_id, status, planned_total, last_update)
                VALUES (?, ?, ?, ?, ?)
            """, (model_id, version_id or "", status, planned_total, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[State] Failed to set job status: {e}")

    def write_job_summary(self, model_id: str, version_id: str, summary: Dict[str, Any]):
        """Write the job summary JSON to collection_state."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE collection_state SET
                    summary_json = ?,
                    attempted = ?,
                    duplicates = ?,
                    saved = ?,
                    last_update = ?
                WHERE model_id = ? AND version_id = ?
            """, (
                json.dumps(summary, ensure_ascii=False),
                summary.get('attempted', 0),
                summary.get('duplicates_total', 0),
                summary.get('new_saved', 0),
                datetime.now().isoformat(),
                model_id,
                version_id or ""
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[State] Failed to write job summary: {e}")


if __name__ == "__main__":
    main()
