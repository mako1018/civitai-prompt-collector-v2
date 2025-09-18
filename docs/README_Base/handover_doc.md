# CivitAI Prompt Collector - 引き継ぎドキュメント

## 現在の状況
- 既存のカオス状態のプロジェクトを一から再構築中
- civitai_collector_v8.py をベースに、機能別にファイル分割してクリーンな構造に

## 完了済みファイル
✅ config.py - 設定管理（カテゴリ定義、環境変数）
✅ requirements.txt - 最小限の依存関係  
✅ collector.py - API呼び出し、データ抽出
✅ database.py - SQLite操作、CRUD

## 未完了ファイル
🔲 categorizer.py - プロンプト自動分類
🔲 visualizer.py - グラフ生成、統計表示  
🔲 main.py - 実行用メインファイル
🔲 streamlit_app.py - UI実装

## 新プロジェクト構造
```
civitai-prompt-collector-v2/
├── src/
│   ├── __init__.py
│   ├── config.py         ✅
│   ├── collector.py      ✅  
│   ├── database.py       ✅
│   ├── categorizer.py    🔲
│   └── visualizer.py     🔲
├── ui/
│   └── streamlit_app.py  🔲
├── data/
├── requirements.txt      ✅
├── main.py               🔲
└── README.md
```

## READMEの目的・ルール
- 引き継ぎ用ドキュメントとして作成済み
- 目的・最終ゴール・運用ルールは維持
- 工程部分のみ実装に合わせて後で更新予定

## 次回最優先タスク
1. categorizer.py作成（プロンプト自動分類）
2. visualizer.py作成（グラフ表示）
3. main.py作成（実行用）
4. 動作テスト実施

## 重要な技術情報
- Python 3.13使用
- SQLite（civitai_dataset.db）
- CivitAI API v1使用
- 6カテゴリ自動分類（NSFW含む）
- 既存のcivitai_collector_v8.pyが動作確認済みの基準

## ユーザー情報
- プログラミング初心者
- VSCode使用、Windows環境
- トークン節約重視
- 説明は簡潔に

## 引き継ぎ時の最初の質問
「前回の続きから、categorizer.pyの作成をお願いします」
