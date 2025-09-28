
# CivitAI Prompt Collector v2 修正・検証・失敗詳細レポート

## 1. 目的・要件
- Streamlit UIでCivitAIプロンプト収集フロー「確認2回目」を完全に可視化・実行可能にする。
- DB仕様変更（テーブル追加・カラム追加・migration対応）
- 収集ジョブ状態・進捗・結果のリアルタイム表示

---


## 2. 主要な修正コード・改変内容（src/UI/runner/スクリプト全体）

### 2.1 DBスキーマ・config・database
- `src/config.py` の `DB_SCHEMA` に `collection_state` テーブル追加（上記参照）
- `prompt_resources` テーブル追加、`civitai_prompts` に `model_version_id` カラム追加（migration対応）
- `src/database.py`：
  - migrationロジック追加（テーブル/カラム追加、既存DBとの互換性維持）
  - `save_prompt_resources` など新規メソッド追加
  - `get_collection_state_for_version` でジョブ状態取得

### 2.2 runner/collectスクリプト
- `scripts/run_one_collect.py`：
  - `--log-file` オプション追加、Loggerクラスでstdout/stderrをファイルに出力
  - 収集完了時に `set_job_status()` でstatus=completed、`write_job_summary()` でsummary_jsonをDBに記録
  - summary_jsonの内容例（上記参照）
- `scripts/collect_from_ui.py`：
  - UIからサブプロセスで起動、進捗・結果をログファイルに出力
  - DB件数・API件数のプレビューをログに記録
  - 収集完了時にDBへsummary_jsonを書き込み
- `scripts/automated_ui_test.py`：
  - UIと同じフローでrunnerを起動し、DB・ログ・UIの状態を自動検証

### 2.3 src/配下の修正
- `src/collector.py`：
  - `check_total_items` 追加（APIから件数取得）
  - `collect_dataset` に max_items, append_only, strict_version_match オプション追加
- `src/categorizer.py`：
  - DBのプロンプトを再分類する `process_database_prompts` 追加
- `src/visualizer.py`：
  - matplotlib/plotly両対応のグラフ生成関数追加

### 2.4 UI (`ui/streamlit_app.py`/`ui/streamlit_app_collect.py`)
- 収集タブ追加（`streamlit_app_collect.py`）
  - モデルID/バージョンID入力、DB件数/API件数プレビュー、収集開始ボタン
  - 収集ジョブの進捗・状態・ログtail・summary_jsonをUIで表示
  - DB summary_jsonが空の場合は「収集結果なし」と明示
  - 収集ジョブID（model_id, version_id, job_id）をUIで表示
- 収集タブのUIロジック例（サンプルコード）:
  - DB自動判定で「初回 or 追加」分岐
  - API件数確認で「計画的収集 or カーソル方式」分岐
  - UI側では「収集ボタン」を押すだけ
  - 詳細は `ui/streamlit_app_collect.py` および「UI収集タブ改修案」参照

### 2.5 continuous_collector.py
- ルート直下にshim（ダミー）追加：`continuous_collector.py` → `scripts/continuous_collector.py` を動的import
  - 互換性維持のため、import時に本体を読み込む

### 2.6 新規/移動/アーカイブスクリプト
- `scripts/archive/` 配下に検証・分析・APIプローブ・DBチェック用スクリプト多数追加
  - 例：`analyze_raw_metadata.py`, `check_diff_version.py`, `debug_fetch_pages.py`, `probe_api.py` など

### 2.7 README/ドキュメント
- `scripts/README_FULL_COLLECTION.md`：フル収集手順・推奨コマンド
- `scripts/README_START_STREAMLIT.md`：Streamlit起動手順・ログ保存方法

---

## 3. UI・src・runnerの失敗点・未達成点

### 3.1 UIの問題
- 収集ジョブの状態・結果が確実に表示されない（summary_jsonが空の場合「収集結果なし」）
- DB件数/API件数のプレビューは出るが、保存件数0/少数の原因が分かりづらい
- 収集タブの「初回/追加/件数不明」分岐はサンプルコードのみで本番UIに未統合
- ジョブ進捗・完了・失敗のUI表示が不安定（ログtail解析に依存）
- UIキャッシュクリア・再分類タイミングが不明瞭

### 3.2 src/runnerの問題
- migration・互換性対応が場当たり的で、DB構造が複雑化
- runnerがsummary_jsonを正しく記録しない場合がある
- append_only/strict_version_matchの挙動が一部不安定
- DBクエリが失敗する場合がある（job_id不一致、summary_json未記録）

### 3.3 GPT改変・混乱
- 複数のGPTエージェントによる修正・上書きでロジックが分断
- DB・UI・runner間のインターフェースが頻繁に変更

---

## 4. 追加証跡・関連ファイル
- `src/config.py`, `src/database.py`, `src/collector.py`, `src/categorizer.py`, `src/visualizer.py`：主要ロジック
- `ui/streamlit_app.py`, `ui/streamlit_app_collect.py`：UIロジック
- `scripts/run_one_collect.py`, `scripts/collect_from_ui.py`, `scripts/automated_ui_test.py`：runner/UI連携・テスト
- `scripts/archive/` 配下：検証・分析・APIプローブ・DBチェック
- `scripts/README_FULL_COLLECTION.md`, `scripts/README_START_STREAMLIT.md`：運用手順
- `continuous_collector.py`：shim（互換性維持）

---

## 5. まとめ・今後の改善案
- UIでDB状態・エラー・進捗をより明確に可視化（「初回/追加/件数不明」分岐の本番統合）
- runner/DB/UI間のインターフェース仕様統一
- DBスキーマ・migration履歴の明文化
- 収集ジョブの状態・結果をリアルタイムでUIに反映
- 仕様変更時は必ずレポート・履歴を残す
- append_only/strict_version_matchの挙動安定化

---

このレポートは2025年9月26日時点のコードベース・DB構造・UI/runner/DB連携の実態、テスト・失敗・証跡を詳細に記録したものです。追加の証跡・履歴・コード差分が必要な場合はご指示ください。

---

## 3. テスト・検証履歴

### 3.1 テストコード例
- `scripts/automated_ui_test.py` で自動UIテスト：
  - モデルメタデータ取得
  - バージョンID選択
  - runner起動（subprocessでrun_one_collect.py）
  - collection_stateをDBから取得しJSON表示
  - runnerログ・streamlitログのtailを表示

### 3.2 テストジョブ
- model_id=974693, version_id=1736657, job_id=b0c23b23
- model_id=974693, version_id=1906683, job_id=47492453

### 3.3 テスト結果・ログ
- runnerは summary_json をDBに書き込むが、UIで結果が表示されないケース多数
- UIで「ログなし」「収集結果なし」と表示されることが多い
- DBには summary_json, status, attempted, duplicates, saved, planned_total が記録されているが、summary_jsonが空の場合が多い
- UIは summary_jsonが空の場合に「収集結果なし」と表示する仕様
- ログ例：
  ```
  Collected total=100, valid=100
  Saved 80 items to DB
  Batch result: attempted=100 new_saved=80 duplicates=20
  [Done] Collected unique prompts: ... saved=80
  [DB] sample civitai_ids: [123,456,...]
  API preview: totalItems reported -> 1243
  === Collection finished at ... ===
  ```

---

## 4. 失敗の原因・経緯

### 4.1 DB仕様変更による互換性問題
- 既存DBとのmigrationで一部カラム追加失敗・データ不整合
- テーブル追加・カラム追加が複数回発生し、DB構造が複雑化

### 4.2 UIとDBの連携不全
- summary_jsonが空の場合、UIで「収集結果なし」と表示される
- runnerがsummary_jsonを正しく記録しない場合がある
- UIの変更がユーザーにとって「見える」形で反映されていない

### 4.3 ロジックの混乱・GPTによる改変
- 複数のGPTエージェントによる修正・上書きでロジックが分断
- migration・互換性対応が場当たり的になり、コードベースが混乱
- DB・UI・runner間のインターフェースが頻繁に変更

---

## 5. 参考ログ・証跡
- `scripts/collect_from_ui.py` で収集開始時にDB件数・API件数をログ出力
- `scripts/check_db_counts.py` でDBの件数確認
- `scripts/check_summary.py` でcollection_stateのsummary_json確認
- `scripts/archive/debug_fetch_pages.py` でAPIとDBのID差分を検証
- `scripts/backfill_prompt_resources.py` でDBバックアップ・リソース再構築

---

## 6. まとめ・今後の改善案
- DBスキーマ・migration履歴の明文化
- UIでDB状態・エラー・進捗をより明確に可視化
- runner/DB/UI間のインターフェース仕様統一
- 収集ジョブの状態・結果をリアルタイムでUIに反映
- 仕様変更時は必ずレポート・履歴を残す

---

このレポートは2025年9月26日時点のコードベース・DB構造・UI/runner/DB連携の実態、テスト・失敗・証跡を詳細に記録したものです。追加の証跡・履歴・コード差分が必要な場合はご指示ください。
