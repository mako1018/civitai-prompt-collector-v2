#!/usr/bin/env python3
"""
シンプルなプロンプト分析アプリ - 実データベース対応版
"""
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from collections import Counter
import numpy as np

# ページ設定
st.set_page_config(
    page_title="Civitai プロンプト分析ツール",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlitの警告を無効化（この設定は現在のバージョンでは不要）
# st.set_option('deprecation.showPyplotGlobalUse', False)

def get_database_connection():
    """データベース接続を取得"""
    return sqlite3.connect('data/civitai_dataset.db')

@st.cache_data
def load_prompt_data():
    """プロンプトデータを読み込み"""
    try:
        conn = get_database_connection()
        
        query = """
        SELECT 
            id,
            civitai_id,
            full_prompt,
            negative_prompt,
            quality_score,
            reaction_count,
            comment_count,
            download_count,
            prompt_length,
            tag_count,
            model_name,
            model_id,
            collected_at,
            model_version_id
        FROM civitai_prompts 
        WHERE full_prompt IS NOT NULL
        ORDER BY quality_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # データ型の調整
        numeric_columns = ['quality_score', 'reaction_count', 'comment_count', 'download_count', 'prompt_length', 'tag_count']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame()

def analyze_prompt_structure(prompt_text):
    """プロンプト構造を分析"""
    if not prompt_text:
        return {}
    
    # 基本統計
    length = len(prompt_text)
    word_count = len(prompt_text.split())
    
    # カンマ区切りの要素数
    comma_elements = [elem.strip() for elem in prompt_text.split(',') if elem.strip()]
    
    # 括弧の種類と数
    parentheses_count = prompt_text.count('(') + prompt_text.count(')')
    square_brackets_count = prompt_text.count('[') + prompt_text.count(']')
    
    # 重み指定パターン (:数値)
    weight_pattern = r':\s*\d*\.?\d+'
    weights = re.findall(weight_pattern, prompt_text)
    
    # ネガティブプロンプトキーワード
    negative_keywords = ['bad', 'ugly', 'blurry', 'low quality', 'worst', 'error', 'cropped']
    negative_count = sum(1 for keyword in negative_keywords if keyword.lower() in prompt_text.lower())
    
    return {
        'length': length,
        'word_count': word_count,
        'comma_elements': len(comma_elements),
        'parentheses_count': parentheses_count,
        'square_brackets_count': square_brackets_count,
        'weight_specifications': len(weights),
        'negative_keywords': negative_count,
        'elements': comma_elements[:10]  # 最初の10要素
    }

def extract_keywords(df, min_frequency=3):
    """プロンプトからキーワードを抽出"""
    all_keywords = []
    
    for prompt in df['full_prompt'].dropna():
        # カンマ区切りで分割
        elements = [elem.strip().lower() for elem in prompt.split(',')]
        
        # 重み指定や括弧を除去
        clean_elements = []
        for elem in elements:
            # 重み指定を除去 (:数値)
            elem = re.sub(r':\s*\d*\.?\d+', '', elem)
            # 括弧を除去
            elem = re.sub(r'[\(\)\[\]{}]', '', elem)
            # 空白文字の正規化
            elem = elem.strip()
            if elem and len(elem) > 2:  # 2文字以上のキーワードのみ
                clean_elements.append(elem)
        
        all_keywords.extend(clean_elements)
    
    # 頻度カウント
    keyword_counts = Counter(all_keywords)
    
    # 最小頻度以上のキーワードのみ返す
    return {k: v for k, v in keyword_counts.items() if v >= min_frequency}

def main():
    st.title("📊 Civitai プロンプト分析ツール")
    st.markdown("収集されたプロンプトデータの詳細分析")
    
    # データ読み込み
    with st.spinner("データを読み込み中..."):
        df = load_prompt_data()
    
    if df.empty:
        st.error("データが見つかりません。収集を開始してください。")
        return
    
    # サイドバー - データ概要
    st.sidebar.header("📈 データ概要")
    st.sidebar.metric("総プロンプト数", len(df))
    st.sidebar.metric("平均品質スコア", f"{df['quality_score'].mean():.1f}")
    st.sidebar.metric("平均プロンプト長", f"{df['prompt_length'].mean():.0f}")
    
    # メインコンテンツ - タブ形式
    tab1, tab2, tab3, tab4 = st.tabs(["📊 基本統計", "🔍 プロンプト分析", "🏷️ キーワード分析", "📋 データ詳細"])
    
    with tab1:
        st.header("基本統計情報")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 品質スコア分布
            fig_quality = px.histogram(
                df, 
                x='quality_score', 
                nbins=30,
                title="品質スコア分布",
                labels={'quality_score': '品質スコア', 'count': '件数'}
            )
            st.plotly_chart(fig_quality, use_container_width=True)
            
            # プロンプト長分布
            fig_length = px.histogram(
                df, 
                x='prompt_length', 
                nbins=30,
                title="プロンプト長分布",
                labels={'prompt_length': 'プロンプト長（文字数）', 'count': '件数'}
            )
            st.plotly_chart(fig_length, use_container_width=True)
        
        with col2:
            # 品質スコア vs プロンプト長
            fig_scatter = px.scatter(
                df, 
                x='prompt_length', 
                y='quality_score',
                title="プロンプト長 vs 品質スコア",
                labels={'prompt_length': 'プロンプト長', 'quality_score': '品質スコア'},
                opacity=0.6
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # リアクション数分布
            fig_reactions = px.histogram(
                df[df['reaction_count'] > 0], 
                x='reaction_count', 
                nbins=20,
                title="リアクション数分布（0より大きい）",
                labels={'reaction_count': 'リアクション数', 'count': '件数'}
            )
            st.plotly_chart(fig_reactions, use_container_width=True)
    
    with tab2:
        st.header("プロンプト構造分析")
        
        # サンプル分析
        sample_size = min(100, len(df))
        sample_df = df.head(sample_size)
        
        st.info(f"上位 {sample_size} 件のプロンプトを分析中...")
        
        structures = []
        for _, row in sample_df.iterrows():
            structure = analyze_prompt_structure(row['full_prompt'])
            structure['quality_score'] = row['quality_score']
            structure['civitai_id'] = row['civitai_id']
            structures.append(structure)
        
        structure_df = pd.DataFrame(structures)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 要素数分布
            fig_elements = px.histogram(
                structure_df, 
                x='comma_elements',
                title="プロンプト要素数分布",
                labels={'comma_elements': '要素数（カンマ区切り）', 'count': '件数'}
            )
            st.plotly_chart(fig_elements, use_container_width=True)
            
            # 重み指定使用率
            fig_weights = px.histogram(
                structure_df, 
                x='weight_specifications',
                title="重み指定使用分布",
                labels={'weight_specifications': '重み指定数', 'count': '件数'}
            )
            st.plotly_chart(fig_weights, use_container_width=True)
        
        with col2:
            # 括弧使用パターン
            fig_brackets = px.scatter(
                structure_df, 
                x='parentheses_count', 
                y='square_brackets_count',
                color='quality_score',
                title="括弧使用パターン vs 品質",
                labels={
                    'parentheses_count': '丸括弧数', 
                    'square_brackets_count': '角括弧数',
                    'quality_score': '品質スコア'
                }
            )
            st.plotly_chart(fig_brackets, use_container_width=True)
            
            # 品質スコア vs 要素数
            fig_quality_elements = px.scatter(
                structure_df, 
                x='comma_elements', 
                y='quality_score',
                title="要素数 vs 品質スコア",
                labels={'comma_elements': '要素数', 'quality_score': '品質スコア'}
            )
            st.plotly_chart(fig_quality_elements, use_container_width=True)
    
    with tab3:
        st.header("キーワード分析")
        
        with st.spinner("キーワードを抽出・分析中..."):
            keywords = extract_keywords(df, min_frequency=5)
        
        if keywords:
            # 上位キーワード
            top_keywords = dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:30])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("頻出キーワード TOP30")
                keyword_df = pd.DataFrame(list(top_keywords.items()), columns=['キーワード', '出現回数'])
                
                fig_keywords = px.bar(
                    keyword_df.head(20), 
                    x='出現回数', 
                    y='キーワード',
                    orientation='h',
                    title="キーワード出現頻度"
                )
                fig_keywords.update_layout(height=600)
                st.plotly_chart(fig_keywords, use_container_width=True)
            
            with col2:
                st.subheader("キーワード統計")
                st.metric("ユニークキーワード数", len(keywords))
                st.metric("総キーワード出現数", sum(keywords.values()))
                st.metric("平均出現回数", f"{np.mean(list(keywords.values())):.1f}")
                
                # キーワード頻度分布
                freq_values = list(keywords.values())
                fig_freq = px.histogram(
                    x=freq_values,
                    nbins=20,
                    title="キーワード頻度分布",
                    labels={'x': '出現回数', 'y': 'キーワード数'}
                )
                st.plotly_chart(fig_freq, use_container_width=True)
        
        else:
            st.warning("十分な頻度のキーワードが見つかりませんでした。")
    
    with tab4:
        st.header("データ詳細")
        
        # フィルター
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_quality = st.slider("最小品質スコア", 0, int(df['quality_score'].max()), 0)
        
        with col2:
            min_length = st.slider("最小プロンプト長", 0, int(df['prompt_length'].max()), 0)
        
        with col3:
            sort_by = st.selectbox("並び順", ['品質スコア', 'プロンプト長', 'リアクション数'], index=0)
        
        # フィルター適用
        filtered_df = df[
            (df['quality_score'] >= min_quality) & 
            (df['prompt_length'] >= min_length)
        ]
        
        # ソート
        sort_columns = {
            '品質スコア': 'quality_score',
            'プロンプト長': 'prompt_length', 
            'リアクション数': 'reaction_count'
        }
        filtered_df = filtered_df.sort_values(sort_columns[sort_by], ascending=False)
        
        st.subheader(f"フィルター結果: {len(filtered_df)} 件")
        
        # データ表示
        display_df = filtered_df[[
            'civitai_id', 'full_prompt', 'quality_score', 
            'reaction_count', 'prompt_length', 'model_name'
        ]].copy()
        
        # プロンプトを短縮表示
        display_df['プロンプト（短縮）'] = display_df['full_prompt'].str[:100] + '...'
        display_df = display_df.drop('full_prompt', axis=1)
        display_df = display_df.rename(columns={
            'civitai_id': 'Civitai ID',
            'quality_score': '品質スコア',
            'reaction_count': 'リアクション数',
            'prompt_length': 'プロンプト長',
            'model_name': 'モデル名'
        })
        
        st.dataframe(display_df, use_container_width=True)
        
        # 選択したプロンプトの詳細表示
        if len(filtered_df) > 0:
            selected_idx = st.selectbox(
                "詳細表示するプロンプトを選択:", 
                range(min(10, len(filtered_df))),
                format_func=lambda x: f"{filtered_df.iloc[x]['civitai_id']} (品質: {filtered_df.iloc[x]['quality_score']})"
            )
            
            if selected_idx is not None:
                selected_row = filtered_df.iloc[selected_idx]
                
                st.subheader("選択プロンプト詳細")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.text_area(
                        "フルプロンプト:", 
                        selected_row['full_prompt'], 
                        height=200
                    )
                    
                    if selected_row['negative_prompt']:
                        st.text_area(
                            "ネガティブプロンプト:",
                            selected_row['negative_prompt'],
                            height=100
                        )
                
                with col2:
                    st.metric("品質スコア", selected_row['quality_score'])
                    st.metric("リアクション数", selected_row['reaction_count'])
                    st.metric("プロンプト長", selected_row['prompt_length'])
                    if selected_row['model_name']:
                        st.info(f"**モデル:** {selected_row['model_name']}")

if __name__ == "__main__":
    main()