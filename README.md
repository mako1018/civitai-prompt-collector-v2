# civitai-prompt-collector-v2

CivitAIからプロンプトデータを収集・分析するPythonアプリケーション。

## 機能

- CivitAI APIから画像メタデータとプロンプトを収集
- SQLiteデータベースに保存
- Streamlit UIでデータ分析・収集操作
- 自動カテゴリ分類
- バックグラウンド収集ジョブ管理

## セットアップ

1. Python 3.13以上をインストール
2. 仮想環境作成: `python -m venv .venv`
3. アクティベート: `.venv\Scripts\activate` (Windows)
4. 依存関係インストール: `pip install -r requirements.txt`
5. DB初期化: `python -c "from src.database import DatabaseManager; DatabaseManager().setup_database()"`

## 使用方法

### UI起動
```bash
python -m streamlit run ui/streamlit_app.py
```

### コマンドライン収集
```bash
python scripts/run_one_collect.py --model-id 123 --version-id 456 --max-items 100
```

## プロジェクト構造

- `src/`: コアモジュール
  - `collector.py`: API収集ロジック
  - `database.py`: DB操作
  - `config.py`: 設定・スキーマ
- `ui/`: Streamlit UI
- `scripts/`: ユーティリティスクリプト
- `data/`: SQLite DBと出力
- `docs/`: ドキュメント

## 最近の改善 (2025年9月)

- DBスキーマ統一 (collection_stateテーブル追加)
- UIジョブ状態表示改善 (DB summary_json優先)
- runner summary_json記録強化
- migrationロジック改善
- テストスクリプト強化

詳細は `REPORT_STREAMLIT_FIXES_DETAIL.md` を参照。

## ドキュメント

- プロジェクトの説明や利用方法は `docs/README.md` をご覧ください。
- 引き継ぎ資料は `docs/README_Base/` と `docs/handover/` にあります。
