#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_baseline.evaluation import default_output_dir, load_rag_plan
from rag_baseline.retrieval_eval import run_retrieval_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate local RAG retrieval without making answer-model calls.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--offline", action="store_true", help="Require the embedding model to already exist in the local cache")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = load_rag_plan(args.config)
    if args.top_k is not None:
        if args.top_k < 1:
            parser.error("--top-k must be >= 1")
        plan = replace(plan, top_k=args.top_k)
    if args.device:
        plan = replace(plan, device=args.device)
    if args.offline:
        plan = replace(plan, offline=True)
    output = args.output or default_output_dir(f"{plan.name}-retrieval-only")
    summary, report = run_retrieval_eval(
        plan,
        output_dir=output,
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
        limit=args.limit,
    )
    print(f"summary: {summary}")
    print(f"report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
