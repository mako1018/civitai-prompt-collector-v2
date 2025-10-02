"""
CivitAI Prompt Collector - 実用的なプロンプト分析ツール
既存データを活用したプロンプトの細分化とカテゴライズ機能
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
from pathlib import Path
import sys
from datetime import datetime

# プロジェクトルートとDBパス定義
project_root = Path(__file__).parent.parent
DEFAULT_DB_PATH = str(project_root / 'data' / 'civitai_dataset.db')

# ページ設定
st.set_page_config(
    page_title="Civitai プロンプト分析ツール",
    page_icon="🎯",
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
    .quality-high { color: #4caf50; font-weight: bold; }
    .quality-medium { color: #ff9800; font-weight: bold; }
    .quality-low { color: #f44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_prompt_data():
    """プロンプトデータを読み込み"""
    try:
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        
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
        WHERE full_prompt IS NOT NULL AND full_prompt != ''
        ORDER BY quality_score DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # データ型の調整
        numeric_columns = ['quality_score', 'reaction_count', 'comment_count', 'download_count', 'prompt_length', 'tag_count']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # プロンプト長の再計算（不正な値の場合）
        mask = df['prompt_length'] <= 0
        df.loc[mask, 'prompt_length'] = df.loc[mask, 'full_prompt'].str.len()
        
        return df
        
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame()

def categorize_prompt_by_content(prompt_text):
    """プロンプトの内容に基づいてカテゴライズ"""
    if not prompt_text:
        return "未分類", 0.0
    
    prompt_lower = prompt_text.lower()
    
    # カテゴリ定義
    categories = {
        "ポートレート": ["portrait", "face", "headshot", "closeup", "person", "woman", "man", "girl", "boy"],
        "風景": ["landscape", "scenery", "nature", "mountain", "forest", "ocean", "sky", "sunset", "sunrise"],
        "アニメ・イラスト": ["anime", "manga", "cartoon", "illustration", "2d", "cel shading", "kawaii"],
        "リアル写真": ["realistic", "photorealistic", "photography", "photo", "camera", "lens"],
        "ファンタジー": ["fantasy", "magic", "dragon", "wizard", "fairy", "medieval", "castle"],
        "サイファイ": ["sci-fi", "futuristic", "robot", "cyberpunk", "space", "alien", "technology"],
        "ホラー": ["horror", "scary", "dark", "gothic", "vampire", "zombie", "creepy"],
        "アート": ["artistic", "painting", "drawing", "sketch", "watercolor", "oil painting"],
        "建築": ["architecture", "building", "house", "interior", "room", "design"],
        "動物": ["animal", "cat", "dog", "horse", "bird", "wildlife"]
    }
    
    # スコアリング
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in prompt_lower)
        if score > 0:
            category_scores[category] = score / len(keywords)
    
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category]
        return best_category, confidence
    
    return "未分類", 0.0

def analyze_prompt_complexity(prompt_text):
    """プロンプトの複雑度を分析"""
    if not prompt_text:
        return "簡単", 0
    
    # 複雑度指標
    length = len(prompt_text)
    comma_count = prompt_text.count(',')
    parentheses_count = prompt_text.count('(') + prompt_text.count(')')
    weight_count = len(re.findall(r':\s*\d*\.?\d+', prompt_text))
    
    # 複雑度スコア計算
    complexity_score = (
        length / 100 * 2 +  # 長さ
        comma_count * 1 +   # 要素数
        parentheses_count * 0.5 +  # 括弧
        weight_count * 2    # 重み指定
    )
    
    if complexity_score < 5:
        return "簡単", complexity_score
    elif complexity_score < 15:
        return "普通", complexity_score
    elif complexity_score < 30:
        return "複雑", complexity_score
    else:
        return "非常に複雑", complexity_score

def extract_top_keywords(df, min_frequency=5, max_keywords=50):
    """頻出キーワードを抽出"""
    all_keywords = []
    
    for prompt in df['full_prompt'].dropna():
        # カンマ区切りで分割して正規化
        elements = [elem.strip().lower() for elem in prompt.split(',')]
        
        for elem in elements:
            # 重み指定や括弧を除去
            elem = re.sub(r':\s*\d*\.?\d+', '', elem)
            elem = re.sub(r'[\(\)\[\]{}]', '', elem)
            elem = elem.strip()
            
            if elem and len(elem) > 2 and not elem.isdigit():
                all_keywords.append(elem)
    
    # 頻度カウント
    keyword_counts = Counter(all_keywords)
    
    # フィルタリング
    filtered_keywords = {
        k: v for k, v in keyword_counts.most_common(max_keywords) 
        if v >= min_frequency
    }
    
    return filtered_keywords

def analyze_quality_patterns(df):
    """品質パターンを分析"""
    if df.empty:
        return {}
    
    # 品質レベルの定義
    df['quality_level'] = pd.cut(
        df['quality_score'], 
        bins=[0, 50, 200, 500, float('inf')], 
        labels=['低', '中', '高', '最高']
    )
    
    patterns = {}
    
    # 品質レベル別統計
    for level in ['低', '中', '高', '最高']:
        level_data = df[df['quality_level'] == level]
        if not level_data.empty:
            patterns[f'{level}品質'] = {
                '件数': len(level_data),
                '平均長さ': level_data['prompt_length'].mean(),
                '平均リアクション': level_data['reaction_count'].mean()
            }
    
    return patterns

def main():
    st.title("🎯 Civitai プロンプト分析ツール")
    st.markdown("収集データに基づくプロンプト細分化とカテゴライズ")
    
    # データ読み込み
    with st.spinner("データを読み込み中..."):
        df = load_prompt_data()
    
    if df.empty:
        st.error("データが見つかりません。収集を開始してください。")
        st.info("データベースパス: " + DEFAULT_DB_PATH)
        return
    
    # サイドバー - 基本情報
    st.sidebar.header("📊 データ概要")
    st.sidebar.metric("総プロンプト数", len(df))
    st.sidebar.metric("平均品質スコア", f"{df['quality_score'].mean():.1f}")
    st.sidebar.metric("平均プロンプト長", f"{df['prompt_length'].mean():.0f}")
    st.sidebar.metric("最高品質スコア", f"{df['quality_score'].max():.0f}")
    
    # メインコンテンツ
    tab1, tab2, tab3, tab4 = st.tabs(["📈 品質分析", "🏷️ カテゴリ分析", "🔍 キーワード分析", "📋 プロンプト詳細"])
    
    with tab1:
        st.header("品質スコア分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 品質スコア分布
            fig_quality = px.histogram(
                df, 
                x='quality_score',
                nbins=50,
                title="品質スコア分布",
                labels={'quality_score': '品質スコア', 'count': '件数'}
            )
            st.plotly_chart(fig_quality, use_container_width=True)
            
            # 品質と長さの関係
            fig_scatter = px.scatter(
                df.sample(min(500, len(df))), 
                x='prompt_length', 
                y='quality_score',
                title="プロンプト長 vs 品質スコア（サンプル500件）",
                labels={'prompt_length': 'プロンプト長', 'quality_score': '品質スコア'},
                opacity=0.6
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            # 品質レベル分布
            df['quality_level'] = pd.cut(
                df['quality_score'], 
                bins=[0, 50, 200, 500, float('inf')], 
                labels=['低品質', '中品質', '高品質', '最高品質']
            )
            
            quality_counts = df['quality_level'].value_counts()
            fig_pie = px.pie(
                values=quality_counts.values,
                names=quality_counts.index,
                title="品質レベル分布"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # 品質パターン分析
            st.subheader("品質パターン")
            patterns = analyze_quality_patterns(df)
            
            for level, stats in patterns.items():
                with st.expander(f"{level} ({stats['件数']}件)"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("平均文字数", f"{stats['平均長さ']:.0f}")
                    with col_b:
                        st.metric("平均リアクション", f"{stats['平均リアクション']:.1f}")
    
    with tab2:
        st.header("プロンプトカテゴリ分析")
        
        # プロンプトをカテゴライズ（サンプリング）
        sample_size = min(200, len(df))
        sample_df = df.head(sample_size).copy()
        
        with st.spinner(f"上位{sample_size}件をカテゴライズ中..."):
            categories = []
            confidences = []
            complexities = []
            complexity_scores = []
            
            for prompt in sample_df['full_prompt']:
                category, confidence = categorize_prompt_by_content(prompt)
                complexity, complexity_score = analyze_prompt_complexity(prompt)
                
                categories.append(category)
                confidences.append(confidence)
                complexities.append(complexity)
                complexity_scores.append(complexity_score)
            
            sample_df['category'] = categories
            sample_df['confidence'] = confidences
            sample_df['complexity'] = complexities
            sample_df['complexity_score'] = complexity_scores
        
        col1, col2 = st.columns(2)
        
        with col1:
            # カテゴリ分布
            category_counts = sample_df['category'].value_counts()
            fig_cat = px.bar(
                x=category_counts.values,
                y=category_counts.index,
                orientation='h',
                title="プロンプトカテゴリ分布",
                labels={'x': '件数', 'y': 'カテゴリ'}
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
            # 複雑度分布
            complexity_counts = sample_df['complexity'].value_counts()
            fig_comp = px.pie(
                values=complexity_counts.values,
                names=complexity_counts.index,
                title="プロンプト複雑度分布"
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        
        with col2:
            # カテゴリ別品質スコア
            category_quality = sample_df.groupby('category')['quality_score'].agg(['mean', 'count']).reset_index()
            category_quality = category_quality[category_quality['count'] >= 3]  # 3件以上のカテゴリのみ
            
            fig_cat_quality = px.bar(
                category_quality,
                x='category',
                y='mean',
                title="カテゴリ別平均品質スコア（3件以上）",
                labels={'mean': '平均品質スコア', 'category': 'カテゴリ'}
            )
            fig_cat_quality.update_xaxes(tickangle=45)
            st.plotly_chart(fig_cat_quality, use_container_width=True)
            
            # 複雑度と品質の関係
            complexity_quality = sample_df.groupby('complexity')['quality_score'].mean().reset_index()
            fig_comp_quality = px.bar(
                complexity_quality,
                x='complexity',
                y='quality_score',
                title="複雑度別平均品質スコア",
                labels={'quality_score': '平均品質スコア', 'complexity': '複雑度'}
            )
            st.plotly_chart(fig_comp_quality, use_container_width=True)
        
        # カテゴリ詳細
        st.subheader("カテゴリ別詳細")
        
        selected_category = st.selectbox(
            "詳細表示するカテゴリを選択:",
            sample_df['category'].unique()
        )
        
        category_data = sample_df[sample_df['category'] == selected_category]
        
        if not category_data.empty:
            st.write(f"**{selected_category}** ({len(category_data)}件)")
            
            # 統計情報
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("平均品質スコア", f"{category_data['quality_score'].mean():.1f}")
            with col_b:
                st.metric("平均プロンプト長", f"{category_data['prompt_length'].mean():.0f}")
            with col_c:
                st.metric("平均信頼度", f"{category_data['confidence'].mean():.2f}")
            
            # サンプルプロンプト表示
            st.subheader("サンプルプロンプト（上位5件）")
            top_samples = category_data.nlargest(5, 'quality_score')
            
            for idx, (_, row) in enumerate(top_samples.iterrows(), 1):
                quality_class = (
                    "quality-high" if row['quality_score'] > 300 
                    else "quality-medium" if row['quality_score'] > 100 
                    else "quality-low"
                )
                
                st.markdown(f"""
                <div class="prompt-card">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <strong>#{idx}</strong>
                        <span class="{quality_class}">品質: {row['quality_score']:.0f}</span>
                    </div>
                    <div style="margin-bottom: 0.5rem;">
                        <strong>複雑度:</strong> {row['complexity']} ({row['complexity_score']:.1f})
                    </div>
                    <div style="font-size: 0.9rem; color: #666;">
                        {row['full_prompt'][:200]}{"..." if len(row['full_prompt']) > 200 else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.header("キーワード分析")
        
        with st.spinner("キーワードを分析中..."):
            keywords = extract_top_keywords(df, min_frequency=10, max_keywords=100)
        
        if keywords:
            col1, col2 = st.columns(2)
            
            with col1:
                # 頻出キーワード TOP30
                top_30_keywords = dict(list(keywords.items())[:30])
                keyword_df = pd.DataFrame(list(top_30_keywords.items()), columns=['キーワード', '出現回数'])
                
                fig_keywords = px.bar(
                    keyword_df,
                    x='出現回数',
                    y='キーワード',
                    orientation='h',
                    title="頻出キーワード TOP30",
                    labels={'出現回数': '出現回数', 'キーワード': 'キーワード'}
                )
                fig_keywords.update_layout(height=800)
                st.plotly_chart(fig_keywords, use_container_width=True)
            
            with col2:
                # キーワード統計
                st.subheader("キーワード統計")
                
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.metric("ユニークキーワード数", len(keywords))
                    st.metric("総出現回数", sum(keywords.values()))
                
                with col_stat2:
                    st.metric("平均出現回数", f"{np.mean(list(keywords.values())):.1f}")
                    st.metric("最高出現回数", max(keywords.values()))
                
                # キーワード頻度分布
                freq_values = list(keywords.values())
                fig_freq_dist = px.histogram(
                    x=freq_values,
                    nbins=20,
                    title="キーワード頻度分布",
                    labels={'x': '出現回数', 'y': 'キーワード数'}
                )
                st.plotly_chart(fig_freq_dist, use_container_width=True)
                
                # トップキーワード詳細
                st.subheader("トップ10キーワード")
                top_10 = list(keywords.items())[:10]
                
                for i, (keyword, count) in enumerate(top_10, 1):
                    percentage = (count / len(df)) * 100
                    st.write(f"{i}. **{keyword}** - {count}回 ({percentage:.1f}%)")
        
        else:
            st.warning("十分な頻度のキーワードが見つかりませんでした。")
    
    with tab4:
        st.header("プロンプト詳細検索")
        
        # フィルター設定
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            min_quality = st.slider("最小品質スコア", 0, int(df['quality_score'].max()), 0)
        
        with col2:
            max_quality = st.slider("最大品質スコア", 0, int(df['quality_score'].max()), int(df['quality_score'].max()))
        
        with col3:
            min_length = st.slider("最小プロンプト長", 0, int(df['prompt_length'].max()), 0)
        
        with col4:
            sort_by = st.selectbox("並び順", ['品質スコア', 'プロンプト長', 'リアクション数'], index=0)
        
        # キーワード検索
        search_keyword = st.text_input("キーワード検索（プロンプト内容で検索）")
        
        # フィルター適用
        filtered_df = df[
            (df['quality_score'] >= min_quality) & 
            (df['quality_score'] <= max_quality) &
            (df['prompt_length'] >= min_length)
        ]
        
        if search_keyword:
            filtered_df = filtered_df[
                filtered_df['full_prompt'].str.contains(search_keyword, case=False, na=False)
            ]
        
        # ソート
        sort_columns = {
            '品質スコア': 'quality_score',
            'プロンプト長': 'prompt_length', 
            'リアクション数': 'reaction_count'
        }
        filtered_df = filtered_df.sort_values(sort_columns[sort_by], ascending=False)
        
        st.subheader(f"検索結果: {len(filtered_df)} 件")
        
        if len(filtered_df) > 0:
            # ページネーション
            items_per_page = 10
            total_pages = max(1, (len(filtered_df) - 1) // items_per_page + 1)
            
            col_page1, col_page2 = st.columns([1, 4])
            with col_page1:
                current_page = st.selectbox("ページ", range(1, total_pages + 1)) - 1
            
            start_idx = current_page * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_df))
            page_data = filtered_df.iloc[start_idx:end_idx]
            
            # 結果表示
            for idx, (_, row) in enumerate(page_data.iterrows(), start_idx + 1):
                quality_class = (
                    "quality-high" if row['quality_score'] > 300 
                    else "quality-medium" if row['quality_score'] > 100 
                    else "quality-low"
                )
                
                with st.expander(f"#{idx} | ID: {row['civitai_id']} | 品質: {row['quality_score']:.0f} | 長さ: {row['prompt_length']:.0f}"):
                    col_detail1, col_detail2 = st.columns([3, 1])
                    
                    with col_detail1:
                        st.text_area(
                            "フルプロンプト:", 
                            row['full_prompt'], 
                            height=120,
                            key=f"prompt_{idx}"
                        )
                        
                        if pd.notna(row['negative_prompt']) and str(row['negative_prompt']).strip():
                            st.text_area(
                                "ネガティブプロンプト:",
                                row['negative_prompt'],
                                height=80,
                                key=f"neg_prompt_{idx}"
                            )
                    
                    with col_detail2:
                        st.metric("品質スコア", f"{row['quality_score']:.0f}")
                        st.metric("リアクション数", f"{row['reaction_count']:.0f}")
                        st.metric("プロンプト長", f"{row['prompt_length']:.0f}")
                        
                        if pd.notna(row['model_name']):
                            st.info(f"**モデル:** {row['model_name']}")
                        
                        if pd.notna(row['collected_at']):
                            st.caption(f"収集日: {row['collected_at']}")
            
            # ページ情報
            st.caption(f"ページ {current_page + 1} / {total_pages} | 表示中: {start_idx + 1}-{end_idx} / {len(filtered_df)}件")
        
        else:
            st.info("検索条件に一致するプロンプトが見つかりませんでした。")

if __name__ == "__main__":
    main()