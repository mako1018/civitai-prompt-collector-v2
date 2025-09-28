#!/usr/bin/env python3
"""
Collect from CivitAI for UI-triggered background jobs.
This script is intended to be launched as a subprocess by the Streamlit UI.
It writes progress to a log file passed via --log-file.
"""
import argparse
import sys
import os
import json
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath('src'))

# DBファイルは必ず data/ ディレクトリで管理
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-id', default=None)
    parser.add_argument('--version-id', default=None)
    parser.add_argument('--model-name', default=None)
    parser.add_argument('--max-items', type=int, default=50)
    parser.add_argument('--save', dest='save', action='store_true')
    parser.add_argument('--no-save', dest='save', action='store_false')
    parser.set_defaults(save=True)
    parser.add_argument('--categorize', dest='categorize', action='store_true')
    parser.add_argument('--no-categorize', dest='categorize', action='store_false')
    parser.set_defaults(categorize=True)
    parser.add_argument('--log-file', required=True)
    parser.add_argument('--strict-version-match', dest='strict_version_match', action='store_true')
    parser.set_defaults(strict_version_match=False)

    args = parser.parse_args()

    # Ensure stdout/stderr are configured to handle UTF-8 on Windows consoles
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    log_path = args.log_file

    try:
        with open(log_path, 'a', encoding='utf-8') as lf:
            try:
                lf.write(f"=== Collection started at {datetime.now().isoformat()} ===\n")
                lf.write(f"Params: model_id={args.model_id}, version_id={args.version_id}, model_name={args.model_name}, max_items={args.max_items}, save={args.save}, categorize={args.categorize}\n")

                # Write DB preview counts so logs explain 0/少数の理由
                try:
                    from database import DatabaseManager
                    db = DatabaseManager()
                    conn = db._get_connection()
                    cur = conn.cursor()
                    vcount = 0
                    rawcount = 0
                    if args.version_id and str(args.version_id).strip():
                        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', (str(args.version_id).strip(),))
                        vcount = cur.fetchone()[0]
                        cur.execute('SELECT COUNT(*) FROM civitai_prompts WHERE raw_metadata LIKE ?', (f"%{str(args.version_id).strip()}%",))
                        rawcount = cur.fetchone()[0]
                    conn.close()
                    lf.write(f"DB preview: model_version_id == {args.version_id} -> {vcount} rows (raw_metadata contains -> {rawcount})\n")
                except Exception:
                    try:
                        lf.write("DB preview: unavailable\n")
                    except Exception:
                        pass

                # Query API totalItems where possible
                try:
                    from collector import check_total_items
                    total = check_total_items(model_id=args.model_id if args.model_id else None, version_id=args.version_id if args.version_id else None)
                    if total is not None:
                        lf.write(f"API preview: totalItems reported -> {total}\n")
                    else:
                        lf.write("API preview: totalItems not reported (cursor-based)\n")
                except Exception:
                    try:
                        lf.write("API preview: failed to query API\n")
                    except Exception:
                        pass

                from collector import CivitaiPromptCollector
                from database import DatabaseManager, save_prompts_batch
                from categorizer import process_database_prompts

                # Try to import the safe, per-page collector (may be in scripts)
                collect_images_safe = None
                try:
                    from scripts.collect_images_safe import collect_images_safe as _cis
                    collect_images_safe = _cis
                except Exception:
                    try:
                        from collect_images_safe import collect_images_safe as _cis2
                        collect_images_safe = _cis2
                    except Exception:
                        collect_images_safe = None

                collector = CivitaiPromptCollector()

                def _clean_id(s):
                    if not s:
                        return None
                    return str(s).strip().rstrip('/')

                selected_id = _clean_id(args.version_id) if args.version_id else _clean_id(args.model_id)

                # Interpret max_items==0 as unlimited (use a large cap)
                if args.max_items is None or args.max_items == 0:
                    max_items = 10_000_000
                else:
                    max_items = args.max_items

                lf.write(f"Collecting... (sanitized model_id={_clean_id(args.model_id)}, version_id={_clean_id(args.version_id)}, max_items={max_items}, strict_version_match={args.strict_version_match})\n")

                if args.version_id and str(args.version_id).isdigit() and collect_images_safe:
                    lf.write('Using collect_images_safe for version-based collection\n')
                    effective_max_items = None if (args.max_items is None or args.max_items == 0) else args.max_items
                    try:
                        page_size = 100
                        if effective_max_items is not None and effective_max_items < page_size:
                            page_size = max(1, int(effective_max_items))
                    except Exception:
                        page_size = 100

                    res = collect_images_safe(model_id=None, version_id=_clean_id(args.version_id), page_size=page_size, max_items=effective_max_items, sleep=1.0, strict_version_match=args.strict_version_match)
                    try:
                        items, saved_count = res
                        lf.write(f"Collected total={len(items)} (items returned)\n")
                        lf.write(f"Saved {saved_count} items to DB\n")
                        saved = saved_count
                    except Exception:
                        items = res
                        lf.write(f"Collected total={len(items)} (items returned)\n")
                        saved = 'handled_by_collect_images_safe'
                else:
                    result = collector.collect_dataset(model_id=selected_id or None, model_name=args.model_name or None, max_items=max_items)
                    lf.write(f"Collected total={result.get('collected',0)}, valid={result.get('valid',0)}\n")

                    saved = 0
                    if args.save and result.get('items'):
                        db = DatabaseManager()
                        saved = save_prompts_batch(db, result['items'])
                        lf.write(f"Saved {saved} items to DB\n")

                if args.categorize:
                    lf.write("Running categorization...\n")
                    process_database_prompts()
                    lf.write("Categorization finished.\n")

                # Build and write a job summary into collection_state so UI-triggered runs
                # are visible to the UI in the same way as run_one_collect.py.
                try:
                    # Determine attempted/sample items
                    def _extract_sample(it):
                        # Try typical fields first
                        cid = None
                        mid = None
                        mvid = None
                        try:
                            if isinstance(it, dict):
                                cid = it.get('civitai_id') or it.get('id') or (it.get('raw_metadata') and (lambda x: (x.get('id') if isinstance(x, dict) else None))(None))
                                mid = it.get('model_id') or it.get('modelId') or None
                                mvid = it.get('model_version_id') or it.get('modelVersionId') or it.get('version') or None
                        except Exception:
                            pass
                        # If still missing, try to parse raw_metadata JSON
                        if not cid and isinstance(it, dict):
                            raw = it.get('raw_metadata') or it.get('raw') or None
                            if raw:
                                try:
                                    import json as _j
                                    r = _j.loads(raw) if isinstance(raw, str) else (r if isinstance(raw, dict) else None)
                                    if isinstance(r, dict):
                                        cid = cid or str(r.get('id') or r.get('civitai_id') or '') or None
                                        mid = mid or str(r.get('modelId') or r.get('model_id') or '') or None
                                        mvid = mvid or str(r.get('modelVersionId') or r.get('model_version_id') or r.get('version') or '') or None
                                except Exception:
                                    pass
                        return {'civitai_id': cid, 'model_id': mid, 'model_version_id': mvid}

                    if 'items' in locals() and items is not None:
                        attempted = len(items)
                        sample_items = [_extract_sample(it) for it in (items[:10] if isinstance(items, list) else [])]
                    elif 'result' in locals() and result is not None:
                        attempted = int(result.get('valid', result.get('collected', 0) or 0))
                        sample_items = [_extract_sample(it) for it in (result.get('items', [])[:10] if isinstance(result.get('items', []), list) else [])]
                    else:
                        attempted = 0
                        sample_items = []

                    new_saved = int(saved) if isinstance(saved, int) else (int(saved) if (isinstance(saved, str) and saved.isdigit()) else 0)
                    duplicates_total = attempted - new_saved if attempted >= new_saved else 0

                    summary = {
                        'planned': None if (args.max_items is None or int(args.max_items) == 0) else int(args.max_items),
                        'attempted': attempted,
                        'new_saved': new_saved,
                        'duplicates_total': duplicates_total,
                        'duplicates_by_version': [],
                        'sample_items': sample_items
                    }

                    # Log the summary for debugging
                    lf.write(f"Job summary: {json.dumps(summary, ensure_ascii=False)}\n")

                    try:
                        # Use ContinuousCivitaiCollector shim to write the job summary into collection_state
                        from continuous_collector import ContinuousCivitaiCollector
                        cc = ContinuousCivitaiCollector()
                        mid = args.model_id or ''
                        vid = args.version_id or ''
                        try:
                            # First set job status (so last_update/time is set), then write summary to avoid
                            # an INSERT OR REPLACE in set_job_status that would clear summary_json.
                            cc.set_job_status(str(mid), str(vid), 'completed', planned_total=summary.get('planned'))
                            cc.write_job_summary(str(mid), str(vid), summary)
                            lf.write('Wrote job summary to collection_state\n')
                        except Exception as _e:
                            lf.write(f'Failed to write job summary/status: {_e}\n')
                    except Exception as _e2:
                        lf.write(f'Failed to import continuous_collector to write summary: {_e2}\n')
                except Exception as _e3:
                    try:
                        lf.write(f'Error while preparing job summary: {_e3}\n')
                    except Exception:
                        pass

                lf.write(f"=== Collection finished at {datetime.now().isoformat()} ===\n")
            except Exception as e:
                try:
                    lf.write(f"Error during collection: {repr(e)}\n")
                except Exception:
                    try:
                        lf.write("Error during collection: (unable to render exception)\n")
                    except Exception:
                        pass
                try:
                    lf.write(f"=== Collection aborted at {datetime.now().isoformat()} ===\n")
                except Exception:
                    pass
    except Exception as e:
        try:
            sys.stderr.write(f"Failed to write log {log_path}: {repr(e)}\n")
        except Exception:
            pass


if __name__ == '__main__':
    main()
