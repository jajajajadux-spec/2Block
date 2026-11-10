"""Absolute-path bootstrap: protocol activation has an arbitrary working directory."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.client.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())

