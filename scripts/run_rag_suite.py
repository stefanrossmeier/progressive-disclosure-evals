#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from rag_baseline.evaluation import load_rag_plan, run_rag_benchmark


def _load_suite(path: Path) -> tuple[str, list[Path]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("RAG suite root must be a mapping")
    configs = data.get("configs")
    if not isinstance(configs, list) or not configs or not all(isinstance(x, str) and x for x in configs):
        raise ValueError("RAG suite configs must be a non-empty list")
    return str(data.get("name") or path.stem), [Path(value) for value in configs]


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run multiple local-RAG configs as one comparison suite.")
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--offline", action="store_true", help="Require the embedding model to already exist in the local cache")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    name, config_paths = _load_suite(args.suite)
    plans = [load_rag_plan(path) for path in config_paths]
    if args.runs is not None:
        if args.runs < 1:
            parser.error("--runs must be >= 1")
        plans = [replace(plan, runs_per_case=args.runs) for plan in plans]
    if args.device:
        plans = [replace(plan, device=args.device) for plan in plans]
    if args.offline:
        plans = [replace(plan, offline=True) for plan in plans]

    if args.dry_run:
        print(f"suite: {name}")
        for path, plan in zip(config_paths, plans):
            print(
                f"  - {path}: rag-{plan.strategy} corpus={plan.corpus_name} "
                f"dataset={plan.dataset} top_k={plan.top_k} runs={plan.runs_per_case}"
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
            print(f"running {path} [rag-{plan.strategy} / {plan.corpus_name}]")
        trial_files.append(
            run_rag_benchmark(
                plan,
                output_dir=root / plan.name,
                quiet=args.quiet,
            )
        )
    records = load_records(trial_files)
    summary, report = write_aggregate(records, root)
    print(f"suite results: {root}")
    print(f"summary: {summary}")
    print(f"report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
