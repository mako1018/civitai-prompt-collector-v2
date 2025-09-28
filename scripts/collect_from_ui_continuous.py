#!/usr/bin/env python3
"""
UI from background collection script - 連続収集対応版
オフセット管理で累積的にデータを取得
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import DatabaseManager
from src.categorizer import process_database_prompts


def main():
    parser = argparse.ArgumentParser(description='Collect CivitAI prompts with continuous collection')
    parser.add_argument('--model-id', default='', help='Model ID')
    parser.add_argument('--version-id', default='', help='Version ID (prioritized)')
    parser.add_argument('--model-name', default='', help='Model name for metadata')
    parser.add_argument('--max-items', type=int, default=50, help='Max items to collect')
    parser.add_argument('--save', action='store_true', help='Save to database')
    parser.add_argument('--no-save', action='store_true', help='Do not save to database')
    parser.add_argument('--categorize', action='store_true', help='Run categorization after collection')
    parser.add_argument('--no-categorize', action='store_true', help='Do not run categorization')
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--continuous', action='store_true', default=True, help='Use continuous collection (resume from last offset)')
    parser.add_argument('--reset', action='store_true', help='Reset collection state (start from beginning)')

    args = parser.parse_args()

    # ログ出力の設定
    if args.log_file:
        class Logger:
            def __init__(self, filename):
                self.terminal = sys.stdout
                self.log = open(filename, 'w', encoding='utf-8')

            def write(self, message):
                self.terminal.write(message)
                self.log.write(message)
                self.log.flush()

            def flush(self):
                self.terminal.flush()
                self.log.flush()

        sys.stdout = Logger(args.log_file)

    print(f"=== Collection started at {datetime.utcnow().isoformat()} ===")
    print(f"Params: model_id={args.model_id}, version_id={args.version_id}, model_name={args.model_name}, max_items={args.max_items}, continuous={args.continuous}, reset={args.reset}")

    try:
        # 連続収集コレクターを使用
        from continuous_collector import ContinuousCivitaiCollector
        collector = ContinuousCivitaiCollector()

        # リセットが要求された場合
        if args.reset:
            collector.reset_collection_state(
                args.model_id or "",
                args.version_id or ""
            )
            print("Collection state reset.")

        # 収集実行
        print("Collecting...")

        # target_id の決定
        if args.version_id.strip():
            target_version_id = args.version_id.strip()
            target_model_id = args.model_id.strip()
            use_version_api = True
        elif args.model_id.strip():
            target_version_id = ""
            target_model_id = args.model_id.strip()
            use_version_api = False
        else:
            print("Error: Either model_id or version_id must be provided")
            sys.exit(1)

        result = collector.collect_continuous(
            model_id=target_model_id,
            version_id=target_version_id,
            model_name=args.model_name.strip() if args.model_name.strip() else None,
            max_items=args.max_items,
            use_version_api=use_version_api
        )

        if "error" in result:
            print(f"Collection error: {result['error']}")
            sys.exit(1)

        print(f"Collected total={result['collected']}, valid={result['valid']}")
        print(f"Total ever collected: {result['total_ever_collected']}")
        print(f"Next collection will start from offset: {result['next_offset']}")

        # データベース保存
        save_enabled = not args.no_save
        if save_enabled and result['valid'] > 0:
            db = DatabaseManager()
            saved_count = 0
            duplicate_count = 0

            for item in result['items']:
                try:
                    if db.save_prompt_data(item):
                        saved_count += 1
                    else:
                        duplicate_count += 1
                except Exception as e:
                    print(f"Failed to save item {item.get('civitai_id', 'unknown')}: {e}")
                    duplicate_count += 1

            if duplicate_count > 0:
                print(f"Saved {saved_count} items to DB, {duplicate_count} duplicates skipped")
            else:
                print(f"Saved {saved_count} items to DB")

            # カテゴライズ実行
            if args.categorize and saved_count > 0:
                print("Running categorization...")
                try:
                    process_database_prompts()
                    print("Categorization finished.")
                except Exception as e:
                    print(f"Categorization failed: {e}")
        elif save_enabled:
            print("No valid items to save")
        else:
            print("Save disabled, items not saved to database")

    except Exception as e:
        print(f"Collection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        print(f"=== Collection finished at {datetime.utcnow().isoformat()} ===")

if __name__ == "__main__":
    main()
