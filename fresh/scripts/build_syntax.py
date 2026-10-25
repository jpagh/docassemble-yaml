"""Compatibility entry point for the shared TextMate-to-syntect converter.

The implementation and canonical inputs live under ``grammars/``. Keep this
entry point so existing regeneration commands and generated headers stay valid.
"""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "grammars/scripts/build_syntax.py"),
        run_name="__main__",
    )
