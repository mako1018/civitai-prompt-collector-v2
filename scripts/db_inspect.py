#!/usr/bin/env python3
"""
Lightweight DB inspection helper for Windows PowerShell / venv usage.

Usage (PowerShell, from project root):
  & .\.venv\Scripts\python.exe scripts\db_inspect.py

This prints the list of tables, columns for each table, and row counts for main tables.
"""
import sqlite3
from pathlib import Path
import sys

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'civitai_dataset.db'

def main():
    if not DB_PATH.exists():
        print('DB not found:', DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print('DB:', DB_PATH)
    print('\nTables:')
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        print('-', t)

    for t in tables:
        print('\n==', t, '==')
        try:
            cur.execute(f"PRAGMA table_info('{t}')")
            cols = cur.fetchall()
            if not cols:
                print('  (no columns returned)')
            for c in cols:
                cid, name, ctype, notnull, dflt_value, pk = c
                print(f'  - {name} ({ctype}), notnull={bool(notnull)}, pk={pk}, default={dflt_value}')
        except Exception as e:
            print('  PRAGMA failed:', e)

        # print simple row count for known tables
        try:
            cur.execute(f"SELECT COUNT(*) FROM '{t}'")
            cnt = cur.fetchone()[0]
            print(f'  rows: {cnt}')
        except Exception:
            pass

    conn.close()

if __name__ == '__main__':
    main()
