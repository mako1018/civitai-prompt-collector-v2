# 引継ぎレポート: Streamlit 収集タブ実装（Collect Tab）

作業日時: 2025-09-22
作業者: 開発チーム（自動生成レポート）

## 概要
このリポジトリに対して、Streamlit ベースの UI に「収集（Collect）」タブを追加し、CivitAI API からのプロンプト収集を UI からバックグラウンドで起動・監視できる仕組みを実装しました。主な要件は以下です。

- モデルID（またはバージョンID）を指定して収集開始できること
- モデル情報（モデル名、バージョン一覧）を取得して UI に反映できること
- 収集処理は UI からバックグラウンドジョブとして開始され、ログに出力されること
- UI上でジョブの状態（実行中/完了/失敗）を確認できること
- 収集完了後にデータベースに保存し、カテゴライズを実行するオプションを用意すること

さらに今回の作業で以下の運用改善と実装追加を行いました（重要）:

- Cursor（next_page_cursor）永続化: 収集中に API が cursor（metadata.nextPage）を返す場合、それを `collection_state.next_page_cursor` に保存し、次回の収集はこの cursor から再開します。これによりサーバーがページ番号ベースで同一 ID を返す場合の重複取得を回避します。
- ハイブリッド自動進行: ランナー（`scripts/run_one_collect.py`）に `--auto-advance-on-empty` を追加しました。これを指定すると、収集結果が既に DB に存在して新規が0件の場合でも `last_offset` と `next_page_cursor` を進めて、次回は前回の続きから再開します（運用での継続収集に適します）。
- 反復実行ランナー: `--repeat` / `--max-iterations` / `--repeat-sleep` オプションを追加し、一定間隔で継続収集を自動で繰り返すことができます（短時間バッチ運用に便利）。
- DB マイグレーション: 既存の DB に `next_page_cursor` カラムが無い場合、自動で `ALTER TABLE` を試みるロジックを追加しました（起動時にカラムを追加）。
- Page ガード: page ベースのリクエストでページ番号が一定値（例: 10）を超える場合、cursor が無ければリクエストを停止するガードを追加しました。これにより 429 (rate limit / too many pages) を避けられます。

これらの改善は「継続的にデータを収集したい」という運用ニーズに直接応えるための対応です。

## 変更点（ファイル）
- 追加 / 変更
  - `ui/streamlit_app_collect.py` (更新)
    - 収集用の入力 UI（Model ID, Version 選択, Model 名, Max items, Run options）を追加
    - `モデル情報を取得` ボタンで CivitAI の `/models/{id}` エンドポイントを呼び、モデル名とバージョン一覧を session_state に保存
    - バックグラウンドジョブ開始時に `scripts/collect_from_ui.py` を `subprocess.Popen` で起動し、`scripts/collect_job_{job_id}.log` にログ出力する運用に変更
    - ジョブ一覧を `st.session_state['collect_jobs']` で管理し、各ジョブごとにログ末尾（最大80行）を表示する expander を追加
    - ログの文言を解析してジョブを `running` / `completed` / `failed` に推定するロジックを追加
  - `scripts/collect_from_ui.py` (既存): サブプロセス起動から実際の収集処理を行うラッパー（既に存在）
  - `src/collector.py` (既存): 収集ロジックに "モデルID として指定された数値を modelVersionId として扱っても結果が無い場合、/models/{id} を呼んで version を抽出して再試行するフォールバックが含まれる（既に実装済み）

- 新規追加ドキュメント
  - `docs/handover/handover_report_collect_tab.md` (本ファイル)

## 実装の詳細
- UI 側
  - `model_id_input` に文字列（通常は数値）を入力して `モデル情報を取得` を押すと、API から `name` と `modelVersions` を取得します。取得後、`model_name_input` と `model_versions` を `st.session_state` に保存します。
  - `model_versions` が設定されている場合、`selectbox` で選択可能になります。選択は `"{id} - {name}"` 形式の文字列として扱い、選択時に ID 部分を抽出して `version_id` に設定します。
  - `収集開始（バックグラウンド）` ボタンはバージョンIDが必須の設定になっています（`version_required=True`）。開始時に job オブジェクトを `st.session_state['collect_jobs']` に格納します。
  - ジョブの expander 内ではログの末尾を表示し、`更新` / `ログを別ウィンドウで開く` / `リストから削除` の操作が可能です。ログが `Saved ...` や `Categorization finished`、`=== Collection finished` を含むと完了と判定されます。

- collector 側
  - 収集処理は `src.collector.CivitaiPromptCollector` が担当し、`scripts/collect_from_ui.py` が CLI ラッパーになっています。
  - 収集完了後、オプションによりデータベース保存とカテゴライズ（`src.categorizer.process_database_prompts`）を実行します。

## ランナーと CLI フラグ（今回追加）

- `--auto-advance-on-empty`:
  - 説明: 収集バッチが全て既に DB に存在して新規が `0` の場合でも `collection_state.last_offset` と `next_page_cursor` を進めます（hybrid 動作）。
  - 利点: サーバーが同じIDを先頭ページで繰り返す問題がある場合に、毎回1ページ目から始まることを避けて継続的に取得できます。
  - 注意点: `total_collected` は DB の実際の件数を優先して同期するため、`total_collected` の不整合は基本的に発生しません。

- `--repeat`, `--max-iterations`, `--repeat-sleep`:
  - 説明: 指定した回数または無制限で収集を繰り返します。`--repeat-sleep` は反復間の待機秒数です。
  - 利点: 長時間の継続収集を CLI だけで行う際に便利です。UI からのバックグラウンド実行と併用可能です。

## マイグレーションと互換性

- 既存 DB に `next_page_cursor` カラムがない場合、`ContinuousCivitaiCollector._get_collection_state` は起動時に `PRAGMA table_info(collection_state)` でカラムを確認し、必要なら `ALTER TABLE ... ADD COLUMN next_page_cursor TEXT` を実行します。ALTER に失敗した場合は警告ログを出しますが、操作は継続されます。

## 実行例（CLI）

- 単発（自動進行あり）:
```pwsh
python .\scripts\run_one_collect.py --model-id 82543 --version-id 2043971 --max-items 150 --auto-advance-on-empty
```

- 反復（5 回）:
```pwsh
python .\scripts\run_one_collect.py --model-id 82543 --version-id 2043971 --max-items 150 --auto-advance-on-empty --repeat --max-iterations 5 --repeat-sleep 2
```

## 例: 実行ログの読み方（今回のサンプル）
- `Migrated collection_state: added next_page_cursor column` — 既存 DB にカラムがなかったため追加しました。
- `Collected: 150 Valid: 79` — 1 回の run_one_collect が 150 件フェッチを試み、79 件が有効（保存候補）でした。
- `DB Batch save completed: 0/79 new items` — 今回はすでに DB に存在するアイテムが多く新規はゼロでした。
- `Auto-advanced collection_state to next_offset=300 (no new items)` — `--auto-advance-on-empty` により offset を進めました。

## ログ例と完了検出
- 収集ログの例（抜粋）:
```
=== Collection started at 2025-09-22T17:33:05.485202 ===
Params: model_id=277058, version_id=, model_name=, max_items=50, save=True, categorize=True
Collecting...
Collected total=50, valid=50
Saved 50 items to DB
Running categorization...
Categorization finished.
=== Collection finished at 2025-09-22T17:33:17.801898 ===
```
- UI は上記の `Saved` / `Categorization finished` / `Collection finished` を完了マーカーとして判定します。

## 動作確認手順
1. Streamlit を起動:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_streamlit_capture.ps1 -Port 8503
# または
.venv\Scripts\python.exe -m streamlit run ui/streamlit_app_collect.py --server.port 8503
```

2. ブラウザで `http://localhost:8503` を開き、`🔎 収集` タブを選択。
3. `Model ID` に `277058` などを入力し、`モデル情報を取得` を押す。
4. `Version` を選択し（または Version ID を直接入力）、`収集開始（バックグラウンド）` を押す。
5. ジョブが開始されると `scripts/collect_job_{id}.log` が作られるので、PowerShell で次を実行してログをリアルタイムで観察できます:

```powershell
Get-Content .\scripts\collect_job_<ID>.log -Wait -Tail 200
```

6. UI の `収集ジョブの状態` セクションで expander を開くとログが末尾（最大80行）表示され、完了時は「状態: 完了」と表示されます。

## 今後の改善案（優先度付け）
- 高: UI 上でログを自動ポーリングして完了を自動で更新する（2-5 秒間隔）。完了時に `st.toast` または視覚的な通知を表示。
- 中: 完了ジョブの自動クリーニング（例: 完了後 1 日で非表示）やフィルタ（完了/実行中のみ表示）トグルを追加。
- 中: ジョブキャンセル機能（起動したプロセスIDを保存・kill 実装）。Windows では権限と安全性の確認が必要。
- 低: UI 上でログのストリーミング表示（WebSocket 風に小分けして表示）して、よりリアルなライブログにする。

さらに今回の作業に基づく追加案（優先度）:
- 高: `--start-offset` フラグをランナーに追加して、運用者が任意のオフセットから再開できるようにする（即効性が高くページ制限に強い）。
- 高: DB マイグレーションを別スクリプト `scripts/migrate_db.py` として切り出し、安全に一度だけ実行できるようにする（CI/運用での確実性向上）。
- 中: `collection_state` に `last_successful_fetch_at` と `last_page_number` などのメタデータを追加して運用監視を充実させる。

## 引き継ぎ要約
- 目的: Streamlit UI から CivitAI のプロンプト収集を起動・監視し、継続的に（前回の続きから）データを取り続けられる運用を実現しました。
- 重要な変更点:
  - UI の `Collect` タブ実装とバックグラウンドジョブ起動（`scripts/collect_from_ui.py` 経由）。
  - `continuous_collector.py`：cursor 永続化、バッチ内 dedupe、ページガードを追加。
  - `scripts/run_one_collect.py`：`--auto-advance-on-empty`, `--repeat` 系オプション、state 同期ロジックを追加。
  - DB 互換性: 起動時に `next_page_cursor` カラムを自動追加するマイグレーションを追加。
- 運用の注意点:
  - デフォルトでは state は DB に保存された新規件数に基づき更新されます（安全）。自動進行が必要な場合は `--auto-advance-on-empty` を付けて実行してください。
  - API のページング実装は安定しないことがあるため、cursor を優先して利用する運用が望ましいです。

必要であれば、このドキュメントを PDF に変換したり、社内引き継ぎ用のスライド（PowerPoint/MDX）を作成します。どちらが良いですか？

## 付録: 変更履歴
- 2025-09-22: `ui/streamlit_app_collect.py` に収集 UI とジョブ管理機能を追加、完了判定ロジックをログ文言に合わせて調整。

---

以上。必要ならこのファイルをベースに README への抜粋や社内ハンドオーバー資料の整備を行います。どの形式で作り直しますか（PDF/Markdown/スライド）?
