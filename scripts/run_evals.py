#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


# Direct execution via `python scripts/run_evals.py` puts `scripts/` on
# sys.path, not the repository root. Expose the repository packages explicitly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evals.run_benchmark import main

if __name__ == "__main__":
    raise SystemExit(main())
