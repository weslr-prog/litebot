"""Deprecated fast exit manager module.

This logic has been archived under `archive/risk_management/fast_exit_manager.py`
so it is no longer imported or executed by the runtime. Any feature work should
reference the short-cycle exit managers instead.
"""

from __future__ import annotations

from pathlib import Path

ARCHIVE_PATH = Path(__file__).resolve().parents[1] / "archive" / "risk_management" / "fast_exit_manager.py"

raise RuntimeError(
    "fast_exit_manager has been retired. See the archived copy at "
    f"{ARCHIVE_PATH}. If you still need accelerated exits, integrate with "
    "the current ShortCycle exit flow instead."
)
