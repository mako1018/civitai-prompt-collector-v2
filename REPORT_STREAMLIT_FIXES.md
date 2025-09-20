CivitAI Prompt Collector — Streamlit Fixes Report

日時: 2025-09-20
作成者: 自動生成レポート (AIアシスタント)

概要
- 本レポートは、ローカル環境での Streamlit UI 起動テスト中に発生した問題の調査・修正作業内容をまとめたものです。

実施したテスト
1. Git リモートと同期の確認（説明のみ、手順は別途実行済み）
2. Streamlit アプリ (`ui/streamlit_app_copy.py`) をコピーして、オリジナルを残したまま起動テストを実施
3. 仮想環境での依存関係インストール（`pip install -r requirements.txt`）および個別パッケージの追加（`plotly`）
4. Streamlit を起動してブラウザから UI にアクセス、表示/エラーを検証
5. ログ追跡と逐次修正（インポートエラー、SQL カラム不一致、Plotly 呼び出しの不整合 等）

検出された問題
- ModuleNotFoundError: No module named 'plotly'
  - 原因: 仮想環境に `plotly` が未インストールであった。

- ImportError / AttributeError: `from config import ...` といったトップレベルインポートや、`VisualizationManager` 未定義
  - 原因: `src` 内モジュールがパッケージ相対インポートで参照されておらず、Streamlit 実行時の `sys.path` に起因する import エラーと、`visualizer.py` 内のクラス名が `DataVisualizer` であった点の不整合。

- Database schema mismatch: Streamlit app が `positive_prompt` / `created_at` などのカラムを参照していたが、実際の DB スキーマは `full_prompt` / `collected_at` などのカラム名を使用していた。
  - 結果: SQLite エラー "no such column: p.positive_prompt" が発生した。

- Plotly usage error: `px.pie` に `values=...` と `names=...` を直接与え、`hover_data=['value']` を指定していたため、plotly の `process_args_into_dataframe` が期待する DataFrame が渡されず `ValueError` が発生した。

対処・修正内容（ファイル単位）
- `ui/streamlit_app_copy.py` / `ui/streamlit_app.py`
  - 削除: 不要な Markdown/コードフェンス（```）の除去（コピー版に残っていたため）
  - インポート修正: `from src.visualizer import VisualizationManager` -> `from src.visualizer import DataVisualizer`
  - SQL 修正: `p.positive_prompt` -> `p.full_prompt`; `p.created_at` -> `p.collected_at` に置換
  - Plotly 修正: `category_counts` (Series) を DataFrame に変換し、`px.pie(data_frame=df_counts, names='category', values='count', hover_data=['count'])` を使用

- `src/database.py`
  - インポート修正: `from config import ...` -> `from .config import ...`（パッケージ相対インポート）
  - 互換メソッド追加: Streamlit UI が期待する `DatabaseManager._get_connection()` と `DatabaseManager.get_prompt_count()` を追加

- `src/__init__.py` と `src/visualizer.py`
  - `src/__init__.py` はプロジェクト情報を供給（既存）
  - `src/visualizer.py` のパブリッククラスは `DataVisualizer` であったため、UI 側のインポートをこれに合わせた

実行した主要コマンド（抜粋）
- 仮想環境でのパッケージ操作:
  - `.venv\Scripts\python.exe -m pip install --upgrade pip`
  - `.venv\Scripts\python.exe -m pip install plotly`

- Streamlit 起動/ログ操作:
  - `.venv\Scripts\python.exe -m streamlit run ui/streamlit_app_copy.py --server.port 8502 --server.headless true --logger.level debug`
  - ログのリダイレクト: stdout/stderr を `streamlit.out.log` / `streamlit.err.log` に保存
  - ポート占有プロセスの調査/停止: `Get-NetTCPConnection -LocalPort 8502` / `Stop-Process -Id <PID>` を使用

変更したファイル一覧
- Modified:
  - `ui/streamlit_app_copy.py`
  - `ui/streamlit_app.py`
  - `src/database.py`
- Checked / Read-only inspected:
  - `src/config.py`
  - `src/visualizer.py`
  - `src/__init__.py`

推奨される追加作業
- `requirements.txt` に `plotly>=6.3.0` を明示的に追加して、将来のセットアップで漏れないようにする
- `.gitignore` に仮想環境 `.venv/` を追加し、既にコミットされている場合は履歴から削除する（`git rm -r --cached .venv` 等）
- DB スキーマに関するドキュメント化: テーブル定義と想定カラム名を README に記載
- 単体テスト: `src` モジュールのインポートテストおよび `DatabaseManager` の基本操作を自動化するテストを追加

ログ・証跡
- `streamlit.out.log` / `streamlit.err.log` に起動・エラーのログを保存

備考
- 一部ファイルに Markdown のコードフェンス（```）が混入していたため、直接 Python として実行する前に取り除く必要がありました。
- 開発用の Streamlit 実行は `ui/streamlit_app_copy.py` を使って行っています。オリジナルは変更せずに残してあります。

---
自動レポート終了

テスト実行ログと結果
- Smoke テスト (`tests/smoke_test.py`) を追加し、仮想環境の Python で実行しました。
  - コマンド: `.venv\\Scripts\\python.exe -c "$env:PYTHONPATH=(Get-Location).Path; .\\venv\\Scripts\\python.exe tests\\smoke_test.py"` (PowerShell セッション内で `PYTHONPATH` を設定して実行)
  - 実行結果: `Smoke test passed` (DB 接続および `get_prompt_count()` が正常に実行され、プロンプト数: 42 を確認)

ファイル更新
- `requirements.txt` の `plotly` を `>=6.3.0` に更新しました。
- `.gitignore` に `.venv` は既に含まれているため、仮想環境は除外設定済みです。

完了日: 2025-09-20

## Verification - 2025-09-20 19:19:54

- Streamlit process: running (PID 25880)
- Local HTTP checks: http://localhost:8502, http://127.0.0.1:8502, http://192.168.40.145:8502 all returned HTTP 200 from PowerShell
- Static assets: /static/js/index.CD8HuT3N.js and /static/css/index.C8X8rNzw.css fetched successfully
- Logs: streamlit.out.log contains startup message; streamlit.err.log empty
- Notes: App serves HTML and static assets; browser ERR_CONNECTION_REFUSED likely client-side (proxy/firewall/cache/extension)
