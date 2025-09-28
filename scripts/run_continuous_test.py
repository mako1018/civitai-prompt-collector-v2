#!/usr/bin/env python3
"""
Quick test runner for ContinuousCivitaiCollector
Run this from PowerShell with: `python .\scripts\run_continuous_test.py`
"""

import sys
from pathlib import Path

# Ensure project root is importable when running from scripts/ via PowerShell
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root.resolve()))

from continuous_collector import ContinuousCivitaiCollector


if __name__ == '__main__':
    c = ContinuousCivitaiCollector()
    print('Instantiated ContinuousCivitaiCollector')
    print('db_path =', c.db_path)
    try:
        summary = c.get_collection_summary()
        print('collection summary entries =', len(summary))
        for s in summary[:10]:
            print(s)
    except Exception as e:
        print('Error when calling get_collection_summary:', e)
        raise
