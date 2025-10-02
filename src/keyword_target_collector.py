#!/usr/bin/env python3
"""
Keyword-based Target Collection for Comprehensive NSFW Collection
特定キーワードターゲットの収集戦略
"""

import requests
import time
from typing import List, Dict, Any
from collections import defaultdict

class KeywordTargetCollector:
    """キーワードベースのターゲット収集"""

    def __init__(self):
        # 日本語・アニメ系エロティック表現
        self.japanese_erotic = [
            'ahegao', 'paizuri', 'nakadashi', 'bukkake', 'gokkun',
            'shibari', 'kinbaku', 'futanari', 'yuri', 'yaoi',
            'tentacle', 'monster girl', 'catgirl', 'bunny girl',
            'schoolgirl', 'office lady', 'maid', 'nurse'
        ]

        # 妊娠・母乳系
        self.pregnancy_lactation = [
            'pregnant', 'pregnancy', 'belly', 'gravid', 'expecting',
            'lactation', 'breast milk', 'nursing', 'milking',
            'swollen breasts', 'milk drip', 'maternal'
        ]

        # 年齢・体型関連
        self.age_body_types = [
            'milf', 'mature', 'cougar', 'older woman', 'mom',
            'teen', 'young', 'petite', 'slim', 'skinny',
            'thicc', 'chubby', 'bbw', 'curvy', 'voluptuous',
            'athletic', 'muscular', 'fit', 'toned'
        ]

        # レズビアン・バイセクシャル
        self.lesbian_content = [
            'lesbian', 'girl on girl', 'women kissing', 'tribbing',
            'scissoring', 'lesbian oral', 'strap-on lesbian',
            'girl love', 'sapphic', 'wlw', 'bisexual'
        ]

        # グループセックス・パーティー
        self.group_activities = [
            'orgy', 'group sex', 'gangbang', 'train', 'bukkake party',
            'swinger', 'swapping', 'wife sharing', 'cuckold',
            'threesome ffm', 'threesome mmf', 'foursome', 'fivesome'
        ]

        # BDSM詳細
        self.bdsm_detailed = [
            'rope bondage', 'shibari', 'suspension', 'hogtied',
            'spreader bar', 'stocks', 'pillory', 'chastity',
            'orgasm denial', 'edging', 'forced orgasm', 'overstim',
            'impact play', 'spanking', 'paddling', 'caning',
            'needle play', 'wax play', 'electro', 'tens'
        ]

        # 特殊フェチ
        self.special_fetishes = [
            'feet', 'foot fetish', 'toe sucking', 'footjob',
            'armpit', 'belly button', 'navel', 'ear licking',
            'hair fetish', 'long hair', 'ponytail', 'braids',
            'glasses', 'stockings', 'pantyhose', 'high heels'
        ]

    def get_comprehensive_keywords(self) -> Dict[str, List[str]]:
        """包括的キーワードセットを返す"""
        return {
            'japanese_erotic': self.japanese_erotic,
            'pregnancy_lactation': self.pregnancy_lactation,
            'age_body_types': self.age_body_types,
            'lesbian_content': self.lesbian_content,
            'group_activities': self.group_activities,
            'bdsm_detailed': self.bdsm_detailed,
            'special_fetishes': self.special_fetishes
        }

    def search_by_keywords(self, keywords: List[str], model_id: str = None, version_id: str = None,
                          nsfw_level: str = "X", max_per_keyword: int = 50) -> Dict[str, Any]:
        """キーワードベース検索収集"""

        results = {
            'keyword_results': {},
            'total_found': 0,
            'unique_prompts': set(),
            'errors': []
        }

        from src.config import USER_AGENT, REQUEST_TIMEOUT, CIVITAI_API_KEY
        headers = {"User-Agent": USER_AGENT}
        if CIVITAI_API_KEY:
            headers['Authorization'] = f"Bearer {CIVITAI_API_KEY}"

        for keyword in keywords:
            try:
                # 検索パラメータ
                params = {
                    'limit': max_per_keyword,
                    'nsfw': nsfw_level,
                    'sort': 'Most Reactions',
                    'query': keyword  # キーワード検索
                }

                # モデル/バージョン指定
                if version_id:
                    params['modelVersionId'] = version_id
                elif model_id:
                    params['modelId'] = model_id

                response = requests.get(
                    "https://civitai.com/api/v1/images",
                    params=params,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])

                    # プロンプト内容の確認
                    relevant_items = []
                    for item in items:
                        prompt = item.get('meta', {}).get('prompt', '').lower()
                        if keyword.lower() in prompt:
                            relevant_items.append(item)
                            results['unique_prompts'].add(prompt[:200])  # 重複チェック用

                    results['keyword_results'][keyword] = {
                        'found_count': len(relevant_items),
                        'total_retrieved': len(items),
                        'items': relevant_items
                    }

                    results['total_found'] += len(relevant_items)

                else:
                    results['errors'].append(f"{keyword}: HTTP {response.status_code}")

                # API制限対策
                time.sleep(0.5)

            except Exception as e:
                results['errors'].append(f"{keyword}: {str(e)}")

        return results

    def analyze_coverage_gaps(self, existing_keywords: List[str]) -> Dict[str, List[str]]:
        """既存データのカバレッジギャップ分析"""

        all_categories = self.get_comprehensive_keywords()
        gaps = {}

        existing_lower = [kw.lower() for kw in existing_keywords]

        for category, keywords in all_categories.items():
            missing = []
            for keyword in keywords:
                if keyword.lower() not in existing_lower:
                    missing.append(keyword)

            if missing:
                gaps[category] = missing

        return gaps

    def recommend_collection_targets(self, model_analysis: Dict) -> Dict[str, Any]:
        """収集ターゲット推奨"""

        recommendations = {
            'high_priority': [],
            'medium_priority': [],
            'experimental': [],
            'reasoning': {}
        }

        # 既存データ分析に基づく推奨
        existing_sexual_rate = model_analysis.get('sexual_expression_rate', 0)

        if existing_sexual_rate < 0.1:  # 10%未満
            recommendations['high_priority'].extend(self.japanese_erotic[:10])
            recommendations['high_priority'].extend(self.age_body_types[:5])
            recommendations['reasoning']['high_priority'] = "性的表現が少ないため、基本的なエロティック表現を優先"

        elif existing_sexual_rate < 0.3:  # 30%未満
            recommendations['medium_priority'].extend(self.bdsm_detailed[:8])
            recommendations['medium_priority'].extend(self.group_activities[:6])
            recommendations['reasoning']['medium_priority'] = "中程度の性的表現があるため、より専門的な表現を追加"

        else:  # 30%以上
            recommendations['experimental'].extend(self.special_fetishes[:10])
            recommendations['experimental'].extend(self.pregnancy_lactation[:5])
            recommendations['reasoning']['experimental'] = "豊富な性的表現があるため、特殊フェチや専門カテゴリを実験"

        return recommendations

def add_keyword_target_ui():
    """Streamlit UIにキーワードターゲット機能追加"""
    import streamlit as st

    st.markdown("### 🎯 キーワードターゲット収集")

    collector = KeywordTargetCollector()

    # カテゴリ選択
    categories = collector.get_comprehensive_keywords()
    selected_categories = st.multiselect(
        "ターゲットカテゴリ",
        list(categories.keys()),
        format_func=lambda x: {
            'japanese_erotic': '🇯🇵 日本・アニメ系エロ（ahegao, paizuri等）',
            'pregnancy_lactation': '🤱 妊娠・母乳系（pregnant, lactation等）',
            'age_body_types': '👩 年齢・体型（milf, petite, thicc等）',
            'lesbian_content': '👭 レズビアン（lesbian, tribbing等）',
            'group_activities': '👥 グループ（orgy, gangbang等）',
            'bdsm_detailed': '⛓️ BDSM詳細（shibari, edging等）',
            'special_fetishes': '🦶 特殊フェチ（feet, glasses等）'
        }.get(x, x)
    )

    # 選択されたキーワードを表示
    if selected_categories:
        all_selected_keywords = []
        for category in selected_categories:
            all_selected_keywords.extend(categories[category])

        st.write(f"**選択キーワード数**: {len(all_selected_keywords)}個")

        with st.expander("📋 選択されたキーワード一覧"):
            for category in selected_categories:
                st.write(f"**{category}**: {', '.join(categories[category])}")

    # 実行設定
    col1, col2 = st.columns(2)
    with col1:
        max_per_keyword = st.number_input("キーワードあたり最大件数", 10, 100, 30)
        nsfw_level = st.selectbox("NSFWレベル", ["X", "Mature", "Soft"], index=0)
    with col2:
        enable_analysis = st.checkbox("収集後分析", True)
        save_results = st.checkbox("結果保存", True)

    return {
        'collector': collector,
        'selected_categories': selected_categories,
        'max_per_keyword': max_per_keyword,
        'nsfw_level': nsfw_level,
        'enable_analysis': enable_analysis,
        'save_results': save_results
    }
