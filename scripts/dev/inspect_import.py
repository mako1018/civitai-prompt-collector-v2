from pathlib import Path
import sys
import importlib, inspect
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
print('sys.path[0]=', sys.path[0])
try:
    m = importlib.import_module('continuous_collector')
    print('module file:', getattr(m, '__file__', None))
    print('has ContinuousCivitaiCollector:', hasattr(m, 'ContinuousCivitaiCollector'))
    print('dict keys sample:', list(m.__dict__.keys())[:50])
    try:
        src = inspect.getsource(m)
        print('\n--- module source head (first 200 lines) ---')
        for i, line in enumerate(src.splitlines()[:200], 1):
            print(f'{i:03d}: {line}')
    except Exception as e:
        print('Could not get source:', e)
except Exception as e:
    import traceback; traceback.print_exc()
