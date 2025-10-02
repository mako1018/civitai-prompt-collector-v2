#!/usr/bin/env python3
"""CivitAI NSFW専用コレクター - 露骨な表現を積極的に収集"""
import requests
import time
import sqlite3
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

sys.path.append('src')
from database import DatabaseManager

class NSFWCivitAICollector:
    """NSFW専用のCivitAI収集器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1/images"
        self.db_manager = DatabaseManager()
        self.request_delay = 1.2  # API制限対応

    def _get_headers(self) -> Dict[str, str]:
        """API リクエストヘッダーを取得"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def collect_nsfw_content(self, target_count: int = 1000) -> Dict[str, int]:
        """NSFW専用の積極的収集"""

        print(f"🔥 NSFW専用収集開始 - 目標: {target_count}件")

        # 1. NSFW専用パラメータでの収集
        nsfw_params = {
            "limit": 100,
            "sort": "Newest",
            "period": "AllTime",
            "nsfw": "X",  # 明示的にNSFWコンテンツを要求
            # "tags": "nsfw,explicit,nude"  # NSFWタグを指定
        }

        collected_items = []
        page = 1
        max_pages = target_count // 100 + 1

        print(f"📋 収集設定:")
        print(f"  - NSFW専用モード: ON")
        print(f"  - 1ページあたり: 100件")
        print(f"  - 最大ページ数: {max_pages}")

        while len(collected_items) < target_count and page <= max_pages:
            print(f"\n🔄 Page {page} を収集中...")

            current_params = nsfw_params.copy()
            current_params["page"] = page

            try:
                # API呼び出し
                headers = self._get_headers()
                response = requests.get(
                    self.base_url,
                    params=current_params,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])

                    if not items:
                        print(f"  ⚠️ Page {page}: データなし - 収集終了")
                        break

                    print(f"  ✅ Page {page}: {len(items)}件取得")

                    # NSFW性の検証と保存
                    nsfw_items = self._filter_and_save_nsfw(items)
                    collected_items.extend(nsfw_items)

                    print(f"  🔥 NSFW判定: {len(nsfw_items)}件")

                elif response.status_code == 401:
                    print(f"  ❌ 認証エラー - APIキーが必要な可能性")
                    break
                elif response.status_code == 429:
                    print(f"  ⏳ レート制限 - 60秒待機")
                    time.sleep(60)
                    continue
                else:
                    print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")

            except Exception as e:
                print(f"  💥 エラー: {e}")

            # レート制限対応
            time.sleep(self.request_delay)
            page += 1

        # 2. 特定NSFWモデルからの収集
        nsfw_model_versions = [
            "128078",  # 既知のNSFWモデル
            "101055",  # 成人向けモデル
            # 他の既知NSFWモデルバージョンを追加
        ]

        for version_id in nsfw_model_versions:
            print(f"\n🎯 NSFWモデル {version_id} から収集中...")
            model_items = self._collect_from_version(version_id, 200)
            collected_items.extend(model_items)

            if len(collected_items) >= target_count:
                break

        # 結果統計
        stats = self._analyze_collected_nsfw(collected_items)

        print(f"\n🎉 NSFW収集完了!")
        print(f"  収集総数: {len(collected_items)}件")
        print(f"  明示的表現: {stats['explicit']}件")
        print(f"  性器表現: {stats['genital']}件")
        print(f"  性行為表現: {stats['sexual_acts']}件")

        return stats

    def _filter_and_save_nsfw(self, items: List[Dict]) -> List[Dict]:
        """アイテムをNSFWフィルタリングして保存"""
        nsfw_items = []

        for item in items:
            # プロンプト抽出
            full_prompt = ""
            if 'meta' in item and item['meta']:
                if isinstance(item['meta'], dict):
                    full_prompt = item['meta'].get('prompt', '') or item['meta'].get('Prompt', '')

            if not full_prompt and 'generationProcess' in item:
                full_prompt = item['generationProcess'].get('prompt', '')

            # NSFW判定
            if self._is_explicit_nsfw(full_prompt):
                # データベースに保存
                prompt_data = self._extract_prompt_data(item, full_prompt)
                saved = self._save_to_database(prompt_data)

                if saved:
                    nsfw_items.append(item)

        return nsfw_items

    def _is_explicit_nsfw(self, prompt: str) -> bool:
        """明示的NSFW判定"""
        if not prompt:
            return False

        prompt_lower = prompt.lower()

        # 明示的キーワード
        explicit_keywords = [
            'fuck', 'fucking', 'cum', 'cumming', 'orgasm',
            'pussy', 'cock', 'dick', 'penis', 'vagina',
            'nude', 'naked', 'sex', 'anal', 'oral',
            'nipples', 'breasts', 'ass', 'penetrat',
            'masturbat', 'erotic', 'explicit', 'nsfw'
        ]

        matches = sum(1 for keyword in explicit_keywords if keyword in prompt_lower)
        return matches >= 2  # 2つ以上のキーワードでNSFW判定

    def _collect_from_version(self, version_id: str, max_items: int) -> List[Dict]:
        """特定バージョンから収集"""
        params = {
            "modelVersionId": version_id,
            "limit": 100,
            "nsfw": "X"  # 明示的NSFW要求
        }

        collected = []
        page = 1

        while len(collected) < max_items and page <= 10:  # 最大10ページ
            current_params = params.copy()
            current_params["page"] = page

            try:
                headers = self._get_headers()
                response = requests.get(
                    self.base_url,
                    params=current_params,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])

                    if not items:
                        break

                    nsfw_items = self._filter_and_save_nsfw(items)
                    collected.extend(nsfw_items)

                    print(f"    Page {page}: {len(nsfw_items)} NSFW件")

                else:
                    print(f"    HTTP {response.status_code}")
                    break

            except Exception as e:
                print(f"    エラー: {e}")
                break

            time.sleep(self.request_delay)
            page += 1

        return collected

    def _extract_prompt_data(self, item: Dict, full_prompt: str) -> Dict:
        """アイテムからプロンプトデータを抽出"""
        return {
            'civitai_id': str(item.get('id', '')),
            'full_prompt': full_prompt,
            'negative_prompt': '',
            'quality_score': self._calculate_nsfw_quality_score(full_prompt),
            'reaction_count': item.get('stats', {}).get('likeCount', 0),
            'comment_count': item.get('stats', {}).get('commentCount', 0),
            'download_count': item.get('stats', {}).get('downloadCount', 0),
            'model_name': item.get('model', {}).get('name', ''),
            'model_id': str(item.get('model', {}).get('id', '')),
            'model_version_id': str(item.get('modelVersionId', '')),
            'raw_metadata': str(item)
        }

    def _calculate_nsfw_quality_score(self, prompt: str) -> int:
        """NSFW専用品質スコア計算"""
        if not prompt:
            return 0

        score = 0
        prompt_lower = prompt.lower()

        # 明示的表現ボーナス
        explicit_terms = ['fucking', 'cumming', 'orgasm', 'penetration']
        score += sum(3 for term in explicit_terms if term in prompt_lower)

        # 性器表現ボーナス
        genital_terms = ['pussy', 'cock', 'penis', 'vagina', 'nipples']
        score += sum(4 for term in genital_terms if term in prompt_lower)

        # 詳細度ボーナス
        if len(prompt) > 200:
            score += 2

        return min(score, 50)  # 最大50点

    def _save_to_database(self, prompt_data: Dict) -> bool:
        """データベースに保存"""
        try:
            self.db_manager.save_prompt(prompt_data)
            return True
        except Exception as e:
            print(f"DB保存エラー: {e}")
            return False

    def _analyze_collected_nsfw(self, items: List[Dict]) -> Dict[str, int]:
        """収集されたNSFWの統計分析"""
        stats = {
            'total': len(items),
            'explicit': 0,
            'genital': 0,
            'sexual_acts': 0
        }

        # 簡易分析（実際のプロンプトを再取得して分析）
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()

        # 最近保存されたプロンプトを分析
        cursor.execute("""
            SELECT full_prompt FROM civitai_prompts
            WHERE collected_at >= datetime('now', '-1 hour')
            ORDER BY collected_at DESC
            LIMIT 1000
        """)

        recent_prompts = cursor.fetchall()

        for (prompt,) in recent_prompts:
            prompt_lower = prompt.lower()

            if any(term in prompt_lower for term in ['fucking', 'cumming', 'orgasm']):
                stats['explicit'] += 1
            if any(term in prompt_lower for term in ['pussy', 'cock', 'penis', 'vagina']):
                stats['genital'] += 1
            if any(term in prompt_lower for term in ['sex', 'penetration', 'masturbation']):
                stats['sexual_acts'] += 1

        conn.close()
        return stats

def main():
    """NSFW収集のメイン実行"""
    # APIキーがあればより多くのコンテンツにアクセス可能
    api_key = None  # 必要に応じて設定

    collector = NSFWCivitAICollector(api_key)

    print("🚀 CivitAI NSFW専用収集開始")
    print("=" * 50)

    # 1000件のNSFWコンテンツを目標に収集
    stats = collector.collect_nsfw_content(target_count=1000)

    print(f"\n✅ 収集完了 - 詳細統計:")
    for key, value in stats.items():
        print(f"  {key}: {value}件")

if __name__ == "__main__":
    main()
