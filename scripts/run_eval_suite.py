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
from evals.benchmark import load_eval_dataset, load_plan, resolve_case_filters, run_benchmark, select_cases
from progressive_disclosure.config import load_project_env


def _load_suite(path: Path) -> tuple[str, list[Path]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("suite root must be a mapping")
    name = data.get("name") or path.stem
    configs = data.get("configs")
    if not isinstance(configs, list) or not configs or not all(isinstance(x, str) and x for x in configs):
        raise ValueError("suite configs must be a non-empty list of paths")
    return str(name), [Path(x) for x in configs]


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run multiple progressive-disclosure experiment configs as one suite.")
    parser.add_argument("--suite", default="experiments/suites/verify-all-v14.yaml")
    parser.add_argument("--runs", type=int, help="Override runs per case in every suite config")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.runs is not None and args.runs < 1:
        parser.error("--runs must be >= 1")

    suite_name, config_paths = _load_suite(Path(args.suite))
    plans = [load_plan(path) for path in config_paths]
    if args.runs is not None:
        plans = [replace(plan, runs_per_case=args.runs) for plan in plans]

    total_trials = 0
    rows: list[tuple[str, str, str, int, int, int]] = []
    for config_path, plan in zip(config_paths, plans):
        dataset = load_eval_dataset(plan.dataset)
        ids, tags = resolve_case_filters(plan)
        selected = select_cases(dataset["cases"], case_ids=ids, tags=tags)
        trials = len(selected) * len(plan.models) * len(plan.prompts) * plan.runs_per_case
        total_trials += trials
        rows.append((str(config_path), plan.corpus_name, dataset["name"], len(selected), trials, plan.max_selection_rounds))

    if args.dry_run:
        print(f"suite: {suite_name}")
        nominal_max = sum(trials * (2 * selection_rounds) for _, _, _, _, trials, selection_rounds in rows)
        for config, corpus, dataset, cases, trials, selection_rounds in rows:
            print(
                f"  - {config}: corpus={corpus} dataset={dataset} cases={cases} "
                f"case_trials={trials} max_selection_rounds={selection_rounds}"
            )
        print(f"case trials: {total_trials}")
        print(f"model calls (nominal): {total_trials * 2} minimum, {nominal_max} maximum")
        return 0

    if args.output:
        output_root = args.output
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output_root = Path("results") / f"{stamp}-{suite_name}"
    output_root.mkdir(parents=True, exist_ok=True)

    trial_files: list[Path] = []
    for config_path, plan in zip(config_paths, plans):
        if not args.quiet:
            print(f"running {config_path} [{plan.corpus_name}]")
        trial_files.append(
            run_benchmark(
                plan,
                output_dir=output_root / plan.name,
                quiet=args.quiet,
            )
        )

    records = load_records(trial_files)
    summary_path, report_path = write_aggregate(records, output_root)
    print(f"suite results: {output_root}")
    print(f"summary: {summary_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
