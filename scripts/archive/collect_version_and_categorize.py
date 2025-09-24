#!/usr/bin/env python3
"""
指定モデルIDとバージョンIDでデータを収集し、DBへ保存、カテゴライズして件数増加を検証するランナースクリプト
Usage: python scripts/collect_version_and_categorize.py
"""
import sys
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
sys.path.insert(0, SRC)

# src をパッケージとして登録してから安全に import する
import importlib
import types
pkg_name = 'src'
if pkg_name not in sys.modules:
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [SRC]
    sys.modules[pkg_name] = pkg

from src.collector import CivitaiPromptCollector
from src.database import DatabaseManager, save_prompts_batch
from src.categorizer import PromptCategorizer, process_database_prompts


MODEL_ID = "101055"        # ユーザ指定モデルID
VERSION_ID = "126613"      # ユーザ指定バージョンID (modelVersionId)
MAX_ITEMS = 50


def main():
    print(f"Starting collection: model_id={MODEL_ID}, version_id={VERSION_ID}, max_items={MAX_ITEMS}")

    db = DatabaseManager()
    initial_total = db.get_total_prompts_count()
    print(f"Initial total prompts in DB: {initial_total}")

    collector = CivitaiPromptCollector()

    # Collect by version id (collector treats numeric model_id as modelVersionId)
    result = collector.collect_dataset(model_id=VERSION_ID, model_name=f"Model_{MODEL_ID}", max_items=MAX_ITEMS)

    items = result.get('items', [])
    print(f"Collected {result.get('collected', 0)} total, {len(items)} valid items to save")

    # Save batch
    saved = save_prompts_batch(db, items)
    print(f"Saved {saved} items to DB")

    # Run categorization (this function reclassifies all DB prompts)
    print("Running categorization (reclassify all prompts)...")
    process_database_prompts()

    final_total = db.get_total_prompts_count()
    print(f"Final total prompts in DB: {final_total}")

    delta = final_total - initial_total
    print(f"Total increased by: {delta} (expected approximately {saved})")

    if delta >= saved:
        print("SUCCESS: DB total increased by at least the number of saved items.")
    else:
        print("WARNING: DB total did not increase by the full saved amount. Some items may have been upserted/duplicates.")


if __name__ == '__main__':
    main()
