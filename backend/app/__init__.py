import sys
from pathlib import Path

_vendor = Path(__file__).resolve().parent.parent / "vendor"
if _vendor.is_dir() and str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))
