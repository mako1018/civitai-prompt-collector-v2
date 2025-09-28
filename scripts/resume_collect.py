#!/usr/bin/env python3
"""
Resume collection using scripts/last_resume.json. This runner reads the saved resume point and
invokes collect_images_safe.collect_images_safe with the matching version_id and page_size.

Usage:
  & .\.venv\Scripts\python.exe scripts\resume_collect.py

This script performs no long-running backups; make sure you've backed up DB beforehand.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.collect_images_safe import collect_images_safe


def main():
    resume_file = Path(__file__).resolve().parent / 'last_resume.json'
    if not resume_file.exists():
        print('No last_resume.json found at', resume_file)
        sys.exit(1)

    data = json.loads(resume_file.read_text(encoding='utf-8'))
    version_id = data.get('version_id')
    if not version_id:
        print('resume file missing version_id')
        sys.exit(1)

    page_size = 100
    sleep = 1.5

    print(f"Resuming collection for version_id={version_id} page_size={page_size} sleep={sleep}")
    collected = collect_images_safe(model_id=None, version_id=version_id, page_size=page_size, max_items=None, sleep=sleep)
    print('Resume run finished. Collected count:', len(collected))


if __name__ == '__main__':
    main()
