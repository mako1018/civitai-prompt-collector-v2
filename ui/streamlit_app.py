"""
CivitAI Prompt Collector - Streamlit Web UI
データベース内容の表示・分析・エクスポート機能を提供
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config import CATEGORIES, DEFAULT_DB_PATH
    from src.database import DatabaseManager
    from src.visualizer import VisualizationManager
except ImportError:
    st.error("モジュールの読み込みに失敗しました。プロジェクト構造を確認してください。")
    st.stop()

# ページ設定
st.set_page_config(
    page_title="CivitAI Prompt Collector",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .category-badge {
        background-color: #e1f5fe;
        color: #01579b;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.1rem;
        display: inline-block;
    }
    .prompt-card {
        background-color: #ffffff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """データベースからデータを読み込み"""
    try:
        db_manager = DatabaseManager()

        # プロンプトデータと分類結果を結合して取得
        query = """
        SELECT
            p.id,
            p.positive_prompt,
            p.negative_prompt,
            p.model_name,
            p.model_id,
            p.created_at,
            pc.category,
            pc.confidence
        FROM civitai_prompts p
        LEFT JOIN prompt_categories pc ON p.id = pc.prompt_id
        ORDER BY p.created_at DESC
        """

        conn = db_manager._get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

@st.cache_data
def get_database_stats():
    """データベースの統計情報を取得"""
    try:
        db_manager = DatabaseManager()

        # 基本統計
        total_prompts = db_manager.get_prompt_count()

        # カテゴリ統計
        query = """
        SELECT category, COUNT(*) as count, AVG(confidence) as avg_confidence
        FROM prompt_categories
        GROUP BY category
        ORDER BY count DESC
        """

        conn = db_manager._get_connection()
        category_stats = pd.read_sql_query(query, conn)
        conn.close()

        return {
            'total_prompts': total_prompts,
            'total_categorized': len(category_stats) > 0,
            'category_stats': category_stats
        }
    except Exception as e:
        st.error(f"統計情報の取得に失敗しました: {e}")
        return {'total_prompts': 0, 'total_categorized': False, 'category_stats': pd.DataFrame()}

def create_category_distribution_chart(df):
    """カテゴリ分布チャートを作成"""
    if df.empty:
        return None

    category_counts = df['category'].value_counts()

    # カラーマップ
    colors = {
        'NSFW': '#ff6b6b',
        'style': '#4ecdc4',
        'lighting': '#ffe66d',
        'composition': '#a8e6cf',
        'mood': '#ff8b94',
        'basic': '#b4a7d6',
        'technical': '#d4a574'
    }

    fig = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title="カテゴリ分布",
        color_discrete_map=colors,
        hover_data=['value']
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        font=dict(size=12),
        showlegend=True,
        height=500
    )

    return fig

def create_confidence_histogram(df):
    """信頼度ヒストグラムを作成"""
    if df.empty or 'confidence' not in df.columns:
        return None

    fig = px.histogram(
        df,
        x='confidence',
        nbins=20,
        title='分類信頼度の分布',
        labels={'confidence': '信頼度', 'count': 'プロンプト数'},
        color_discrete_sequence=['#1f77b4']
    )

    fig.update_layout(
        xaxis_title="信頼度",
        yaxis_title="プロンプト数",
        font=dict(size=12),
        height=400
    )

    return fig

def display_prompt_card(row):
    """プロンプトカードを表示"""
    with st.container():
        st.markdown(f"""
        <div class="prompt-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong>ID: {row['id']}</strong>
                <span class="category-badge">{row['category']} ({row['confidence']:.2f})</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>モデル:</strong> {row['model_name']} (ID: {row['model_id']})
            </div>
            <div style="margin-bottom: 0.5rem;">
                <strong>作成日:</strong> {row['created_at']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # プロンプト内容をexpanderで表示
        with st.expander("プロンプト詳細を表示"):
            st.text_area("ポジティブプロンプト", value=row['positive_prompt'], height=100, disabled=True)
            if pd.notna(row['negative_prompt']) and row['negative_prompt'].strip():
                st.text_area("ネガティブプロンプト", value=row['negative_prompt'], height=80, disabled=True)

def main():
    """メイン関数"""

    # タイトル
    st.title("🎨 CivitAI Prompt Collector")
    st.markdown("プロンプトデータの分析・表示・エクスポートツール")

    # データ読み込み
    df = load_data()
    stats = get_database_stats()

    if df.empty:
        st.warning("データが見つかりません。まずはデータ収集を実行してください。")
        st.code("python main.py --collect-only", language="bash")
        return

    # サイドバー: フィルター機能
    st.sidebar.header("📊 データ統計")
    st.sidebar.metric("総プロンプト数", stats['total_prompts'])
    st.sidebar.metric("分類済み数", len(df[df['category'].notna()]))

    # カテゴリフィルター
    st.sidebar.header("🔍 フィルター")

    # カテゴリ選択
    available_categories = df['category'].dropna().unique().tolist()
    selected_categories = st.sidebar.multiselect(
        "カテゴリで絞り込み",
        options=available_categories,
        default=available_categories
    )

    # 信頼度フィルター
    if 'confidence' in df.columns and df['confidence'].notna().any():
        confidence_range = st.sidebar.slider(
            "信頼度で絞り込み",
            min_value=float(df['confidence'].min()),
            max_value=float(df['confidence'].max()),
            value=(float(df['confidence'].min()), float(df['confidence'].max())),
            step=0.01
        )
    else:
        confidence_range = None

    # データフィルタリング
    filtered_df = df.copy()
    if selected_categories:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]

    if confidence_range:
        filtered_df = filtered_df[
            (filtered_df['confidence'] >= confidence_range[0]) &
            (filtered_df['confidence'] <= confidence_range[1])
        ]

    # メインコンテンツ
    tab1, tab2, tab3, tab4 = st.tabs(["📊 ダッシュボード", "📝 プロンプト一覧", "📈 詳細分析", "💾 データエクスポート"])

    with tab1:
        st.header("ダッシュボード")

        # 統計サマリー
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("表示中のプロンプト", len(filtered_df))
        with col2:
            if 'confidence' in filtered_df.columns:
                avg_confidence = filtered_df['confidence'].mean()
                st.metric("平均信頼度", f"{avg_confidence:.2f}")
            else:
                st.metric("平均信頼度", "N/A")
        with col3:
            unique_models = filtered_df['model_name'].nunique()
            st.metric("使用モデル数", unique_models)
        with col4:
            categories_count = filtered_df['category'].nunique()
            st.metric("カテゴリ数", categories_count)

        # グラフ表示
        col1, col2 = st.columns(2)

        with col1:
            # カテゴリ分布
            pie_chart = create_category_distribution_chart(filtered_df)
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)

        with col2:
            # 信頼度ヒストグラム
            hist_chart = create_confidence_histogram(filtered_df)
            if hist_chart:
                st.plotly_chart(hist_chart, use_container_width=True)

    with tab2:
        st.header("プロンプト一覧")

        # 表示件数選択
        display_count = st.selectbox("表示件数", [10, 25, 50, 100, "全て"], index=0)

        if display_count == "全て":
            display_df = filtered_df
        else:
            display_df = filtered_df.head(display_count)

        st.write(f"表示中: {len(display_df)} / {len(filtered_df)} 件")

        # プロンプトカード表示
        for idx, row in display_df.iterrows():
            display_prompt_card(row)

    with tab3:
        st.header("詳細分析")

        # カテゴリ別統計
        if not stats['category_stats'].empty:
            st.subheader("カテゴリ別統計")

            category_chart = px.bar(
                stats['category_stats'],
                x='category',
                y='count',
                title='カテゴリ別プロンプト数',
                labels={'count': 'プロンプト数', 'category': 'カテゴリ'},
                color='avg_confidence',
                color_continuous_scale='viridis'
            )
            st.plotly_chart(category_chart, use_container_width=True)

            # 統計テーブル
            st.dataframe(stats['category_stats'], use_container_width=True)

        # モデル別統計
        st.subheader("モデル別統計")
        model_stats = filtered_df['model_name'].value_counts().head(10)

        model_chart = px.bar(
            x=model_stats.values,
            y=model_stats.index,
            orientation='h',
            title='上位10モデル使用頻度',
            labels={'x': 'プロンプト数', 'y': 'モデル名'}
        )
        st.plotly_chart(model_chart, use_container_width=True)

    with tab4:
        st.header("データエクスポート")

        # CSVダウンロード
        st.subheader("CSVエクスポート")

        # エクスポート用データ準備
        export_df = filtered_df.copy()

        # カラム選択
        available_columns = export_df.columns.tolist()
        selected_columns = st.multiselect(
            "エクスポートするカラムを選択",
            options=available_columns,
            default=available_columns
        )

        if selected_columns:
            export_df = export_df[selected_columns]

        # プレビュー
        st.subheader("プレビュー")
        st.dataframe(export_df.head(5), use_container_width=True)

        # ダウンロードボタン
        csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv_data,
            file_name=f"civitai_prompts_{len(export_df)}件.csv",
            mime="text/csv"
        )

        st.info(f"エクスポート対象: {len(export_df)} 件")

if __name__ == "__main__":
    main()
