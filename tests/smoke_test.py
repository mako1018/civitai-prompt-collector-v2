import sys
from src.config import DEFAULT_DB_PATH
from src.database import DatabaseManager

print('Python executable:', sys.executable)
print('DEFAULT_DB_PATH:', DEFAULT_DB_PATH)

try:
    db = DatabaseManager()
    conn = db._get_connection()
    print('DB connection OK:', conn is not None)
    count = db.get_prompt_count()
    print('Prompt count:', count)
    conn.close()
    print('Smoke test passed')
except Exception as e:
    print('Smoke test failed:', e)
    raise
