#!/usr/bin/env python3
"""
Enhanced NSFW Collection Strategy for Streamlit UI
NSFWを含む包括的収集機能の追加実装
"""

import streamlit as st
import sqlite3
from typing import List, Dict, Any
from collections import defaultdict
import requests
import json
import time
from datetime import datetime

class ComprehensiveCollectionStrategy:
    """包括的収集戦略 - NSFW含む多層的アプローチ"""

    def __init__(self):
        # 多層的キーワードデータベース
        self.sexual_keywords = {
            'explicit_genital': [
                'pussy', 'vagina', 'cock', 'penis', 'dick', 'clit', 'labia',
                'vulva', 'anus', 'asshole', 'shaft', 'glans', 'foreskin'
            ],
            'explicit_acts': [
                'sex', 'fucking', 'blowjob', 'handjob', 'footjob', 'titjob', 'boobjob',
                'masturbation', 'masturbate', 'orgasm', 'cum', 'cumshot', 'creampie',
                'gangbang', 'threesome', 'foursome', 'orgy', 'anal', 'oral',
                'deepthroat', 'facefuck', 'rimming', 'cunnilingus', 'fellatio'
            ],
            'sex_positions': [
                'missionary', 'doggy style', 'cowgirl', 'reverse cowgirl', 'spooning',
                'standing', 'sixty nine', '69', 'side by side', 'legs up', 'bent over',
                'on all fours', 'from behind', 'face down ass up', 'spread legs',
                'legs apart', 'squatting', 'kneeling', 'sitting on'
            ],
            'sex_toys': [
                'dildo', 'vibrator', 'sex toy', 'adult toy', 'buttplug', 'butt plug',
                'anal beads', 'strap-on', 'strapon', 'pocket pussy', 'fleshlight',
                'cock ring', 'love egg', 'bullet vibrator', 'wand massager',
                'double dildo', 'realistic dildo', 'glass dildo', 'silicone toy'
            ],
            'body_explicit': [
                'breasts', 'tits', 'boobs', 'nipples', 'ass', 'butt', 'thighs',
                'cleavage', 'nude', 'naked', 'topless', 'bottomless', 'bare breasts',
                'exposed breasts', 'big tits', 'small tits', 'huge breasts',
                'large breasts', 'perky breasts', 'saggy breasts', 'round ass',
                'big ass', 'thick thighs', 'wide hips', 'curvy', 'voluptuous'
            ],
            'fetish_kink': [
                'bdsm', 'bondage', 'dominatrix', 'submissive', 'dominant', 'slave',
                'master', 'mistress', 'latex', 'leather', 'whip', 'chain', 'rope',
                'collar', 'leash', 'gag', 'blindfold', 'handcuffs', 'fetish',
                'kinky', 'roleplay', 'cosplay', 'uniform', 'schoolgirl', 'nurse',
                'maid', 'secretary', 'police', 'military'
            ],
            'clothing_lingerie': [
                'lingerie', 'panties', 'bra', 'stockings', 'fishnet', 'corset',
                'thong', 'bikini', 'micro bikini', 'g-string', 'teddy',
                'babydoll', 'chemise', 'bustier', 'garter belt', 'pantyhose',
                'see-through', 'transparent', 'sheer', 'lace', 'satin', 'silk'
            ],
            'suggestive_mood': [
                'sexy', 'seductive', 'erotic', 'aroused', 'horny', 'lustful',
                'passionate', 'sensual', 'sultry', 'alluring', 'tempting',
                'provocative', 'naughty', 'playful', 'flirty', 'teasing'
            ]
        }

        # 収集戦略パターン
        self.collection_strategies = {
            'standard': {'nsfw': 'Soft', 'sort': 'Most Reactions'},
            'nsfw_explicit': {'nsfw': 'X', 'sort': 'Most Reactions'},
            'nsfw_recent': {'nsfw': 'X', 'sort': 'Newest'},
            'comprehensive_soft': {'nsfw': 'Soft', 'sort': 'Newest'},
            'comprehensive_none': {'nsfw': 'None', 'sort': 'Most Reactions'},
        }

    def get_enhanced_ui_components(self):
        """Streamlit UIコンポーネントの拡張設定を返す"""

        st.markdown("### 🔥 包括的収集戦略（NSFW対応）")

        # 収集モード選択
        collection_mode = st.selectbox(
            "収集モード",
            [
                "comprehensive_multi", "nsfw_explicit_only", "standard_safe",
                "targeted_keywords", "experimental_deep"
            ],
            format_func=lambda x: {
                "comprehensive_multi": "🎯 包括的マルチ収集（推奨）",
                "nsfw_explicit_only": "🔞 NSFW明示的のみ",
                "standard_safe": "✅ 標準安全モード",
                "targeted_keywords": "🎪 キーワードターゲット収集",
                "experimental_deep": "🧪 実験的深層収集"
            }[x]
        )

        # 詳細設定
        with st.expander("🛠️ 詳細設定"):
            # NSFWレベル設定
            nsfw_levels = st.multiselect(
                "NSFWレベル（複数選択可）",
                ["None", "Soft", "Mature", "X"],
                default=["Soft", "X"] if collection_mode == "comprehensive_multi" else ["X"]
            )

            # ソート戦略
            sort_strategies = st.multiselect(
                "ソート戦略（複数選択可）",
                ["Most Reactions", "Most Downloads", "Most Likes", "Most Discussed", "Newest"],
                default=["Most Reactions", "Newest"]
            )

            # キーワードフィルタリング
            enable_keyword_filtering = st.checkbox("🔍 キーワードベース後処理フィルタリング", True)

            if enable_keyword_filtering:
                selected_categories = st.multiselect(
                    "収集対象キーワードカテゴリ",
                    list(self.sexual_keywords.keys()),
                    default=list(self.sexual_keywords.keys())
                )

                # カスタムキーワード追加
                custom_keywords = st.text_area(
                    "追加キーワード（カンマ区切り）",
                    placeholder="例: ahegao, paizuri, nakadashi, hentai",
                    help="日本語のエロティック表現や専門用語を追加可能"
                )

        # 収集量設定
        col1, col2 = st.columns(2)
        with col1:
            max_per_strategy = st.number_input("戦略あたり最大件数", 50, 2000, 500)
        with col2:
            parallel_requests = st.number_input("並列リクエスト数", 1, 5, 2)

        return {
            'collection_mode': collection_mode,
            'nsfw_levels': nsfw_levels,
            'sort_strategies': sort_strategies,
            'enable_keyword_filtering': enable_keyword_filtering,
            'selected_categories': selected_categories if enable_keyword_filtering else [],
            'custom_keywords': [kw.strip() for kw in custom_keywords.split(',') if kw.strip()] if enable_keyword_filtering and custom_keywords else [],
            'max_per_strategy': max_per_strategy,
            'parallel_requests': parallel_requests
        }

    def execute_comprehensive_collection(self, model_id: str, version_id: str, settings: Dict):
        """包括的収集の実行"""

        collection_results = {
            'total_collected': 0,
            'by_strategy': {},
            'sexual_analysis': defaultdict(int),
            'new_keywords_found': set(),
            'errors': []
        }

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # 各戦略の実行
            strategies_to_run = self._build_collection_strategies(settings)

            for i, (strategy_name, params) in enumerate(strategies_to_run.items()):
                status_text.text(f"実行中: {strategy_name}")
                progress = (i + 1) / len(strategies_to_run)
                progress_bar.progress(progress)

                try:
                    result = self._execute_single_strategy(
                        model_id, version_id, params, settings['max_per_strategy']
                    )

                    collection_results['by_strategy'][strategy_name] = result
                    collection_results['total_collected'] += result['collected_count']

                    # 性的表現分析
                    for item in result['items']:
                        sexual_keywords = self._analyze_sexual_content(
                            item.get('meta', {}).get('prompt', ''),
                            settings['selected_categories']
                        )

                        for keyword in sexual_keywords:
                            collection_results['sexual_analysis'][keyword] += 1
                            collection_results['new_keywords_found'].add(keyword)

                    # 小休止（API制限対策）
                    time.sleep(1)

                except Exception as e:
                    error_msg = f"{strategy_name}: {str(e)}"
                    collection_results['errors'].append(error_msg)
                    st.warning(f"戦略 {strategy_name} でエラー: {e}")

            # 結果表示
            self._display_collection_results(collection_results)

            return collection_results

        except Exception as e:
            st.error(f"包括的収集でエラーが発生しました: {e}")
            return collection_results

        finally:
            progress_bar.empty()
            status_text.empty()

    def _build_collection_strategies(self, settings: Dict) -> Dict[str, Dict]:
        """設定に基づいて収集戦略を構築"""
        strategies = {}

        mode = settings['collection_mode']

        if mode == "comprehensive_multi":
            # すべてのNSFWレベル×ソート戦略の組み合わせ
            for nsfw_level in settings['nsfw_levels']:
                for sort_strategy in settings['sort_strategies']:
                    strategy_name = f"{nsfw_level}_{sort_strategy.replace(' ', '_')}"
                    strategies[strategy_name] = {
                        'nsfw': nsfw_level,
                        'sort': sort_strategy
                    }

        elif mode == "nsfw_explicit_only":
            # 明示的NSFWのみ
            for sort_strategy in settings['sort_strategies']:
                strategy_name = f"X_{sort_strategy.replace(' ', '_')}"
                strategies[strategy_name] = {
                    'nsfw': 'X',
                    'sort': sort_strategy
                }

        elif mode == "targeted_keywords":
            # キーワードベースの戦略的収集
            strategies["targeted_nsfw"] = {'nsfw': 'X', 'sort': 'Most Reactions'}
            strategies["targeted_soft"] = {'nsfw': 'Soft', 'sort': 'Most Reactions'}

        # その他のモードも同様に実装...

        return strategies

    def _execute_single_strategy(self, model_id: str, version_id: str, params: Dict, max_items: int) -> Dict:
        """単一戦略の実行"""
        try:
            # 直接APIを呼び出し（既存のコレクターを使わずにnsfwパラメータ対応）
            from src.config import USER_AGENT, REQUEST_TIMEOUT, CIVITAI_API_KEY

            # API呼び出しパラメータ
            api_params = {
                'limit': min(max_items, 200),  # API制限考慮
                'nsfw': params['nsfw'],
                'sort': params['sort']
            }

            # モデル/バージョン指定
            if version_id and str(version_id).strip():
                api_params['modelVersionId'] = str(version_id).strip()
            elif model_id and str(model_id).strip():
                api_params['modelId'] = str(model_id).strip()

            # APIリクエスト実行
            headers = {"User-Agent": USER_AGENT}
            if CIVITAI_API_KEY:
                headers['Authorization'] = f"Bearer {CIVITAI_API_KEY}"

            response = requests.get(
                "https://civitai.com/api/v1/images",
                params=api_params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])

                return {
                    'collected_count': len(items),
                    'items': items,
                    'params': api_params,
                    'success': True,
                    'total_available': data.get('metadata', {}).get('totalItems'),
                    'next_page': data.get('metadata', {}).get('nextPage')
                }
            else:
                return {
                    'collected_count': 0,
                    'items': [],
                    'params': api_params,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }

        except Exception as e:
            return {
                'collected_count': 0,
                'items': [],
                'params': api_params,
                'success': False,
                'error': str(e)
            }

    def _analyze_sexual_content(self, prompt_text: str, selected_categories: List[str]) -> List[str]:
        """プロンプトの性的表現分析"""
        if not prompt_text:
            return []

        prompt_lower = prompt_text.lower()
        found_keywords = []

        for category in selected_categories:
            if category in self.sexual_keywords:
                for keyword in self.sexual_keywords[category]:
                    if keyword in prompt_lower:
                        found_keywords.append(keyword)

        return found_keywords

    def _display_collection_results(self, results: Dict):
        """収集結果の表示"""
        st.markdown("### 📊 収集結果")

        # 概要統計
        col1, col2, col3 = st.columns(3)
        col1.metric("総収集件数", results['total_collected'])
        col2.metric("実行戦略数", len(results['by_strategy']))
        col3.metric("発見キーワード数", len(results['new_keywords_found']))

        # 戦略別結果
        if results['by_strategy']:
            st.markdown("#### 戦略別収集結果")
            strategy_df_data = []
            for strategy_name, result in results['by_strategy'].items():
                strategy_df_data.append({
                    '戦略': strategy_name,
                    '収集件数': result['collected_count'],
                    '成功': '✅' if result['success'] else '❌',
                    'NSFWレベル': result['params'].get('nsfw', 'N/A'),
                    'ソート': result['params'].get('sort', 'N/A')
                })

            if strategy_df_data:
                import pandas as pd
                strategy_df = pd.DataFrame(strategy_df_data)
                st.dataframe(strategy_df, use_container_width=True)

        # 性的表現分析
        if results['sexual_analysis']:
            st.markdown("#### 🔥 発見された性的表現")

            # トップキーワード
            top_keywords = sorted(
                results['sexual_analysis'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**トップ20キーワード:**")
                for keyword, count in top_keywords:
                    st.write(f"- `{keyword}`: {count}件")

            with col2:
                # カテゴリー別統計
                category_stats = defaultdict(int)
                for keyword, count in results['sexual_analysis'].items():
                    for category, keywords in self.sexual_keywords.items():
                        if keyword in keywords:
                            category_stats[category] += count

                if category_stats:
                    st.markdown("**カテゴリー別統計:**")
                    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                        st.write(f"- {category}: {count}件")

        # エラー表示
        if results['errors']:
            st.markdown("#### ⚠️ エラー")
            for error in results['errors']:
                st.error(error)


def add_comprehensive_collection_to_streamlit():
    """
    Streamlit UIに包括的収集機能を追加
    既存のstreamlit_app.pyの収集タブに統合するためのコード
    """

    # インスタンス化
    strategy = ComprehensiveCollectionStrategy()

    # UI設定の取得
    settings = strategy.get_enhanced_ui_components()

    return strategy, settings

# 使用例（streamlit_app.pyに統合する際の参考）
"""
# streamlit_app.py の収集タブ内に追加:

with tab_collect:
    st.header("データ収集（CivitAI API）")

    # 既存の基本設定...

    # 新しい包括的収集機能を追加
    st.markdown("---")

    # 包括的収集機能の追加
    strategy, settings = add_comprehensive_collection_to_streamlit()

    # 実行ボタン
    if st.button("🚀 包括的収集実行", type="primary"):
        if version_id:
            with st.spinner("包括的収集を実行中..."):
                results = strategy.execute_comprehensive_collection(
                    model_id, version_id, settings
                )
            st.success("包括的収集が完了しました！")
        else:
            st.error("Version IDを指定してください")
"""
