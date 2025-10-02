#!/usr/bin/env python3
"""
データ統計管理・可視化システム

収集データの統計分析と傾向把握のためのダッシュボード機能
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
import json
import re
from collections import Counter

class StatisticsManager:
    def __init__(self, db_path: str = "data/civitai_dataset.db"):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_basic_stats(self) -> dict:
        """基本統計情報取得"""
        with self.get_connection() as conn:
            # 基本カウント
            basic_query = """
                SELECT
                    COUNT(*) as total_prompts,
                    COUNT(DISTINCT model_name) as unique_models,
                    COUNT(DISTINCT model_version_id) as unique_versions,
                    AVG(quality_score) as avg_quality,
                    AVG(reaction_count) as avg_reactions,
                    AVG(prompt_length) as avg_length,
                    MIN(collected_at) as first_collected,
                    MAX(collected_at) as last_collected
                FROM civitai_prompts
            """

            basic_df = pd.read_sql_query(basic_query, conn)

            # 品質分布
            quality_query = """
                SELECT
                    CASE
                        WHEN quality_score >= 500 THEN 'Very High (500+)'
                        WHEN quality_score >= 100 THEN 'High (100-499)'
                        WHEN quality_score >= 50 THEN 'Medium (50-99)'
                        WHEN quality_score >= 10 THEN 'Low (10-49)'
                        ELSE 'Very Low (0-9)'
                    END as quality_tier,
                    COUNT(*) as count
                FROM civitai_prompts
                GROUP BY quality_tier
                ORDER BY MIN(quality_score) DESC
            """

            quality_df = pd.read_sql_query(quality_query, conn)

            return {
                'basic': basic_df.iloc[0].to_dict(),
                'quality_distribution': quality_df
            }

    def analyze_prompt_trends(self) -> dict:
        """プロンプトトレンド分析"""
        with self.get_connection() as conn:
            # 時系列データ
            timeline_query = """
                SELECT
                    DATE(collected_at) as collection_date,
                    COUNT(*) as daily_count,
                    AVG(quality_score) as daily_avg_quality
                FROM civitai_prompts
                WHERE collected_at IS NOT NULL
                GROUP BY DATE(collected_at)
                ORDER BY collection_date
            """

            timeline_df = pd.read_sql_query(timeline_query, conn)

            # 長さ分布
            length_query = """
                SELECT
                    CASE
                        WHEN prompt_length >= 1000 THEN 'Very Long (1000+)'
                        WHEN prompt_length >= 500 THEN 'Long (500-999)'
                        WHEN prompt_length >= 200 THEN 'Medium (200-499)'
                        WHEN prompt_length >= 50 THEN 'Short (50-199)'
                        ELSE 'Very Short (0-49)'
                    END as length_category,
                    COUNT(*) as count,
                    AVG(quality_score) as avg_quality
                FROM civitai_prompts
                GROUP BY length_category
                ORDER BY MIN(prompt_length)
            """

            length_df = pd.read_sql_query(length_query, conn)

            return {
                'timeline': timeline_df,
                'length_distribution': length_df
            }

    def analyze_model_performance(self) -> dict:
        """モデル性能分析"""
        with self.get_connection() as conn:
            model_query = """
                SELECT
                    model_name,
                    COUNT(*) as prompt_count,
                    AVG(quality_score) as avg_quality,
                    MAX(quality_score) as max_quality,
                    AVG(reaction_count) as avg_reactions,
                    AVG(prompt_length) as avg_length
                FROM civitai_prompts
                WHERE model_name IS NOT NULL
                GROUP BY model_name
                HAVING prompt_count >= 5
                ORDER BY avg_quality DESC
            """

            model_df = pd.read_sql_query(model_query, conn)

            return {'models': model_df}

    def extract_keyword_trends(self) -> dict:
        """キーワードトレンド分析"""
        with self.get_connection() as conn:
            # 全プロンプト取得
            cursor = conn.cursor()
            cursor.execute("SELECT full_prompt, quality_score FROM civitai_prompts WHERE full_prompt IS NOT NULL")
            prompts_data = cursor.fetchall()

            # キーワード抽出・分析
            keyword_stats = Counter()
            quality_by_keyword = {}

            # 一般的なキーワード定義
            target_keywords = [
                'masterpiece', 'best quality', 'high quality', 'detailed', 'ultra detailed',
                'realistic', 'photorealistic', 'anime', 'portrait', 'landscape',
                '8k', '4k', 'high resolution', 'sharp', 'focus', 'depth of field',
                'lighting', 'cinematic', 'dramatic', 'beautiful', 'stunning',
                'girl', 'woman', 'man', 'boy', 'character', 'background'
            ]

            for prompt, quality in prompts_data:
                if not prompt:
                    continue

                prompt_lower = prompt.lower()
                for keyword in target_keywords:
                    if keyword in prompt_lower:
                        keyword_stats[keyword] += 1
                        if keyword not in quality_by_keyword:
                            quality_by_keyword[keyword] = []
                        quality_by_keyword[keyword].append(quality)

            # 品質統計計算
            keyword_quality_stats = {}
            for keyword, qualities in quality_by_keyword.items():
                if len(qualities) >= 5:  # 5件以上のデータがあるもののみ
                    keyword_quality_stats[keyword] = {
                        'count': len(qualities),
                        'avg_quality': sum(qualities) / len(qualities),
                        'max_quality': max(qualities),
                        'min_quality': min(qualities)
                    }

            return {
                'keyword_frequency': dict(keyword_stats.most_common(20)),
                'keyword_quality': keyword_quality_stats
            }

    def generate_recommendations(self) -> dict:
        """データに基づく推奨事項生成"""
        stats = self.get_basic_stats()
        trends = self.analyze_prompt_trends()
        models = self.analyze_model_performance()
        keywords = self.extract_keyword_trends()

        recommendations = {
            'collection_strategy': [],
            'prompt_optimization': [],
            'model_selection': [],
            'data_quality': []
        }

        # 収集戦略推奨
        avg_quality = stats['basic']['avg_quality']
        if avg_quality < 50:
            recommendations['collection_strategy'].append(
                "平均品質が低め（{:.1f}）。より高品質なプロンプトの収集を重点化".format(avg_quality)
            )

        # プロンプト最適化推奨
        best_keywords = sorted(keywords['keyword_quality'].items(),
                              key=lambda x: x[1]['avg_quality'], reverse=True)[:5]

        recommendations['prompt_optimization'].append(
            f"高品質プロンプトに頻出のキーワード: {[k[0] for k in best_keywords]}"
        )

        # モデル選択推奨
        if not models['models'].empty:
            top_model = models['models'].iloc[0]
            recommendations['model_selection'].append(
                f"最高性能モデル: {top_model['model_name']} (平均品質: {top_model['avg_quality']:.1f})"
            )

        # データ品質推奨
        total_prompts = stats['basic']['total_prompts']
        if total_prompts < 1000:
            recommendations['data_quality'].append(
                f"データ量が少なめ（{total_prompts}件）。より多くのサンプル収集を推奨"
            )

        return recommendations

def create_statistics_dashboard():
    """Streamlit統計ダッシュボード"""
    st.set_page_config(page_title="CivitAI プロンプト統計", layout="wide")

    st.title("📊 CivitAI プロンプトデータ統計ダッシュボード")

    # 統計マネージャー初期化
    stats_manager = StatisticsManager()

    # サイドバー
    st.sidebar.header("📋 分析オプション")
    show_basic = st.sidebar.checkbox("基本統計", value=True)
    show_trends = st.sidebar.checkbox("トレンド分析", value=True)
    show_models = st.sidebar.checkbox("モデル分析", value=True)
    show_keywords = st.sidebar.checkbox("キーワード分析", value=True)
    show_recommendations = st.sidebar.checkbox("推奨事項", value=True)

    # メイン表示
    if show_basic:
        st.header("🎯 基本統計")

        try:
            basic_stats = stats_manager.get_basic_stats()
            basic = basic_stats['basic']

            # メトリクス表示
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("総プロンプト数", f"{basic['total_prompts']:,}")
            with col2:
                st.metric("ユニークモデル数", f"{basic['unique_models']:,}")
            with col3:
                st.metric("平均品質スコア", f"{basic['avg_quality']:.1f}")
            with col4:
                st.metric("平均文字数", f"{basic['avg_length']:.0f}")

            # 品質分布
            quality_dist = basic_stats['quality_distribution']
            fig_quality = px.pie(quality_dist, values='count', names='quality_tier',
                               title="品質スコア分布")
            st.plotly_chart(fig_quality, use_container_width=True)

        except Exception as e:
            st.error(f"基本統計の取得に失敗: {str(e)}")

    if show_trends:
        st.header("📈 トレンド分析")

        try:
            trend_stats = stats_manager.analyze_prompt_trends()

            # タイムライン
            if not trend_stats['timeline'].empty:
                timeline_df = trend_stats['timeline']
                timeline_df['collection_date'] = pd.to_datetime(timeline_df['collection_date'])

                fig_timeline = px.line(timeline_df, x='collection_date', y='daily_count',
                                     title="日別収集数推移")
                st.plotly_chart(fig_timeline, use_container_width=True)

            # 長さ分布
            length_dist = trend_stats['length_distribution']
            fig_length = px.bar(length_dist, x='length_category', y='count',
                              color='avg_quality', title="プロンプト長さ分布")
            st.plotly_chart(fig_length, use_container_width=True)

        except Exception as e:
            st.error(f"トレンド分析に失敗: {str(e)}")

    if show_models:
        st.header("🤖 モデル性能分析")

        try:
            model_stats = stats_manager.analyze_model_performance()
            models_df = model_stats['models']

            if not models_df.empty:
                # トップ10モデル表示
                st.subheader("トップ10モデル（平均品質順）")
                top_models = models_df.head(10)

                fig_models = px.scatter(top_models, x='prompt_count', y='avg_quality',
                                      size='max_quality', hover_name='model_name',
                                      title="モデル性能散布図")
                st.plotly_chart(fig_models, use_container_width=True)

                # 詳細データテーブル
                st.dataframe(top_models, use_container_width=True)
            else:
                st.warning("十分なモデルデータがありません")

        except Exception as e:
            st.error(f"モデル分析に失敗: {str(e)}")

    if show_keywords:
        st.header("🏷️ キーワード分析")

        try:
            keyword_stats = stats_manager.extract_keyword_trends()

            # 頻出キーワード
            st.subheader("頻出キーワード TOP20")
            freq_data = keyword_stats['keyword_frequency']
            freq_df = pd.DataFrame(list(freq_data.items()), columns=['keyword', 'frequency'])

            fig_freq = px.bar(freq_df.head(15), x='frequency', y='keyword',
                            orientation='h', title="キーワード出現頻度")
            st.plotly_chart(fig_freq, use_container_width=True)

            # キーワード品質相関
            st.subheader("キーワード品質相関")
            quality_data = keyword_stats['keyword_quality']
            quality_df = pd.DataFrame.from_dict(quality_data, orient='index')

            if not quality_df.empty:
                quality_df = quality_df.reset_index().rename(columns={'index': 'keyword'})
                quality_df = quality_df.sort_values('avg_quality', ascending=False).head(15)

                fig_quality_kw = px.scatter(quality_df, x='count', y='avg_quality',
                                          size='max_quality', hover_name='keyword',
                                          title="キーワード使用頻度 vs 平均品質")
                st.plotly_chart(fig_quality_kw, use_container_width=True)

        except Exception as e:
            st.error(f"キーワード分析に失敗: {str(e)}")

    if show_recommendations:
        st.header("💡 データドリブン推奨事項")

        try:
            recommendations = stats_manager.generate_recommendations()

            for category, items in recommendations.items():
                if items:
                    st.subheader(category.replace('_', ' ').title())
                    for item in items:
                        st.write(f"• {item}")

        except Exception as e:
            st.error(f"推奨事項生成に失敗: {str(e)}")

    # フッター情報
    st.sidebar.markdown("---")
    st.sidebar.info("💡 このダッシュボードは収集データをリアルタイム分析し、ComfyUI用プロンプト最適化の洞察を提供します。")

if __name__ == "__main__":
    create_statistics_dashboard()
