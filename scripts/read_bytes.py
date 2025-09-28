from pathlib import Path
p=Path(__file__).resolve().parents[1]/'continuous_collector.py'
b=p.read_bytes()
print('path=', p)
print('size=', len(b))
print(repr(b[:800]))
