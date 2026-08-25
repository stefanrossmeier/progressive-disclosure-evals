#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from qwen_rag_pipeline.evaluation import default_output_dir, load_plan
from qwen_rag_pipeline.retrieval_eval import run_retrieval_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fully local Qwen hierarchical-RAG retrieval eval.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = load_plan(args.config)
    if args.top_k is not None:
        if args.top_k < 1:
            parser.error("--top-k must be >= 1")
        if plan.unique_document_slots > args.top_k:
            parser.error("--top-k cannot be smaller than configured unique_document_slots")
        plan = replace(plan, top_k=args.top_k)
    if args.device:
        plan = replace(plan, device=args.device)
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
