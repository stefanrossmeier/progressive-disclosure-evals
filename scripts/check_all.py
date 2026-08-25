#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def run(*args: str) -> None:
    result = subprocess.run([sys.executable, *args], check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    run("-m", "pytest")
    run("scripts/validate_corpus.py", "--all")
    run("scripts/validate_dataset.py", "--all")
    run("scripts/validate_dataset.py", "--dataset", "datasets/multi-dev-v2.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
