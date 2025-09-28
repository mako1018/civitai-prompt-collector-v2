#!/usr/bin/env python3
"""
Run a single continuous collection job from PowerShell or CMD.
Usage:
  python ./scripts/run_one_collect.py --model-id 82543 --version-id 2043971 --max-items 50 --reset
"""
import argparse
import sys
from pathlib import Path
import time
import logging

# Ensure project root is importable
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from continuous_collector import ContinuousCivitaiCollector
    from src.database import DatabaseManager, save_prompts_batch
except Exception as e:
    print('[ERROR] Failed to import project modules:', e)
    raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--version-id', required=True)
    parser.add_argument('--max-items', type=int, default=50)
    parser.add_argument('--reset', action='store_true', help='Reset collection state before running')
    parser.add_argument('--auto-advance-on-empty', action='store_true', help='Advance offset even when no new items were saved (hybrid)')
    parser.add_argument('--repeat', action='store_true', help='Repeat collection runs until no more items or max-iterations reached')
    parser.add_argument('--max-iterations', type=int, default=0, help='Maximum number of iterations when --repeat is used (0 = unlimited)')
    parser.add_argument('--repeat-sleep', type=int, default=2, help='Seconds to sleep between repeated runs')
    parser.add_argument('--log-file', required=True)

    args = parser.parse_args()

    # Configure logging to file
    logging.basicConfig(
        filename=args.log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )

    logger = logging.getLogger(__name__)

    # Redirect stdout to log file as well for any print statements from imported modules
    log_file_handle = open(args.log_file, 'a', encoding='utf-8')
    sys.stdout = log_file_handle
    sys.stderr = log_file_handle

    collector = ContinuousCivitaiCollector()
    model_id = str(args.model_id)
    version_id = str(args.version_id)

    logger.info('DB path = %s', collector.db_path if hasattr(collector, 'db_path') else 'unknown')

    if args.reset:
        logger.info('Resetting collection state for %s / %s', model_id, version_id)
        try:
            collector.reset_collection_state(model_id, version_id)
        except Exception as e:
            logger.warning('reset_collection_state failed: %s', e)

    # Interpret max_items==0 as unlimited (use a large cap)
    if args.max_items is None or args.max_items == 0:
        max_items = 10_000_000
    else:
        max_items = args.max_items

    iteration = 0
    consecutive_empty = 0
    while True:
        iteration += 1
        logger.info('Starting collection (iteration %d)...', iteration)
        # Mark job as running in collection_state
        try:
            collector.set_job_status(model_id, version_id, 'running', planned_total=max_items)
        except Exception:
            pass

        res = collector.collect_continuous(model_id=model_id, version_id=version_id, model_name=None, max_items=max_items, use_version_api=True)
        logger.info('Collected: %s Valid: %s', res.get('collected'), res.get('valid'))
        logger.info('Next offset: %s', res.get('next_offset'))

        if res.get('valid', 0) > 0:
            db = DatabaseManager()
            # Quick sync: ensure collection_state.total_collected matches DB count if inconsistent
            try:
                # get current recorded state
                state = collector._get_collection_state(model_id, version_id)
                db_count = db.get_total_prompts_count()
                if state.get('total_collected', 0) != db_count:
                    logger.info("[State] Detected mismatch: state.total_collected=%s vs db_count=%s. Syncing state to DB count.", state.get('total_collected', 0), db_count)
                    try:
                        collector.set_collection_state(model_id, version_id, state.get('last_offset', 0), db_count)
                    except Exception as e:
                        logger.warning('[WARN] Failed to set collection_state during sync: %s', e)
            except Exception:
                pass

            new = save_prompts_batch(db, res.get('items', []))
            logger.info('New items saved to DB: %s', new)
            try:
                logger.info('Total prompts in DB now: %s', db.get_total_prompts_count())
            except Exception:
                pass

            # Update collection state only after successful DB save.
            try:
                next_cursor = res.get('next_page_cursor')
                next_offset = res.get('next_offset', 0)
                if new and new > 0:
                    try:
                        collector._update_collection_state(model_id, version_id, new, next_offset, next_page_cursor=next_cursor)
                        logger.info("[State] Updated collection_state: +%s items, next_offset=%s", new, next_offset)
                    except Exception as e:
                        logger.warning('[WARN] Failed to update collection_state: %s', e)
                else:
                    if args.auto_advance_on_empty:
                        try:
                            # advance offset even if nothing new saved (hybrid mode). total_collected not incremented.
                            collector._update_collection_state(model_id, version_id, 0, next_offset, next_page_cursor=next_cursor)
                            logger.info("[State] Auto-advanced collection_state to next_offset=%s (no new items)", next_offset)
                        except Exception as e:
                            logger.warning('[WARN] Failed to auto-advance collection_state: %s', e)
                    else:
                        logger.info('[State] No new items saved; collection_state not advanced')
            except Exception:
                pass
            # Build job summary: attempted, duplicates by version, new_saved
            try:
                # attempted == number of unique items returned by collector
                attempted = res.get('valid', 0)
                new_saved = new
                # duplicates: compare attempted - new_saved, but categorize by model/version from items/raw
                duplicates_total = attempted - new_saved if attempted >= new_saved else 0
                dup_by_version = {}
                for item in res.get('items', []):
                    cid = item.get('civitai_id')
                    # check if exists in DB prior to save: query by civitai_id
                    try:
                        existing = db.get_prompt_by_civitai_id(cid)
                        existed_before = bool(existing and existing.get('id'))
                    except Exception:
                        existed_before = False
                    if existed_before:
                        mid = item.get('model_id') or ''
                        mvid = item.get('model_version_id') or ''
                        key = f"{mid}||{mvid}"
                        dup_by_version[key] = dup_by_version.get(key, 0) + 1

                duplicates_list = []
                for k, v in dup_by_version.items():
                    mid, mvid = k.split('||')
                    duplicates_list.append({"model_id": mid, "version_id": mvid, "count": v})

                summary = {
                    "planned": max_items,
                    "attempted": attempted,
                    "new_saved": new_saved,
                    "duplicates_total": duplicates_total,
                    "duplicates_by_version": duplicates_list,
                    "sample_items": [ { 'civitai_id': it.get('civitai_id'), 'model_id': it.get('model_id'), 'model_version_id': it.get('model_version_id') } for it in res.get('items', [])[:10] ]
                }
                # Write summary and mark job completed
                try:
                    # Set job status first (upsert that does not include summary_json)
                    # then write the summary JSON so it is not accidentally overwritten
                    try:
                        collector.set_job_status(model_id, version_id, 'completed', planned_total=max_items)
                    except Exception:
                        pass
                    collector.write_job_summary(model_id, version_id, summary)
                except Exception as e:
                    logger.warning('[WARN] Failed to write job summary/status: %s', e)
            except Exception as e:
                logger.warning('[WARN] Failed to build/write job summary: %s', e)
        else:
            logger.info('No valid items to save')

        # iteration control: if nothing was collected at all, count as an empty iteration
        if res.get('collected', 0) == 0:
            consecutive_empty += 1
        else:
            consecutive_empty = 0

        # stop conditions for repeat
        if not args.repeat:
            break
        if args.max_iterations and iteration >= args.max_iterations:
            logger.info('[Runner] Reached max iterations: %s', args.max_iterations)
            break
        # if we've had 3 consecutive empty iterations, stop
        if consecutive_empty >= 3:
            logger.info('[Runner] Consecutive empty iterations reached; stopping')
            break

        time_to_sleep = args.repeat_sleep
        if time_to_sleep and time_to_sleep > 0:
            logger.info('[Runner] Sleeping %ss before next iteration...', time_to_sleep)
            time.sleep(time_to_sleep)

    logger.info('\nDone.')

if __name__ == '__main__':
    main()
