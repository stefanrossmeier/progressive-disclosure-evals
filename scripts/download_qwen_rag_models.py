#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from qwen_rag_pipeline.model_assets import DEFAULT_MODEL_ROOT, MODEL_ASSETS, download_assets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the version-pinned Qwen embedding and reranker models into a local directory."
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_workers < 1:
        parser.error("--max-workers must be >= 1")

    if args.dry_run:
        print(f"model root: {args.model_root}")
        for asset in MODEL_ASSETS:
            print(f"{asset.role}: {asset.repo_id}@{asset.revision} -> {asset.local_path(args.model_root)}")
        return 0

    manifest = download_assets(
        model_root=args.model_root,
        token=os.getenv("HF_TOKEN"),
        max_workers=args.max_workers,
    )
    print(f"downloaded Qwen RAG models; manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
