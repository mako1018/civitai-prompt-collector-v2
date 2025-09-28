"""Shim module: load the implementation from scripts/continuous_collector.py

Historically the repository had the implementation under `scripts/continuous_collector.py` but
some workflows import `continuous_collector` from the project root. The root file was empty which
caused imports to yield an empty module. This shim dynamically loads the real implementation
from the `scripts` folder into this module namespace so `from continuous_collector import ...`
keeps working.
"""

from importlib import util
from pathlib import Path
import sys

_impl_path = Path(__file__).resolve().parent / 'scripts' / 'continuous_collector.py'
if not _impl_path.exists():
    raise ImportError(f"Implementation not found at {_impl_path}")

spec = util.spec_from_file_location('continuous_collector_impl', str(_impl_path))
_mod = util.module_from_spec(spec)
# Execute the module in its own namespace
spec.loader.exec_module(_mod)

# Re-export public symbols into this module's globals
for _name in dir(_mod):
    if _name.startswith('_'):
        continue
    globals()[_name] = getattr(_mod, _name)

# Also keep a reference to the underlying module
__impl_module__ = _mod
