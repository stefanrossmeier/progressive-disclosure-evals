#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evals.aggregate import load_records, write_aggregate
from progressive_disclosure.config import load_project_env
from qwen_rag_pipeline.evaluation import load_plan, run_benchmark


def _load_suite(path: Path) -> tuple[str, list[Path]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Qwen RAG suite root must be a mapping")
    configs = data.get("configs")
    if not isinstance(configs, list) or not configs or not all(isinstance(item, str) and item for item in configs):
        raise ValueError("Qwen RAG suite configs must be a non-empty list")
    return str(data.get("name") or path.stem), [Path(value) for value in configs]


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run the Qwen hierarchical-hybrid RAG suite.")
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    name, config_paths = _load_suite(args.suite)
    plans = [load_plan(path) for path in config_paths]
    if args.runs is not None:
        if args.runs < 1:
            parser.error("--runs must be >= 1")
        plans = [replace(plan, runs_per_case=args.runs) for plan in plans]
    if args.device:
        plans = [replace(plan, device=args.device) for plan in plans]

    if args.dry_run:
        print(f"suite: {name}")
        for path, plan in zip(config_paths, plans):
            print(
                f"  - {path}: corpus={plan.corpus_name} dataset={plan.dataset} top_k={plan.top_k} "
                f"doc_candidates={plan.document_candidates} unique_docs={plan.unique_document_slots} "
                f"runs={plan.runs_per_case}"
            )
        return 0

    if args.output:
        root = args.output
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        root = Path("results") / f"{stamp}-{name}"
    root.mkdir(parents=True, exist_ok=True)

    trial_files: list[Path] = []
    for path, plan in zip(config_paths, plans):
        if not args.quiet:
            print(f"running {path} [qwen-rag / {plan.corpus_name}]")
        trial_files.append(run_benchmark(plan, output_dir=root / plan.name, quiet=args.quiet))

    records = load_records(trial_files)
    summary_path, report_path = write_aggregate(records, root)
    completed = [record for record in records if record.get("status") == "completed"]
    comparable = [bool(record.get("result", {}).get("comparable_success")) for record in completed]
    coverage = [bool(record.get("result", {}).get("answer_evidence_coverage")) for record in completed]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["qwen_rag"] = {
        "comparable_success_rate": sum(comparable) / len(comparable) if comparable else None,
        "answer_evidence_coverage_rate": sum(coverage) / len(coverage) if coverage else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n## Qwen RAG comparison metrics\n\n")
        if comparable:
            handle.write(f"- Answer + complete discovery: **{100 * sum(comparable) / len(comparable):.1f}%**\n")
        if coverage:
            handle.write(f"- Retrieved-context answer-evidence coverage: **{100 * sum(coverage) / len(coverage):.1f}%**\n")
    print(f"suite results: {root}")
    print(f"summary: {summary_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
