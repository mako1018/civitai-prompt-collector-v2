#!/usr/bin/env python3
"""
CivitAI Prompt Collector - データベース操作
SQLiteデータベースの作成、保存、取得を担当
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import DEFAULT_DB_PATH, DB_SCHEMA


class DatabaseManager:
    """データベース操作を管理するクラス"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_directory()
        self.setup_database()

    def _ensure_directory(self):
        """データベースファイルのディレクトリを作成"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    # 互換性メソッド: Streamlit UI が期待するインターフェースを提供
    def _get_connection(self):
        """内部用: 生の sqlite3.Connection を返す"""
        return sqlite3.connect(self.db_path)

    def get_prompt_count(self) -> int:
        """保存されているプロンプトの総数を返す (Streamlit UI 互換)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def setup_database(self):
        """データベースとテーブルを作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # テーブル作成
            for table_name, schema in DB_SCHEMA.items():
                cursor.execute(schema)

            # Migration: ensure model_version_id column exists (backwards compatible)
            try:
                cursor.execute("PRAGMA table_info(civitai_prompts)")
                cols = [r[1] for r in cursor.fetchall()]
                if 'model_version_id' not in cols:
                    cursor.execute('ALTER TABLE civitai_prompts ADD COLUMN model_version_id TEXT')
                    print('[DB] Migrated: added column model_version_id')
                # Ensure prompt_resources table exists (DB_SCHEMA should include it)
                if 'prompt_resources' not in cols:
                    # This check is simply to avoid failing on older DBs; actual creation handled by DB_SCHEMA
                    pass
            except Exception as e:
                print(f'[DB] Migration warning: {e}')

            # Ensure collection_state table exists
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_state'")
                if not cursor.fetchone():
                    cursor.execute(DB_SCHEMA['collection_state'])
                    print('[DB] Migrated: created collection_state table')
            except Exception as e:
                print(f'[DB] Migration warning for collection_state: {e}')

            conn.commit()
            print(f"[DB] Database initialized: {self.db_path}")

        except Exception as e:
            print(f"[DB] Error setting up database: {e}")

        finally:
            conn.close()

    def save_prompt_data(self, prompt_data: Dict[str, Any]) -> bool:
        """プロンプトデータをデータベースに保存

        返り値:
            True  -> 新規に挿入された
            False -> 既存行が更新された、または保存失敗
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check existence first to determine insert vs update
            cursor.execute('SELECT id FROM civitai_prompts WHERE civitai_id = ?', (prompt_data["civitai_id"],))
            existing = cursor.fetchone()

            if existing is None:
                # Insert new
                cursor.execute('''
                INSERT INTO civitai_prompts
                (civitai_id, full_prompt, negative_prompt, quality_score,
                 reaction_count, comment_count, download_count, prompt_length, tag_count,
                 model_name, model_id, model_version_id, collected_at, raw_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    prompt_data["civitai_id"],
                    prompt_data["full_prompt"],
                    prompt_data["negative_prompt"],
                    prompt_data.get("quality_score"),
                    prompt_data.get("reaction_count", 0),
                    prompt_data.get("comment_count", 0),
                    prompt_data.get("download_count", 0),
                    prompt_data.get("prompt_length", 0),
                    prompt_data.get("tag_count", 0),
                    prompt_data.get("model_name"),
                    prompt_data.get("model_id"),
                    prompt_data.get("model_version_id"),
                    prompt_data.get("collected_at", datetime.now().isoformat()),
                    prompt_data.get("raw_metadata")
                ))
                conn.commit()

                # prompt_idを取得
                cursor.execute('SELECT id FROM civitai_prompts WHERE civitai_id = ?', (prompt_data["civitai_id"],))
                row = cursor.fetchone()
                prompt_id = row[0] if row else None
                # Save resources if present
                try:
                    if prompt_id and prompt_data.get('resources'):
                        self.save_prompt_resources(prompt_id, prompt_data.get('resources'))
                except Exception:
                    pass
                return True if prompt_id is not None else False

            else:
                # Update existing row
                # Merge incoming model_version_id into existing row if DB value is empty
                try:
                    cursor.execute('SELECT model_version_id, raw_metadata FROM civitai_prompts WHERE civitai_id = ?', (prompt_data["civitai_id"],))
                    existing_row = cursor.fetchone()
                    existing_mv = existing_row[0] if existing_row else None
                    existing_raw = existing_row[1] if existing_row else None
                except Exception:
                    existing_mv = None
                    existing_raw = None

                incoming_mv = prompt_data.get("model_version_id")
                # If incoming_mv is empty, try to parse raw_metadata to find a modelVersionId or civitaiResources checkpoint
                if not incoming_mv:
                    try:
                        raw = prompt_data.get('raw_metadata')
                        if raw:
                            import json as _json
                            parsed = _json.loads(raw)
                            # try direct fields
                            cand = parsed.get('modelVersionId') or ''
                            if not cand and isinstance(parsed.get('modelVersionIds'), list) and parsed.get('modelVersionIds'):
                                cand = parsed.get('modelVersionIds')[0]
                            # check meta.civitaiResources
                            if not cand:
                                meta = parsed.get('meta') or parsed.get('metadata') or {}
                                civres = meta.get('civitaiResources') or parsed.get('civitaiResources') or []
                                if isinstance(civres, list):
                                    for r in civres:
                                        if isinstance(r, dict):
                                            typ = r.get('type') or r.get('resourceType') or ''
                                            if str(typ).lower() == 'checkpoint':
                                                cand = r.get('modelVersionId') or r.get('id') or cand
                                                if cand:
                                                    break
                            if cand:
                                incoming_mv = str(cand)
                    except Exception:
                        pass

                # Prefer existing value if present, otherwise use incoming (if not empty)
                final_mv = existing_mv if existing_mv not in (None, '') else (str(incoming_mv) if incoming_mv not in (None, '') else existing_mv)

                # Prefer incoming raw_metadata if it provides more/different info
                final_raw = prompt_data.get("raw_metadata") or existing_raw

                cursor.execute('''
                UPDATE civitai_prompts SET
                    full_prompt = ?,
                    negative_prompt = ?,
                    quality_score = ?,
                    reaction_count = ?,
                    comment_count = ?,
                    download_count = ?,
                    prompt_length = ?,
                    tag_count = ?,
                    model_name = ?,
                    model_id = ?,
                    model_version_id = ?,
                    collected_at = ?,
                    raw_metadata = ?
                WHERE civitai_id = ?
                ''', (
                    prompt_data.get("full_prompt"),
                    prompt_data.get("negative_prompt"),
                    prompt_data.get("quality_score"),
                    prompt_data.get("reaction_count", 0),
                    prompt_data.get("comment_count", 0),
                    prompt_data.get("download_count", 0),
                    prompt_data.get("prompt_length", 0),
                    prompt_data.get("tag_count", 0),
                    prompt_data.get("model_name"),
                    prompt_data.get("model_id"),
                    final_mv,
                    prompt_data.get("collected_at", datetime.now().isoformat()),
                    final_raw,
                    prompt_data["civitai_id"]
                ))
                conn.commit()
                # Save resources if present (update/replace)
                try:
                    # get prompt id
                    cursor.execute('SELECT id FROM civitai_prompts WHERE civitai_id = ?', (prompt_data['civitai_id'],))
                    prow = cursor.fetchone()
                    if prow:
                        prompt_id = prow[0]
                        if prompt_data.get('resources'):
                            self.save_prompt_resources(prompt_id, prompt_data.get('resources'))
                except Exception:
                    pass
                # Indicate this was an update (not an insert)
                print(f"[DB] Updated existing civitai_id={prompt_data['civitai_id']} (model_version_id set to {final_mv})")
                return False

        except Exception as e:
            print(f"[DB] Error saving prompt data: {e}")
            return False

        finally:
            conn.close()

    def save_prompt_categories(self, prompt_id: int, categories: Dict[str, Dict]) -> bool:
        """プロンプトのカテゴリデータを保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 既存のカテゴリを削除（重複防止）
            cursor.execute('DELETE FROM prompt_categories WHERE prompt_id = ?', (prompt_id,))

            # 新しいカテゴリを挿入
            for category, data in categories.items():
                cursor.execute('''
                INSERT INTO prompt_categories (prompt_id, category, keywords, confidence)
                VALUES (?, ?, ?, ?)
                ''', (
                    prompt_id,
                    category,
                    json.dumps(data["keywords"], ensure_ascii=False),
                    data["confidence"]
                ))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Error saving categories: {e}")
            return False

        finally:
            conn.close()

    def save_prompt_resources(self, prompt_id: int, resources: List[Dict[str, Any]]) -> bool:
        """プロンプトに紐づく civitaiResources を正規化して保存/更新する

        resources: list of dicts with keys: index,type,name,modelId,modelVersionId,resourceId,raw
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Remove existing resources for prompt
            cursor.execute('DELETE FROM prompt_resources WHERE prompt_id = ?', (prompt_id,))

            for r in resources:
                cursor.execute('''
                INSERT INTO prompt_resources
                (prompt_id, resource_index, resource_type, resource_name, resource_model_id, resource_model_version_id, resource_id, resource_raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    prompt_id,
                    r.get('index'),
                    r.get('type'),
                    r.get('name'),
                    r.get('modelId'),
                    r.get('modelVersionId'),
                    r.get('resourceId'),
                    r.get('raw')
                ))

            conn.commit()
            return True

        except Exception as e:
            print(f"[DB] Error saving resources: {e}")
            return False

        finally:
            conn.close()

    def get_prompt_resources(self, prompt_id: int) -> List[Dict[str, Any]]:
        """指定プロンプトのリソース一覧を返す"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT resource_index, resource_type, resource_name, resource_model_id, resource_model_version_id, resource_id, resource_raw FROM prompt_resources WHERE prompt_id = ? ORDER BY resource_index', (prompt_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    'index': r[0],
                    'type': r[1],
                    'name': r[2],
                    'modelId': r[3],
                    'modelVersionId': r[4],
                    'resourceId': r[5],
                    'raw': r[6]
                })
            return result

        except Exception as e:
            print(f"[DB] Error getting resources: {e}")
            return []

        finally:
            conn.close()

    def get_prompt_by_civitai_id(self, civitai_id: str) -> Optional[Dict[str, Any]]:
        """CivitAI IDでプロンプトを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM civitai_prompts WHERE civitai_id = ?', (civitai_id,))
            row = cursor.fetchone()

            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

        except Exception as e:
            print(f"[DB] Error getting prompt: {e}")
            return None

        finally:
            conn.close()

    def get_all_prompts(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """全プロンプトを取得（オプション：モデル名でフィルタ）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if model_name:
                cursor.execute('SELECT * FROM civitai_prompts WHERE model_name = ?', (model_name,))
            else:
                cursor.execute('SELECT * FROM civitai_prompts')

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            print(f"[DB] Error getting prompts: {e}")
            return []

        finally:
            conn.close()

    def get_category_statistics(self) -> Dict[str, Dict[str, int]]:
        """カテゴリ別統計を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
            SELECT p.model_name, c.category, COUNT(*) as count
            FROM civitai_prompts p
            JOIN prompt_categories c ON p.id = c.prompt_id
            GROUP BY p.model_name, c.category
            ORDER BY p.model_name, c.category
            ''')

            rows = cursor.fetchall()

            # データ構造: {model_name: {category: count}}
            stats = {}
            for model_name, category, count in rows:
                model_name = model_name or "Unknown"
                if model_name not in stats:
                    stats[model_name] = {}
                stats[model_name][category] = count

            return stats

        except Exception as e:
            print(f"[DB] Error getting statistics: {e}")
            return {}

        finally:
            conn.close()

    def get_total_prompts_count(self) -> int:
        """保存されているプロンプトの総数を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
            count = cursor.fetchone()[0]
            return count

        except Exception as e:
            print(f"[DB] Error getting count: {e}")
            return 0

        finally:
            conn.close()

    def get_prompt_count_by_version(self, version_id: str) -> int:
        """指定バージョンIDで保存されているプロンプト件数を返す"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (str(version_id),))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"[DB] Error getting count by version: {e}")
            return 0

    def get_collection_state(self) -> List[Dict[str, Any]]:
        """collection_state テーブルの全行を取得して辞書のリストで返す"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Ensure table exists
            cursor.execute('''
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
            ''')
            cursor.execute('SELECT model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state ORDER BY last_update DESC')
            rows = cursor.fetchall()
            cols = ['model_id', 'version_id', 'last_offset', 'total_collected', 'status', 'planned_total', 'attempted', 'duplicates', 'saved', 'summary_json', 'last_update']
            result = [dict(zip(cols, r)) for r in rows]
            conn.close()
            return result
        except Exception as e:
            print(f"[DB] Error reading collection_state: {e}")
            return []

    def get_collection_state_for_version(self, version_id: int) -> List[Dict[str, Any]]:
        """指定 version_id に対応する collection_state 行を取得（version_id が None の場合は全件）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if version_id:
                cursor.execute('SELECT model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state WHERE version_id = ? ORDER BY last_update DESC', (str(version_id),))
            else:
                cursor.execute('SELECT model_id, version_id, last_offset, total_collected, status, planned_total, attempted, duplicates, saved, summary_json, last_update FROM collection_state ORDER BY last_update DESC')
            rows = cursor.fetchall()
            cols = ['model_id', 'version_id', 'last_offset', 'total_collected', 'status', 'planned_total', 'attempted', 'duplicates', 'saved', 'summary_json', 'last_update']
            result = [dict(zip(cols, r)) for r in rows]
            conn.close()
            return result
        except Exception as e:
            print(f"[DB] Error reading collection_state for version: {e}")
            return []


# 便利関数
def create_database(db_path: str = DEFAULT_DB_PATH) -> DatabaseManager:
    """データベースを作成して管理オブジェクトを返す"""
    return DatabaseManager(db_path)


def save_prompts_batch(db_manager: DatabaseManager, prompts_data: List[Dict[str, Any]]) -> int:
    """プロンプトデータをバッチで保存

    戻り値は"新規に追加された件数"を返す。
    """
    new_count = 0

    for prompt_data in prompts_data:
        try:
            is_new = db_manager.save_prompt_data(prompt_data)
            if is_new:
                new_count += 1
        except Exception as e:
            print(f"[DB] Failed to save prompt: {prompt_data.get('civitai_id', 'unknown')} - {e}")

    print(f"[DB] Batch save completed: {new_count}/{len(prompts_data)} new items")
    return new_count
