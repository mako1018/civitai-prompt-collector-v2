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
    
    def setup_database(self):
        """データベースとテーブルを作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # テーブル作成
            for table_name, schema in DB_SCHEMA.items():
                cursor.execute(schema)
            
            conn.commit()
            print(f"[DB] Database initialized: {self.db_path}")
            
        except Exception as e:
            print(f"[DB] Error setting up database: {e}")
            
        finally:
            conn.close()
    
    def save_prompt_data(self, prompt_data: Dict[str, Any]) -> bool:
        """プロンプトデータをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # UPSERT（挿入または更新）
            cursor.execute('''
            INSERT INTO civitai_prompts
            (civitai_id, full_prompt, negative_prompt, quality_score,
             reaction_count, comment_count, download_count, prompt_length, tag_count,
             model_name, model_id, collected_at, raw_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(civitai_id) DO UPDATE SET
                full_prompt=excluded.full_prompt,
                negative_prompt=excluded.negative_prompt,
                quality_score=excluded.quality_score,
                reaction_count=excluded.reaction_count,
                comment_count=excluded.comment_count,
                download_count=excluded.download_count,
                prompt_length=excluded.prompt_length,
                tag_count=excluded.tag_count,
                model_name=excluded.model_name,
                model_id=excluded.model_id,
                collected_at=excluded.collected_at,
                raw_metadata=excluded.raw_metadata
            ''', (
                prompt_data["civitai_id"],
                prompt_data["full_prompt"],
                prompt_data["negative_prompt"],
                prompt_data["quality_score"],
                prompt_data["reaction_count"],
                prompt_data["comment_count"],
                prompt_data["download_count"],
                prompt_data["prompt_length"],
                prompt_data["tag_count"],
                prompt_data["model_name"],
                prompt_data["model_id"],
                prompt_data.get("collected_at", datetime.now().isoformat()),
                prompt_data["raw_metadata"]
            ))
            
            conn.commit()
            
            # prompt_idを取得（カテゴリ保存用）
            cursor.execute('SELECT id FROM civitai_prompts WHERE civitai_id = ?', 
                         (prompt_data["civitai_id"],))
            row = cursor.fetchone()
            prompt_id = row[0] if row else None
            
            return prompt_id is not None
            
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


# 便利関数
def create_database(db_path: str = DEFAULT_DB_PATH) -> DatabaseManager:
    """データベースを作成して管理オブジェクトを返す"""
    return DatabaseManager(db_path)


def save_prompts_batch(db_manager: DatabaseManager, prompts_data: List[Dict[str, Any]]) -> int:
    """プロンプトデータをバッチで保存"""
    saved_count = 0
    
    for prompt_data in prompts_data:
        if db_manager.save_prompt_data(prompt_data):
            saved_count += 1
        else:
            print(f"[DB] Failed to save prompt: {prompt_data.get('civitai_id', 'unknown')}")
    
    print(f"[DB] Batch save completed: {saved_count}/{len(prompts_data)} items saved")
    return saved_count
