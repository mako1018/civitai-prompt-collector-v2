"""
CivitAI Prompt Collector - Streamlit Web UI (with collection tab)
コピー元: streamlit_app.py に収集タブを追加した派生版
"""

import streamlit as st
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'src'))
import pandas as pd
import requests
from database import DatabaseManager
try:
    import plotly.express as px  # type: ignore[import]
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
try:
    import matplotlib.pyplot as plt  # type: ignore[import]
except ImportError:
    plt = None
import sqlite3
import uuid
from pathlib import Path
import sys
import subprocess
from datetime import datetime, timedelta, timezone
import re
import ast
import os
import time
import math

# プロジェクトルートとDBパス定義
project_root = Path(__file__).parent.parent
DEFAULT_DB_PATH = str(project_root / 'data' / 'civitai_dataset.db')
import sys
sys.path.append(str(project_root / 'src'))

# ページ設定
st.set_page_config(
    page_title="CivitAI Prompt Collector (Collect)",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタム CSS
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
    try:
        db_manager = DatabaseManager()
        query = """
        SELECT
            p.id,
            p.full_prompt,
            p.negative_prompt,
            p.model_name,
            p.model_id,
            p.collected_at,
            pc.category,
            pc.confidence
        FROM civitai_prompts p
        LEFT JOIN prompt_categories pc ON p.id = pc.prompt_id
        ORDER BY p.collected_at DESC
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
    try:
        db_manager = DatabaseManager()
        total_prompts = db_manager.get_prompt_count()
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
    if df.empty:
        return None
    category_counts = df['category'].value_counts()
    df_counts = category_counts.rename_axis('category').reset_index(name='count')
    colors = {
        'NSFW': '#ff6b6b',
        'style': '#4ecdc4',
        'lighting': '#ffe66d',
        'composition': '#a8e6cf',
        'mood': '#ff8b94',
        'basic': '#b4a7d6',
        'technical': '#d4a574'
    }
    if PLOTLY_AVAILABLE:
        fig = px.pie(data_frame=df_counts, names='category', values='count', title="カテゴリ分布", color_discrete_map=colors, hover_data=['count'])
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(font=dict(size=12), showlegend=True, height=500)
        return fig
    else:
        fig, ax = plt.subplots(figsize=(6, 6))
        wedges, texts, autotexts = ax.pie(df_counts['count'], labels=df_counts['category'], autopct='%1.1f%%', colors=[colors.get(c, None) for c in df_counts['category']])
        ax.set_title('カテゴリ分布')
        plt.tight_layout()
        return fig

def create_confidence_histogram(df):
    if df.empty or 'confidence' not in df.columns:
        return None
    if PLOTLY_AVAILABLE:
        fig = px.histogram(df, x='confidence', nbins=20, title='分類信頼度の分布', labels={'confidence': '信頼度', 'count': 'プロンプト数'}, color_discrete_sequence=['#1f77b4'])
        fig.update_layout(xaxis_title="信頼度", yaxis_title="プロンプト数", font=dict(size=12), height=400)
        return fig

    else:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(df['confidence'].dropna(), bins=20, color='#1f77b4')
        ax.set_title('分類信頼度の分布')
        ax.set_xlabel('信頼度')
        ax.set_ylabel('プロンプト数')
        plt.tight_layout()
        return fig


def display_chart(fig, use_container_width=True):
    """Display a figure produced by either plotly or matplotlib safely.
    If plotly is available and the figure looks like a plotly figure, use st.plotly_chart.
    Otherwise fall back to st.pyplot for matplotlib figures.
    """
    try:
        if PLOTLY_AVAILABLE:
            # plotly figures typically have 'to_plotly_json' or come from plotly.graph_objs
            # Use a conservative check to avoid importing plotly modules here.
            if hasattr(fig, 'to_plotly_json') or getattr(fig, '__module__', '').startswith('plotly'):
                st.plotly_chart(fig, width='stretch')
                return
        # Fallback: assume matplotlib figure
        try:
            import matplotlib.pyplot as _plt  # noqa: F401
        except Exception:
            pass
        st.pyplot(fig)
    except Exception:
        # Last-resort: just print the object
        st.write(fig)
    # end display_chart

def display_prompt_card(row):
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
                <strong>作成日:</strong> {row.get('collected_at', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        prompt_id = row.get('id', '')
        show_key = f"show_prompt_{prompt_id}"
        placeholder = st.empty()

        def _show_prompt(id=prompt_id):
            st.session_state[f"show_prompt_{id}"] = True

        if st.session_state.get(show_key, False):
            full_key = f"full_prompt_{prompt_id}"
            neg_key = f"neg_prompt_{prompt_id}"
            with placeholder.container():
                st.text_area("ポジティブプロンプト", value=row.get('full_prompt', ''), height=100, disabled=True, key=full_key)
                if pd.notna(row.get('negative_prompt')) and str(row.get('negative_prompt')).strip():
                    st.text_area("ネガティブプロンプト", value=row.get('negative_prompt', ''), height=80, disabled=True, key=neg_key)
                if st.button("閉じる", key=f"close_{prompt_id}"):
                    st.session_state[show_key] = False
                    try:
                        if hasattr(st, 'experimental_rerun'):
                            st.experimental_rerun()
                        else:
                            import streamlit.components.v1 as components
                            components.html('<script>window.location.reload()</script>', height=0)
                    except Exception:
                        st.stop()
        else:
            if placeholder.button("詳細を表示", key=f"open_{prompt_id}", on_click=_show_prompt, args=()):
                try:
                    if hasattr(st, 'experimental_rerun'):
                        st.experimental_rerun()
                    else:
                        import streamlit.components.v1 as components
                        components.html('<script>window.location.reload()</script>', height=0)
                except Exception:
                    st.stop()

def read_log_tail(path, lines=50):
    from pathlib import Path
    log_path = Path(path)
    if not log_path.is_absolute():
        log_path = Path(__file__).parent.parent / log_path
    if not log_path.exists():
        return ''
    try:
        with log_path.open('r', encoding='utf-8', errors='replace') as f:
            data = f.read()
            return '\n'.join(data.splitlines()[-lines:])
    except Exception:
        return ''

def extract_progress_from_log(tail):
    if not tail:
        return None
    patterns = [
        r'Collected total=(\d+)',
        r'valid=(\d+)',
        r'収集済み[：:]\s*(\d+)',
        r'進捗[：:]\s*(\d+)',
        r'saved=(\d+)',
        r'new_saved=(\d+)'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, tail)
        if matches:
            try:
                return int(matches[-1])
            except:
                continue
    return None

def infer_status_from_tail(tail):
    # tailが空でも、ログファイルが存在すれば'準備中'や'実行中'と判定
    if tail is None:
        return '未開始/待機中'
    if tail == '':
        return '準備中/実行中'
    low = tail.lower()
    if 'traceback' in low or 'error' in low:
        return '失敗'
    if '=== collection started' in low:
        if '=== collection finished' in low:
            return '完了'
        return '収集中'
    if 'collected total' in low or 'collected=' in low or 'collected ' in low:
        return '収集中'
    if '=== collection finished' in low or 'collection finished' in low:
        return '完了'
    if 'saved' in low and ('items' in low or 'item' in low):
        return '完了'
    if 'categorization finished' in low or 'categorisation finished' in low:
        return '完了'
    return '実行中'

def parse_job_summary(tail: str) -> dict:
    """Parse known log markers from the job tail and return a summary dict."""
    summary = {
        'collected': None,
        'valid': None,
        'saved': None,
        'attempted': None,
        'new_saved': None,
        'duplicates': None,
        'sample_ids': [],
        'updated_count': 0,
        'api_total': None
    }
    if not tail:
        return summary
    for line in tail.splitlines():
        l = line.strip()
        # Collected total patterns
        m = re.search(r'Collected total=(\d+)', l)
        if m:
            try:
                summary['collected'] = int(m.group(1))
            except Exception:
                pass
        m = re.search(r'valid=(\d+)', l)
        if m:
            try:
                summary['valid'] = int(m.group(1))
            except Exception:
                pass

        # Saved explicit
        m = re.search(r'Saved\s+(\d+)\s+items to DB', l)
        if m:
            try:
                summary['saved'] = int(m.group(1))
            except Exception:
                pass

        # Batch result
        m = re.search(r'Batch result: attempted=(\d+)\s+new_saved=(\d+)\s+duplicates=(\d+)', l)
        if m:
            try:
                summary['attempted'] = int(m.group(1))
                summary['new_saved'] = int(m.group(2))
                summary['duplicates'] = int(m.group(3))
            except Exception:
                pass

        # Done line
        m = re.search(r'\[Done\] Collected unique prompts: .* saved=(\d+)', l)
        if m:
            try:
                summary['saved'] = int(m.group(1))
            except Exception:
                pass

        # Sample ids
        m = re.search(r"\[DB\] sample civitai_ids:\s*(\[.*\])", l)
        if m:
            try:
                # use ast.literal_eval to parse list-like Python repr
                vals = ast.literal_eval(m.group(1))
                if isinstance(vals, (list, tuple)):
                    summary['sample_ids'] = [str(x) for x in vals]
            except Exception:
                pass

        # Updated existing lines
        if '[DB] Updated existing civitai_id=' in l or 'Updated existing civitai_id=' in l:
            summary['updated_count'] += 1

        # API preview marker (from collect_from_ui logs)
        m = re.search(r'API preview: totalItems reported -> (\d+)', l)
        if m:
            try:
                summary['api_total'] = int(m.group(1))
            except Exception:
                pass

    return summary

@st.cache_data(ttl=2)
def load_data_no_cache():
    """キャッシュを使わないデータ読み込み"""
    try:
        db_manager = DatabaseManager()
        query = """
        SELECT
            p.id,
            p.full_prompt,
            p.negative_prompt,
            p.model_name,
            p.model_id,
            p.collected_at,
            pc.category,
            pc.confidence
        FROM civitai_prompts p
        LEFT JOIN prompt_categories pc ON p.id = pc.prompt_id
        ORDER BY p.collected_at DESC
        """
        conn = db_manager._get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        return pd.DataFrame()

def main():
    global sys
    import sys
    global Path
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    from pathlib import Path
    # 収集ジョブ状態の自動更新（3秒ごと）
    st_autorefresh = getattr(st, 'autorefresh', None)
    # intervalを1000ms（1秒）に短縮し、確実に自動更新
    if st_autorefresh:
        st_autorefresh(interval=1000, key="job_status_autorefresh")
    st.title("🎨 CivitAI Prompt Collector - Collect")
    st.markdown("プロンプトデータの分析・表示・収集タブを提供します")

    df = load_data()
    stats = get_database_stats()

    st.sidebar.header("📊 データ統計")
    if st.sidebar.button("🔄 リフレッシュ（最新データ読み込み）"):
        try:
            st.cache_data.clear()
        except Exception:
            try:
                st.experimental_memo_clear()
            except Exception:
                pass
        try:
            if hasattr(st, 'experimental_rerun'):
                st.experimental_rerun()
            else:
                raise AttributeError('experimental_rerun not available')
        except Exception:
            try:
                import streamlit.components.v1 as components
                components.html('<script>window.location.reload()</script>', height=0)
            except Exception:
                st.stop()

    st.sidebar.metric("総プロンプト数", stats['total_prompts'])
    st.sidebar.metric("分類済み数", len(df[df['category'].notna()]))

    tab_collect, tab1, tab2, tab3, tab4 = st.tabs(["🔎 収集", "📊 ダッシュボード", "📋 プロンプト一覧", "📈 詳細分析", "💾 データエクスポート"])

    with tab_collect:
        st.header("データ収集（CivitAI API）")
        st.markdown("モデルIDまたはバージョンIDを指定してプロンプトを収集し、データベースに保存します。完了後に自動で再分類を行い、UIのキャッシュをクリアします。")

        col_a, col_b = st.columns(2)
        with col_a:
            model_id = st.text_input("Model ID（モデル識別子、任意）", value="", key='model_id_input', help="モデルの ID。通常は数値の modelId（例: 101055）や文字列が入ります。")
            # Provide a button to fetch model metadata (name + versions) from CivitAI
            fetch_info = st.button("モデル情報を取得", key='fetch_model_info')

            # If user clicked 'fetch_info', call API to populate model_name and versions
            if fetch_info and model_id:
                try:
                    import sys
                    from pathlib import Path
                    project_root = Path(__file__).parent.parent
                    sys.path.append(str(project_root / 'src'))
                    import config
                    API_BASE_URL = config.API_BASE_URL
                    REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
                    USER_AGENT = config.USER_AGENT
                    CIVITAI_API_KEY = config.CIVITAI_API_KEY
                    base_api = API_BASE_URL.rsplit('/', 1)[0]
                    model_url = f"{base_api}/models/{str(model_id).strip()}"
                    headers = {"User-Agent": USER_AGENT}
                    if CIVITAI_API_KEY:
                        headers['Authorization'] = f"Bearer {CIVITAI_API_KEY}"
                    resp = requests.get(model_url, headers=headers, timeout=REQUEST_TIMEOUT)
                    if resp.status_code == 200:
                        j = resp.json()
                        mname = j.get('name') or j.get('title') or j.get('modelName')
                        if mname:
                            st.session_state['model_name_input'] = mname
                        # build versions list
                        mvers = j.get('modelVersions') or j.get('versions') or []
                        vers = []
                        for v in mvers:
                            if isinstance(v, dict):
                                vid = v.get('id') or v.get('modelVersionId')
                                vname = v.get('name') or ''
                                if vid:
                                    vers.append({'id': str(vid), 'name': vname})
                        if vers:
                            st.session_state['model_versions'] = vers
                            # preselect first
                            st.session_state['version_select'] = 0
                    else:
                        st.warning(f"モデル情報の取得に失敗しました: HTTP {resp.status_code}")
                except Exception as e:
                    st.error(f"モデル情報の取得中にエラー: {e}")
                    # fallback to DB lookup
                    try:
                        db_path = DEFAULT_DB_PATH
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        cur.execute("SELECT model_name FROM civitai_prompts WHERE model_id = ? AND model_name IS NOT NULL AND model_name <> '' LIMIT 1", (str(model_id).strip(),))
                        row = cur.fetchone()
                        if row and row[0]:
                            st.session_state['model_name_input'] = row[0]
                        conn.close()
                    except Exception:
                        pass

            # Version input: if we have discovered versions, show a selectbox, otherwise fallback to text input
            versions = st.session_state.get('model_versions', None)
            if versions:
                # versions is list of dicts with keys 'id' and 'name'
                opts = [f"{v.get('id')} - {v.get('name', '')}" for v in versions]
                # Normalize stored index/value to a serializable string if needed
                try:
                    existing = st.session_state.get('version_select', None)
                    if isinstance(existing, int):
                        # keep as index (old behavior) by ensuring index is in range
                        if existing < 0 or existing >= len(opts):
                            st.session_state['version_select'] = 0
                    elif existing is not None and existing not in opts:
                        # remove invalid stored value to avoid serialization issues
                        try:
                            del st.session_state['version_select']
                        except Exception:
                            st.session_state['version_select'] = 0
                except Exception:
                    st.session_state['version_select'] = 0

                # Ensure we always pass strings to selectbox; use index-based default when possible
                default_index = 0
                try:
                    if isinstance(st.session_state.get('version_select', None), int):
                        default_index = st.session_state.get('version_select')
                except Exception:
                    default_index = 0

                # Use selectbox without a persistent key to avoid session_state type conflicts
                sel = st.selectbox("Version（選択）", options=opts, index=default_index)
                # extract id from selected option string like '123 - name'
                if isinstance(sel, str):
                    version_id = str(sel.split(' - ', 1)[0])
                else:
                    version_id = str(sel)
            else:
                version_id = st.text_input("Version ID（数値、必須）", value="", key='version_id_input', help="バージョンID（数値）を必ず指定してください。指定するとそのバージョンを収集します。")

            # model_name input uses a session_state key so we can autofill it
            model_name = st.text_input("モデル名（自動補完）", value=st.session_state.get('model_name_input', ''), key='model_name_input')
            # Default to a conservative limit (1000) to avoid accidental large runs
            max_items = st.number_input("最大取得件数", value=1000, min_value=1, max_value=100000, step=1)
            status_check = st.button("状況を確認（DB件数 + API件数取得）", key='status_check')
        with col_b:
            st.write("実行オプション")
            run_save = st.checkbox("データベースに保存する", value=True)
            run_categorize = st.checkbox("収集後に自動で再分類する", value=True)
            strict_version_match = st.checkbox("厳密なバージョン一致のみ許可 (checkpoint のみ)", value=False, help="有効にすると、meta.civitaiResources の checkpoint リソースと正確に一致する場合のみそのバージョンとして扱います。")

        # Status check: show DB counts and API totalItems when requested
        if status_check:
            try:
                db = DatabaseManager()
                # Count records that reference this version in model_version_id OR raw_metadata
                vcount = 0
                rawcount = 0
                if version_id and str(version_id).strip():
                    conn = db._get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (str(version_id).strip(),))
                        vcount = cur.fetchone()[0]
                        # also count raw_metadata contains as a hint
                        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', (f"%{str(version_id).strip()}%",))
                        rawcount = cur.fetchone()[0]
                    finally:
                        conn.close()
                    st.info(f"DB: model_version_id == {version_id} の件数: {vcount} (raw_metadata に {rawcount} 件含む)")
                else:
                    st.info("Version ID が指定されていません。")

                # check API totalItems via collector helper
                try:
                    from src.collector import check_total_items
                    total = check_total_items(model_id=model_id if model_id else None, version_id=version_id if version_id else None)
                    if total is not None:
                        st.success(f"API が報告する総件数: {total} 件")
                    else:
                        st.warning("API は totalItems を返しませんでした（カーソル方式で収集されます）")
                except Exception as e:
                    st.error(f"API 件数確認に失敗: {e}")
            except Exception as e:
                st.error(f"状況確認に失敗しました: {e}")

        # Immediate preview: always show DB counts + API total (helps explain 0/少数の原因)
        try:
            if version_id and str(version_id).strip():
                db = DatabaseManager()
                conn = db._get_connection()
                cur = conn.cursor()
                try:
                    cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (str(version_id).strip(),))
                    vcount = cur.fetchone()[0]
                    cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', (f"%{str(version_id).strip()}%",))
                    rawcount = cur.fetchone()[0]
                finally:
                    conn.close()

                # API preview
                try:
                    from src.collector import check_total_items
                    total = check_total_items(model_id=model_id if model_id else None, version_id=version_id if version_id else None)
                except Exception:
                    total = None

                col1, col2, col3 = st.columns(3)
                col1.metric(f"DB 保存済み (model_version_id == {version_id})", vcount)
                col2.metric("raw_metadata に出現", rawcount)
                if total is not None:
                    col3.metric("API が報告する総件数", total)
                else:
                    col3.metric("API が報告する総件数", "N/A")

                with st.expander("補足: なぜ0件/少数かを判断するためのヒント"):
                    st.markdown("""
                    - DB 側の `model_version_id` が未設定（今回の補完で埋められている可能性があります）だと UI に保存数が表示されません。
                    - raw_metadata に該当バージョンが含まれている件数はヒントになります（必ずしも保存対象とは限りません）。
                    - API の totalItems は利用可能な場合にのみ返されます（返さないAPIはカーソル方式で全件取得されます）。
                    """)
            else:
                st.info("Version ID を入力すると、DB に保存済みの件数と API の総件数をプレビューします。")
        except Exception as e:
            st.warning(f"プレビューの取得に失敗しました: {e}")

        # Require version_id to run
        version_required = True
        start_disabled = False
        if version_required and (not (version_id and str(version_id).strip())):
            start_disabled = True
            st.warning("Version ID は必須です。Version ID を入力してください。")

        start_button = st.button("▶ 収集開始（バックグラウンド）", disabled=start_disabled)
        # New controls: Full Collect, Resume, Stop
        st.write('')
        if st.button('🔍 全件収集（最初から最後まで）', disabled=start_disabled):
            # Start full collect (no max-items limit) as background job
            job_id = str(uuid.uuid4())[:8]
            log_dir = Path(project_root) / 'scripts'
            log_file = log_dir / f'collect_full_{job_id}.log'
            def _clean_id_local(s):
                if not s:
                    return ''
                return str(s).strip().rstrip('/')

            args = [
                sys.executable,
                str(Path(project_root) / 'scripts' / 'collect_from_ui.py'),
                '--model-id', _clean_id_local(model_id) or '',
                '--version-id', _clean_id_local(version_id) or '',
                '--model-name', (model_name or ''),
                '--max-items', str(0),
                '--save' if run_save else '--no-save',
                '--categorize' if run_categorize else '--no-categorize',
                '--log-file', str(log_file)
            ]
            if strict_version_match:
                args.append('--strict-version-match')
            try:
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(project_root))
                # record requested_max_items for clearer job summaries (0 means unlimited)
                job = {'id': job_id, 'log_file': str(log_file), 'model_id': _clean_id_local(model_id), 'version_id': (_clean_id_local(version_id) or ''), 'model_name': model_name, 'started_at': datetime.utcnow().isoformat() + 'Z', 'status': 'running', 'last_tail': '', 'requested_max_items': 0}
                st.session_state.setdefault('collect_jobs', []).insert(0, job)
                st.success(f"フル収集ジョブを開始しました: {job_id}")
            except Exception as e:
                st.error(f"ジョブ開始失敗: {e}")

        if st.button('▶ 再開（保存された状態から）'):
            # Start resume job using scripts/resume_collect.py
            job_id = str(uuid.uuid4())[:8]
            log_dir = Path(project_root) / 'scripts'
            log_file = log_dir / f'collect_resume_{job_id}.log'
            def _clean_id_local(s):
                if not s:
                    return ''
                return str(s).strip().rstrip('/')
            args = [
                sys.executable,
                str(Path(project_root) / 'scripts' / 'resume_collect.py'),
                '--log-file', str(log_file)
            ]
            try:
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(project_root))
                job = {'id': job_id, 'log_file': str(log_file), 'model_id': _clean_id_local(model_id), 'version_id': (_clean_id_local(version_id) or ''), 'model_name': model_name, 'started_at': datetime.utcnow().isoformat() + 'Z', 'status': 'running', 'last_tail': ''}
                st.session_state.setdefault('collect_jobs', []).insert(0, job)
                st.success(f"再開ジョブを開始しました: {job_id}")
            except Exception as e:
                st.error(f"再開ジョブ開始失敗: {e}")

        if st.button('⏹ 停止（実行中ジョブへ停止指示）'):
            # Create stop file used by collector scripts to gracefully stop
            stop_file = Path(project_root) / 'scripts' / 'collect_stop.flag'
            try:
                stop_file.write_text('stop')
                st.info('停止フラグを作成しました。実行中のジョブは次のチェックポイントで停止します。')
            except Exception as e:
                st.error(f'停止フラグの作成に失敗しました: {e}')

        if start_button:
            # Launch background subprocess to run collection
            job_id = str(uuid.uuid4())[:8]
            # write this job's log to the centralized logs/collect_jobs directory
            log_dir = Path(project_root) / 'logs' / 'collect_jobs'
            log_file = log_dir / f'collect_job_{job_id}.log'

            # Enforce version_id usage: version is required and will be used as modelVersionId
            # Sanitize inputs: trim and remove trailing slashes
            def _clean_id(s):
                if not s:
                    return ''
                return str(s).strip().rstrip('/')

            selected_id = _clean_id(version_id) if version_id and str(version_id).strip() else (_clean_id(model_id) if model_id else None)

            args = [
                sys.executable,
                str(Path(project_root) / 'scripts' / 'collect_from_ui.py'),
                '--model-id', selected_id or '',
                '--version-id', _clean_id(version_id) or '',
                '--model-name', (model_name or ''),
                '--max-items', str(int(max_items)),
                '--no-save' if not run_save else '--save',
                '--categorize' if run_categorize else '--no-categorize',
                '--log-file', str(log_file)
            ]
            if strict_version_match:
                args.append('--strict-version-match')

            try:
                # Start subprocess detached
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(project_root))
                # register job in session_state
                job = {
                    'id': job_id,
                    'log_file': str(log_file),
                    'model_id': selected_id,
                    'version_id': (version_id or ''),
                    'model_name': (model_name or ''),
                    'started_at': datetime.utcnow().isoformat() + 'Z',
                    'status': 'running',
                    'last_tail': '',
                    'requested_max_items': int(max_items)
                }
                if 'collect_jobs' not in st.session_state:
                    st.session_state['collect_jobs'] = []
                st.session_state['collect_jobs'].insert(0, job)

                st.success(f"ジョブ開始: {job_id} — ログ: {log_file}")
                st.write("ログをリアルタイムで見るには別ウィンドウで次を実行してください:")
                st.code(f"Get-Content {log_file} -Wait -Tail 200", language='powershell')
            except Exception as e:
                st.error(f"バックグラウンドジョブの開始に失敗しました: {e}")

        # --- Job status display ---
        st.subheader("収集ジョブの状態")

        jobs = st.session_state.get('collect_jobs', [])
        db_manager = DatabaseManager()

        if jobs:
            for j in list(jobs):
                with st.expander(f"ジョブ {j['id']} — モデル {j.get('model_id','')} / バージョン {j.get('version_id','')}"):
                    lf = str(Path(j.get('log_file')).as_posix())
                    tail = read_log_tail(lf, lines=80)
                    version_id_str = str(j.get('version_id')) if j.get('version_id') is not None else ''
                    cs_list = db_manager.get_collection_state_for_version(version_id_str)
                    cs = cs_list[0] if cs_list else None
                    # 完了判定: ログtailまたはDB進捗に完了キーワードがあれば必ず'完了'
                    status = None
                    tail_lower = tail.lower() if tail else ''
                    is_finished = False
                    if cs and 'status' in cs and cs['status'] in ('completed', '完了'):
                        is_finished = True
                    if '=== collection finished' in tail_lower or 'job summary' in tail_lower:
                        is_finished = True
                    if is_finished:
                        status = '完了'
                    else:
                        if cs and 'status' in cs:
                            status = cs['status']
                        else:
                            status = infer_status_from_tail(tail)
                    # 進捗・予定件数
                    total_collected = cs['total_collected'] if cs and 'total_collected' in cs else None
                    planned_total = cs['planned_total'] if cs and 'planned_total' in cs else j.get('requested_max_items', None)
                    last_update = cs['last_update'] if cs and 'last_update' in cs else None
                    started_at = j.get('started_at')
                    def to_jst(dtstr):
                        try:
                            dt = datetime.fromisoformat(str(dtstr).replace('Z',''))
                            jst = dt.astimezone(timezone(timedelta(hours=9)))
                            return jst.strftime('%Y-%m-%d %H:%M:%S JST')
                        except Exception:
                            return str(dtstr)
                    elapsed_sec = None
                    if started_at and last_update:
                        try:
                            dt_start = datetime.fromisoformat(str(started_at).replace('Z',''))
                            dt_last = datetime.fromisoformat(str(last_update).replace('Z',''))
                            elapsed_sec = (dt_last - dt_start).total_seconds()
                        except Exception:
                            elapsed_sec = None
                    # ステータス・進捗バー（上部）
                    st.markdown("### ステータス")
                    cols_status = st.columns([2,2,2,2])
                    with cols_status[0]:
                        if status in ('running', '収集中'):
                            st.info('状態: 実行中')
                        elif status in ('completed', '完了'):
                            st.success('状態: 完了')
                        elif status in ('failed', '失敗'):
                            st.error('状態: 失敗')
                        elif status in ('idle', '未開始/待機中', None):
                            st.write('状態: 未開始/待機中')
                        else:
                            st.write(f'状態: {status}')
                    with cols_status[1]:
                        # 進捗バーは常に表示。予定件数が不明/無制限なら仮の最大値（1000）で割合計算
                        bar_max = 1000
                        if planned_total and planned_total not in (None, 0, '0', 'unlimited'):
                            try:
                                bar_max = int(planned_total)
                            except Exception:
                                bar_max = 1000
                        bar_val = int(total_collected) if total_collected is not None else 0
                        # 完了時は100%表示
                        if status in ('completed', '完了'):
                            progress = 1.0
                        else:
                            progress = min(1.0, bar_val / bar_max) if bar_max > 0 else 0.0
                        st.progress(progress, text=f"進捗: {bar_val} / {bar_max} 件 ({progress*100:.1f}%)")
                        if planned_total in (None, 0, '0', 'unlimited'):
                            st.write(f"進捗: {bar_val} 件（予定件数不明/無制限）")
                    with cols_status[2]:
                        if elapsed_sec is not None:
                            mins = int(elapsed_sec // 60)
                            secs = int(elapsed_sec % 60)
                            st.write(f"経過時間: {mins}分{secs}秒")
                    with cols_status[3]:
                        st.write(f"開始: {to_jst(started_at)}")
                        if last_update:
                            st.write(f"最終更新: {to_jst(last_update)}")
                    # ログ・サマリー（下部）
                    st.markdown("### ログ（末尾）")
                    if tail:
                        st.code(tail, language='text')
                    else:
                        st.info('ログはまだありません。')
                    try:
                        summary = parse_job_summary(tail)
                        if any(v is not None for k,v in summary.items() if k in ('collected','saved','duplicates','new_saved')) or summary['sample_ids'] or summary['updated_count']:
                            st.markdown('### ジョブサマリー')
                            planned_display = planned_total if planned_total not in (None, 0, '0', '', 'None') else (j.get('requested_max_items') if j.get('requested_max_items', None) not in (None, 0, '0', '', 'None') else 'unlimited')
                            fetched = summary.get('collected') or summary.get('attempted') or summary.get('total_unique') or total_collected or 'N/A'
                            duplicates = summary.get('duplicates')
                            if duplicates is None and summary.get('attempted') is not None and summary.get('new_saved') is not None:
                                try:
                                    duplicates = int(summary.get('attempted')) - int(summary.get('new_saved'))
                                except Exception:
                                    duplicates = None
                            cols = st.columns(4)
                            cols[0].metric('取得予定 (planned)', planned_display)
                            cols[1].metric('取得 (fetched)', fetched)
                            cols[2].metric('新規保存', summary.get('new_saved') if summary.get('new_saved') is not None else (summary.get('saved') if summary.get('saved') is not None else '0'))
                            cols[3].metric('重複 (duplicates)', duplicates if duplicates is not None else 'N/A')
                            if summary.get('updated_count'):
                                st.write(f"既存行を更新した件数（model_version_id 埋め等）: {summary.get('updated_count')}")
                            if summary.get('sample_ids'):
                                st.write('サンプル civitai_id: ' + ', '.join(summary.get('sample_ids')))
                            if summary.get('api_total') is not None:
                                st.write(f"API が報告する総件数: {summary.get('api_total')}")
                    except Exception:
                        pass
                    col_refresh, col_open, col_remove = st.columns([1,2,1])
                    with col_refresh:
                        if st.button('更新', key=f'refresh_{j["id"]}'):
                            try:
                                st.session_state['__refresh_ts'] = time.time()
                                if hasattr(st, 'experimental_rerun'):
                                    st.experimental_rerun()
                            except Exception:
                                pass
                    with col_open:
                        if st.button('ログを別ウィンドウで開く', key=f'open_{j["id"]}'):
                            st.write(f"PowerShell コマンド: Get-Content {j.get('log_file')} -Wait -Tail 200")
                    with col_remove:
                        if st.button('リストから削除', key=f'remove_{j["id"]}'):
                            try:
                                st.session_state['collect_jobs'] = [x for x in st.session_state['collect_jobs'] if x['id'] != j['id']]
                                if hasattr(st, 'experimental_rerun'):
                                    st.experimental_rerun()
                            except Exception:
                                pass
        else:
            st.info('収集中のジョブはありません。')

    with tab1:
        st.header("ダッシュボード")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("表示中のプロンプト", len(df))
        with col2:
            if 'confidence' in df.columns:
                avg_confidence = df['confidence'].mean()
                st.metric("平均信頼度", f"{avg_confidence:.2f}")
            else:
                st.metric("平均信頼度", "N/A")
        with col3:
            unique_models = df['model_name'].nunique()
            st.metric("使用モデル数", unique_models)
        with col4:
            categories_count = df['category'].nunique()
            st.metric("カテゴリ数", categories_count)

        col1, col2 = st.columns(2)
        with col1:
            pie_chart = create_category_distribution_chart(df)
            if pie_chart:
                display_chart(pie_chart, use_container_width=True)
        with col2:
            hist_chart = create_confidence_histogram(df)
            if hist_chart:
                display_chart(hist_chart, use_container_width=True)

    with tab2:
        st.header("プロンプト一覧")
        page_size = 50
        total_items = len(df)
        total_pages = max(1, math.ceil(total_items / page_size))
        colp1, colp2 = st.columns([1, 3])
        with colp1:
            page = st.number_input("ページ", min_value=1, max_value=total_pages, value=1, step=1, format="%d")
        with colp2:
            st.write(f"表示: {page_size} 件/ページ — 合計 {total_items} 件 / 全 {total_pages} ページ")
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        display_df = df.iloc[start_idx:end_idx]
        st.write(f"表示中: {len(display_df)} / {len(df)} 件 (ページ {page}/{total_pages})")
        for idx, row in display_df.iterrows():
            display_prompt_card(row)

    with tab3:
        st.header("詳細分析")
        if not stats['category_stats'].empty:
            st.subheader("カテゴリ別統計")
            try:
                category_chart = px.bar(stats['category_stats'], x='category', y='count', title='カテゴリ別プロンプト数', labels={'count': 'プロンプト数', 'category': 'カテゴリ'}, color='avg_confidence', color_continuous_scale='viridis')
                display_chart(category_chart, use_container_width=True)
            except Exception:
                st.write(stats['category_stats'])

        st.subheader("モデル別統計")
        model_stats = df['model_name'].value_counts().head(10)
        try:
            model_chart = px.bar(x=model_stats.values, y=model_stats.index, orientation='h', title='上位10モデル使用頻度', labels={'x': 'プロンプト数', 'y': 'モデル名'})
            display_chart(model_chart, use_container_width=True)
        except Exception:
            st.write(model_stats)

    with tab4:
        st.header("データエクスポート")
        export_df = df.copy()
        available_columns = export_df.columns.tolist()
        selected_columns = st.multiselect("エクスポートするカラムを選択", options=available_columns, default=available_columns, key='selected_columns')
        if selected_columns:
            export_df = export_df[selected_columns]
        st.subheader("プレビュー")
        st.dataframe(export_df.head(5), use_container_width=True)
        csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(label="📥 CSVダウンロード", data=csv_data, file_name=f"civitai_prompts_{len(export_df)}件.csv", mime="text/csv")
        st.info(f"エクスポート対象: {len(export_df)} 件")

if __name__ == "__main__":
    main()

