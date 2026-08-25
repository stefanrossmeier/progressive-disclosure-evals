#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.config import load_project_env
from rag_baseline.evaluation import (
    default_output_dir,
    load_rag_plan,
    run_rag_benchmark,
    write_rag_aggregate,
)


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run dense or hybrid local-RAG end-to-end evals.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--offline", action="store_true", help="Require the embedding model to already exist in the local cache")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    plan = load_rag_plan(args.config)
    if args.runs is not None:
        if args.runs < 1:
            parser.error("--runs must be >= 1")
        plan = replace(plan, runs_per_case=args.runs)
    if args.top_k is not None:
        if args.top_k < 1:
            parser.error("--top-k must be >= 1")
        plan = replace(plan, top_k=args.top_k)
    if args.device:
        plan = replace(plan, device=args.device)
    if args.offline:
        plan = replace(plan, offline=True)

    if args.dry_run:
        print(f"experiment: {plan.name}")
        print(f"retrieval: rag-{plan.strategy}")
        print(f"dataset: {plan.dataset}")
        print(f"corpus: {plan.corpus_name} ({plan.corpus_root})")
        print(f"index: {plan.index_dir}")
        print(f"top-k chunks: {plan.top_k}")
        print(f"max chunks/document: {plan.max_chunks_per_document}")
        print(f"runs/case: {plan.runs_per_case}")
        print(f"answer model: {plan.model}")
        return 0

    output = args.output or default_output_dir(plan.name)
    trials = run_rag_benchmark(
        plan,
        output_dir=output,
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
        limit=args.limit,
        quiet=args.quiet,
    )
    summary_path, report_path, summary = write_rag_aggregate(trials, output)
    overall = summary["overall"]
    pct = lambda value: "n/a" if value is None else f"{100 * value:.1f}%"
    print(
        "aggregate: "
        f"completed={overall['completed']}/{overall['trials']} "
        f"task_success={pct(overall['overall_success_rate'])} "
        f"discovery={pct(overall['discovery_success_rate'])} "
        f"answer={pct(overall['answer_accuracy'])} "
        f"mean_docs={overall['mean_document_reads']:.2f}"
    )
    print(f"trials: {trials}")
    print(f"summary: {summary_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
