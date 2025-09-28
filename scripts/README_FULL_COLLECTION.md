Full-collection recommended steps

This file documents recommended steps to run a full collection for a model/version.

1) Backup DB
   - Copy data/civitai_dataset.db to a timestamped backup before running full collection.

2) Smoke test
   - Run scripts/collect_images_safe.py for 1-2 pages (e.g. --max-items 200) to confirm credentials and API behavior.

3) Ensure DB schema
   - Verify collection_state table exists and has next_page_cursor column; run scripts/reset_db_for_test.py or migrate if needed.

4) Run full collection in controlled batches
   - Use scripts/collect_images_safe.py without --max-items to iterate until exhaustion.
   - Prefer running during off-peak hours, set page-size=100 and sleep=1.0.
   - Persist each page to DB using DatabaseManager.save_prompts_batch and update collection_state.next_page_cursor after successful DB commit.

5) Monitor and resume
   - Watch logs for rate-limit (429) or 5xx: pause/backoff and resume using saved cursor.

6) Post-processing
   - Run categorizer, compute statistics, and export visuals.

7) Safety
   - Use small max_pages or set an admin "stop" file to gracefully stop.

Example commands (PowerShell):

# Smoke test (200 items)
$env:PYTHONPATH = (Get-Location).Path; C:/APP/civitai-prompt-collector-v2/.venv/Scripts/python.exe scripts/collect_images_safe.py --version-id 1934796 --page-size 100 --max-items 200 --sleep 1.0

# Full run (no max, careful: long)
$env:PYTHONPATH = (Get-Location).Path; C:/APP/civitai-prompt-collector-v2/.venv/Scripts/python.exe scripts/collect_images_safe.py --version-id 1934796 --page-size 100 --sleep 1.0
