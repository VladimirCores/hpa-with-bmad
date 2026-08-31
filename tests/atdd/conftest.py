"""Root conftest for ATDD tests — ensures hpdc_test_client is importable."""
from __future__ import annotations

import sys
from pathlib import Path

_SUPPORT = str(Path(__file__).resolve().parent / "support")
if _SUPPORT not in sys.path:
    sys.path.insert(0, _SUPPORT)
