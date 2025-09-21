#!/usr/bin/env python3
"""
CivitAI Prompt Collector - メイン実行ファイル
collector.py、categorizer.py、visualizer.pyを統合実行

保存先: プロジェクトルート/main.py
実行方法: python main.py
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# プロジェクト内モジュールのインポート - 仮想環境なし対応版
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')

# srcディレクトリをPythonパスに追加（最優先）
sys.path.insert(0, src_path)

try:
    # src をパッケージとして登録してから importlib で読み込む
    import importlib
    import types

    pkg_name = 'src'
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [src_path]
        sys.modules[pkg_name] = pkg

    # src パッケージ配下のモジュールを安全に読み込む
    config = importlib.import_module('src.config')
    collector = importlib.import_module('src.collector')
    categorizer = importlib.import_module('src.categorizer')
    visualizer = importlib.import_module('src.visualizer')
    database = importlib.import_module('src.database')

    # 必要な要素を個別に取得
    CIVITAI_API_KEY = config.CIVITAI_API_KEY
    DEFAULT_MODELS = config.DEFAULT_MODELS
    DEFAULT_MAX_ITEMS = config.DEFAULT_MAX_ITEMS

    CivitaiPromptCollector = collector.CivitaiPromptCollector
    process_database_prompts = categorizer.process_database_prompts
    DataVisualizer = visualizer.DataVisualizer
    DatabaseManager = database.DatabaseManager

    print("モジュール読み込み完了")

except ImportError as e:
    print(f"インポートエラー: {e}")
    print(f"現在のディレクトリ: {current_dir}")
    print(f"srcパス: {src_path}")
    print(f"srcディレクトリ存在: {os.path.exists(src_path)}")
    if os.path.exists(src_path):
        print(f"srcディレクトリ内容: {os.listdir(src_path)}")
    sys.exit(1)
except AttributeError as e:
    print(f"属性エラー: {e}")
    print("config.pyまたは他のファイル内の定義を確認してください")
    sys.exit(1)

def print_banner():
    """プロジェクトバナー表示"""
    print("=" * 60)
    print("🤖 CivitAI Prompt Collector v2.0")
    print("プロンプト収集・自動分類・可視化ツール")
    print("=" * 60)

def check_environment() -> bool:
    """環境・設定チェック"""
    print("🔍 環境チェック中...")

    # APIキー確認
    if not CIVITAI_API_KEY or CIVITAI_API_KEY == "your_api_key_here":
        print("❌ CivitAI APIキーが設定されていません")
        print("   config.py の CIVITAI_API_KEY を設定してください")
        return False

    print("✅ APIキー設定確認")

    # データディレクトリ確認・作成
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    viz_dir = data_dir / "visualizations"
    viz_dir.mkdir(exist_ok=True)

    print("✅ ディレクトリ構造確認")
    return True

def run_collection(max_items: int = DEFAULT_MAX_ITEMS, model_id: Optional[str] = None) -> bool:
    """データ収集実行"""
    print(f"\n📦 データ収集開始 (最大{max_items}件)")

    try:
        collector = CivitaiPromptCollector()
        db = DatabaseManager()

        if model_id:
            # 指定モデル収集
            result = collector.collect_dataset(
                model_id=model_id,
                model_name=f"Model_{model_id}",
                max_items=max_items
            )
        else:
            # デフォルトモデル収集
            model_name, model_id = next(iter(DEFAULT_MODELS.items()))
            result = collector.collect_dataset(
                model_id=model_id,
                model_name=model_name,
                max_items=max_items
            )

        # データベース保存
        saved_count = 0
        for item in result.get('items', []):
            if db.save_prompt_data(item):
                saved_count += 1

        print(f"✅ 収集完了:")
        print(f"  - 総取得数: {result.get('collected', 0)}件")
        print(f"  - 有効データ: {result.get('valid', 0)}件")
        print(f"  - データベース保存: {saved_count}件")

        return saved_count > 0

    except Exception as e:
        print(f"❌ 収集エラー: {e}")
        return False

def run_categorization() -> bool:
    """プロンプト分類実行"""
    print(f"\n🏷️  プロンプト自動分類開始")

    try:
        # categorizer.pyのprocess_database_prompts()を呼び出し
        process_database_prompts()
        print("✅ 分類完了")
        return True

    except Exception as e:
        print(f"❌ 分類エラー: {e}")
        return False

def run_visualization() -> bool:
    """データ可視化実行"""
    print(f"\n📊 データ可視化開始")

    try:
        visualizer = DataVisualizer()

        # 統計サマリー表示
        summary = visualizer.generate_statistics_summary()
        if "error" not in summary:
            print("\n=== 統計サマリー ===")
            for key, value in summary.items():
                print(f"{key}: {value}")

        # 全グラフ生成
        results = visualizer.generate_all_visualizations()

        if "error" not in results:
            print(f"\n✅ 可視化完了:")
            for graph_type, file_path in results.items():
                if file_path and Path(file_path).exists():
                    print(f"  - {graph_type}: {file_path}")

        return True

    except Exception as e:
        print(f"❌ 可視化エラー: {e}")
        return False

def show_database_status():
    """データベース状況表示"""
    try:
        db = DatabaseManager()

        # プロンプト数取得
        prompts = db.get_all_prompts()
        prompt_count = len(prompts)

        # 分類済み数取得 - SQLite直接接続で修正
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM prompt_categories')
        categorized_count = cursor.fetchone()[0]
        conn.close()

        print(f"\n📊 データベース状況:")
        print(f"  - 総プロンプト数: {prompt_count}件")
        print(f"  - 分類済み数: {categorized_count}件")

        if prompt_count > 0:
            completion_rate = (categorized_count / prompt_count) * 100
            print(f"  - 完了率: {completion_rate:.1f}%")

    except Exception as e:
        print(f"データベース状況確認エラー: {e}")
        # 基本情報のみ表示
        try:
            db = DatabaseManager()
            prompts = db.get_all_prompts()
            print(f"\n📊 データベース状況:")
            print(f"  - 総プロンプト数: {len(prompts)}件")
        except Exception as inner_e:
            print(f"  - データベース接続エラー: {inner_e}")

def main():
    """メイン実行関数"""
    # コマンドライン引数解析
    parser = argparse.ArgumentParser(
        description="CivitAI Prompt Collector - プロンプト収集・分類・可視化ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                     # 全フロー実行
  python main.py --collect-only      # 収集のみ
  python main.py --categorize-only   # 分類のみ
  python main.py --visualize-only    # 可視化のみ
  python main.py --max-items=100     # 最大100件収集
  python main.py --model-id=2091367  # 指定モデル収集
        """
    )

    # 実行オプション
    parser.add_argument('--collect-only', action='store_true', help='データ収集のみ実行')
    parser.add_argument('--categorize-only', action='store_true', help='プロンプト分類のみ実行')
    parser.add_argument('--visualize-only', action='store_true', help='データ可視化のみ実行')
    parser.add_argument('--status', action='store_true', help='データベース状況確認のみ')

    # 収集設定
    parser.add_argument('--max-items', type=int, default=DEFAULT_MAX_ITEMS, help=f'最大収集件数 (デフォルト: {DEFAULT_MAX_ITEMS})')
    parser.add_argument('--model-id', type=str, help='収集対象モデルID')

    # デバッグオプション
    parser.add_argument('--no-env-check', action='store_true', help='環境チェックをスキップ')

    args = parser.parse_args()

    # バナー表示
    print_banner()

    # 環境チェック
    if not args.no_env_check and not check_environment():
        sys.exit(1)

    # 状況確認のみ
    if args.status:
        show_database_status()
        return

    # 実行フラグ設定
    run_collect = args.collect_only or not (args.categorize_only or args.visualize_only)
    run_category = args.categorize_only or not (args.collect_only or args.visualize_only)
    run_visual = args.visualize_only or not (args.collect_only or args.categorize_only)

    success_count = 0
    start_time = time.time()

    # データ収集
    if run_collect:
        if run_collection(max_items=args.max_items, model_id=args.model_id):
            success_count += 1
        else:
            print("\n⚠️ データ収集に失敗しました")
            if not args.collect_only:
                print("   残りのフローをスキップします")
                sys.exit(1)

    # プロンプト分類
    if run_category:
        # 既存データ確認
        try:
            db = DatabaseManager()
            prompts = db.get_all_prompts()
            if not prompts:
                print("⚠️ 分類するプロンプトがありません")
                print("   先に --collect-only を実行してください")
            else:
                if run_categorization():
                    success_count += 1
        except Exception as e:
            print(f"分類前チェックエラー: {e}")

    # データ可視化
    if run_visual:
        # 既存データ確認
        try:
            db = DatabaseManager()
            prompts = db.get_all_prompts()
            if not prompts:
                print("⚠️ 可視化するデータがありません")
                print("   先に --collect-only を実行してください")
            else:
                if run_visualization():
                    success_count += 1
        except Exception as e:
            print(f"可視化前チェックエラー: {e}")

    # 完了サマリー
    elapsed_time = time.time() - start_time
    print(f"\n" + "=" * 60)
    print(f"🎯 実行完了!")
    print(f"  - 実行時間: {elapsed_time:.1f}秒")
    print(f"  - 成功フロー数: {success_count}")

    # データベース状況表示
    show_database_status()

    # 次のステップ提案
    if success_count > 0:
        print(f"\n💡 次のステップ:")
        if run_collect and not run_category:
            print("   python main.py --categorize-only  # プロンプト分類")
        elif run_category and not run_visual:
            print("   python main.py --visualize-only   # データ可視化")
        elif success_count == 3:
            print("   data/visualizations/ フォルダで結果を確認してください")

    print("=" * 60)

if __name__ == "__main__":
    main()
