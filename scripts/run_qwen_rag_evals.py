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
from qwen_rag_pipeline.evaluation import default_output_dir, load_plan, run_benchmark, write_aggregate_report


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run Qwen hierarchical-hybrid RAG end-to-end evals.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    plan = load_plan(args.config)
    if args.runs is not None:
        if args.runs < 1:
            parser.error("--runs must be >= 1")
        plan = replace(plan, runs_per_case=args.runs)
    if args.device:
        plan = replace(plan, device=args.device)

    if args.dry_run:
        print(f"experiment: {plan.name}")
        print("retrieval: qwen-hierarchical-hybrid")
        print(f"dataset: {plan.dataset}")
        print(f"corpus: {plan.corpus_name} ({plan.corpus_root})")
        print(f"index: {plan.index_dir}")
        print(f"model root: {plan.model_root}")
        print(f"top-k chunks: {plan.top_k}")
        print(f"document candidates: {plan.document_candidates}")
        print(f"chunk candidates/document: {plan.chunk_candidates_per_document}")
        print(f"unique document slots: {plan.unique_document_slots}")
        print(f"runs/case: {plan.runs_per_case}")
        print(f"answer model: {plan.model}")
        return 0

    output = args.output or default_output_dir(plan.name)
    trials = run_benchmark(
        plan,
        output_dir=output,
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
        limit=args.limit,
        quiet=args.quiet,
    )
    summary_path, report_path, summary = write_aggregate_report(trials, output)
    overall = summary["overall"]
    qwen = summary.get("qwen_rag", {})
    pct = lambda value: "n/a" if value is None else f"{100 * value:.1f}%"
    print(
        "aggregate: "
        f"completed={overall['completed']}/{overall['trials']} "
        f"citation_strict={pct(overall['overall_success_rate'])} "
        f"answer={pct(overall['answer_accuracy'])} "
        f"discovery={pct(overall['discovery_success_rate'])} "
        f"answer+discovery={pct(qwen.get('comparable_success_rate'))}"
    )
    print(f"trials: {trials}")
    print(f"summary: {summary_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
