"""
Safe image collector for CivitAI (adopted policy implementation)
- Prefer metadata.totalItems when present
- Otherwise follow nextPage / nextCursor until exhausted
- Deduplicate by civitai_id, skip empty prompts
- Respect rate limits with sleep and retries
"""
import time
import math
import requests
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import sys
import os

# Allow running this script directly from scripts/ by adding project root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Database and collector integration
from src.database import create_database, save_prompts_batch
from continuous_collector import ContinuousCivitaiCollector

DEFAULT_LIMIT = 100
DEFAULT_SLEEP = 1.0
MAX_RETRIES = 3


def collect_images_safe(model_id: Optional[str] = None,
                        version_id: Optional[str] = None,
                        page_size: int = DEFAULT_LIMIT,
                        max_items: Optional[int] = None,
                        sleep: float = DEFAULT_SLEEP,
                        strict_version_match: bool = False) -> Tuple[List[Dict], int]:
    if not (model_id or version_id):
        raise ValueError("model_id または version_id を指定してください")

    base = "https://civitai.com/api/v1/images"
    params = {"limit": 1}
    if version_id:
        params["modelVersionId"] = version_id
    else:
        params["modelId"] = model_id

    # 1) Probe metadata (limit=1)
    try:
        probe = requests.get(base, params=params, timeout=30)
        probe.raise_for_status()
        meta = probe.json().get("metadata", {})
    except Exception:
        meta = {}

    total_items = meta.get("totalItems") or meta.get("total")
    try:
        if total_items:
            print(f"[Info] API reported approximate totalItems={total_items}")
        else:
            print("[Info] API did not report totalItems — will use cursor-based scan")
    except Exception as e:
        # Avoid crashing when console encoding cannot represent characters (Windows cp932)
        try:
            print(repr(e))
        except Exception:
            pass

    # Prepare DB and state objects
    db_manager = create_database()
    collector = ContinuousCivitaiCollector()

    # 2) iterate pages
    collected: List[Dict] = []
    seen_ids = set()
    next_page_url = None
    next_cursor = meta.get("nextCursor") or None
    use_cursor_param = False
    # track processed items (for offset updates)
    total_processed = 0
    # track total newly inserted into DB across all batches in this run
    total_new_saved = 0

    # Start loop
    while True:
        # Respect max_items if set
        if max_items and len(collected) >= max_items:
            break

        # Build request
        params_page = {"limit": page_size}
        if version_id:
            params_page["modelVersionId"] = version_id
        else:
            params_page["modelId"] = model_id

        if next_page_url:
            # full URL returned by API (prefer)
            req_url = next_page_url
            req_params = None
        else:
            req_url = base
            # If we have a cursor and not a full URL, send as 'cursor' param
            if next_cursor:
                params_page["cursor"] = next_cursor
                use_cursor_param = True
            req_params = params_page

        # request with retries
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if req_params is not None:
                    resp = requests.get(req_url, params=req_params, timeout=60)
                else:
                    resp = requests.get(req_url, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.exceptions.RequestException as e:
                if attempt == MAX_RETRIES:
                    raise
                backoff = 1.5 ** attempt
                try:
                    print(f"[Warn] Request failed (attempt {attempt}), retrying in {backoff:.1f}s: {e}")
                except Exception:
                    try:
                        print(repr(e))
                    except Exception:
                        pass
                time.sleep(backoff)
        items = data.get("items") or []
        meta = data.get("metadata") or {}

        # Check stop flag created by UI
        try:
            stop_flag = Path(__file__).resolve().parent / 'collect_stop.flag'
            if stop_flag.exists():
                print('[Info] Stop flag detected — stopping collection gracefully')
                try:
                    stop_flag.unlink()
                except Exception:
                    pass
                break
        except Exception:
            pass

        # Prefer metadata.nextPage (full URL) if present
        next_page_url = meta.get("nextPage")
        next_cursor = meta.get("nextCursor") if not next_page_url else None

        # Process items: dedupe by civitai_id and skip empty prompts
        prompts_to_save: List[Dict] = []
        new_in_batch = 0
        for it in items:
            cid = str(it.get("id") or it.get("civitai_id") or "")
            prompt_text = (it.get("meta") or {}).get("prompt") or ""
            # skip empty or missing
            if not cid or not prompt_text:
                total_processed += 1
                continue
            # dedupe across pages in this run
            if cid in seen_ids:
                total_processed += 1
                continue

            seen_ids.add(cid)

            # extract prompt data using existing collector helper to match DB schema
            prompt_data = collector._extract_prompt_data(it, model_name="", model_id=(model_id or ""))
            # If this collector was invoked with a version_id, make sure we record it on the extracted prompt_data
            try:
                if prompt_data is not None and version_id:
                    prompt_data['model_version_id'] = str(version_id)
            except Exception:
                pass
            if not prompt_data:
                total_processed += 1
                continue

            prompts_to_save.append(prompt_data)
            collected.append(it)
            new_in_batch += 1
            total_processed += 1
            if max_items and len(collected) >= max_items:
                break

        # Persist page to DB and update collection_state
        try:
            new_saved = 0
            if prompts_to_save:
                new_saved = save_prompts_batch(db_manager, prompts_to_save)
                # detailed logging: attempted vs newly inserted vs duplicates
                attempted = len(prompts_to_save)
                duplicates = attempted - new_saved
                try:
                    print(f"[DB] Batch result: attempted={attempted} new_saved={new_saved} duplicates={duplicates}")
                except Exception:
                    try:
                        print(f"[DB] Batch result: attempted={attempted} new_saved={new_saved} duplicates={duplicates}".encode('utf-8', errors='replace'))
                    except Exception:
                        pass
                # show a short sample of civitai_ids for context
                try:
                    sample_ids = [p.get('civitai_id') for p in prompts_to_save[:5]]
                    print(f"[DB] sample civitai_ids: {sample_ids}")
                except Exception:
                    pass
                # accumulate into total
                total_new_saved += new_saved
        except Exception as e:
            print(f"[DB] Failed to save batch: {e}")
            new_saved = 0

        # Update collection_state: increment total_collected by new_saved and advance offset by items processed
        try:
            prev_state = collector._get_collection_state(model_id or "", version_id or "")
            prev_offset = prev_state.get("last_offset", 0) if isinstance(prev_state, dict) else 0
            new_offset = prev_offset + len(items)
            # prefer nextPage URL for persistence, otherwise nextCursor
            cursor_to_store = meta.get("nextPage") or meta.get("nextCursor")
            collector._update_collection_state(model_id or "", version_id or "", new_items=new_saved, new_offset=new_offset, next_page_cursor=cursor_to_store)
        except Exception as e:
            print(f"[State] Failed to update collection_state: {e}")

        try:
            print(f"[Page] fetched={len(items)} new_unique={new_in_batch} new_saved={new_saved} total_unique={len(collected)}")
        except Exception:
            try:
                print(repr((len(items), new_in_batch, new_saved, len(collected))))
            except Exception:
                pass

        # Termination conditions
        if total_items and len(collected) >= int(total_items):
            # If API reported totalItems, we can stop when reached or exceeded
            print("[Info] Reached reported totalItems — stopping")
            break
        if not total_items and not next_page_url and not next_cursor:
            print("[Info] Cursor/page exhausted — stopping")
            break

        # Sleep to avoid rate limits
        time.sleep(sleep)

    try:
        print(f"[Done] Collected unique prompts: {len(collected)} saved={total_new_saved}")
    except Exception:
        try:
            print(repr((len(collected), total_new_saved)))
        except Exception:
            pass
    return collected, total_new_saved


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-id')
    parser.add_argument('--version-id')
    parser.add_argument('--page-size', type=int, default=DEFAULT_LIMIT)
    parser.add_argument('--max-items', type=int)
    parser.add_argument('--sleep', type=float, default=DEFAULT_SLEEP)
    args = parser.parse_args()

    res = collect_images_safe(model_id=args.model_id, version_id=args.version_id,
                              page_size=args.page_size, max_items=args.max_items, sleep=args.sleep)
    try:
        items, saved = res
        print('Result count:', len(items), 'saved=', saved)
    except Exception:
        print('Result (legacy):', res)
