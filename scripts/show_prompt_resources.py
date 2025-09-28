#!/usr/bin/env python3
"""Show resources for a given civitai_id or list recent entries"""
import sys
from src.database import DatabaseManager
from src.database import create_database

DB = create_database()

def show_by_civitai_id(cid: str):
    row = DB.get_prompt_by_civitai_id(cid)
    if not row:
        print(f"No prompt with civitai_id={cid}")
        return
    pid = row['id']
    print(f"Prompt id={pid} civitai_id={cid} model_version_id={row.get('model_version_id')}")
    res = DB.get_prompt_resources(pid)
    if not res:
        print("  (no resources)")
        return
    for r in res:
        print(f"  - idx={r['index']} type={r['type']} name={r['name']} modelId={r['modelId']} modelVersionId={r['modelVersionId']} resourceId={r['resourceId']}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        show_by_civitai_id(sys.argv[1])
    else:
        print("Usage: show_prompt_resources.py <civitai_id>")
