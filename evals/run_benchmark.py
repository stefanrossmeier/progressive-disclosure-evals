from __future__ import annotations

import argparse
from pathlib import Path

from evals.aggregate import aggregate, load_records, write_aggregate
from evals.benchmark import (
    BenchmarkPlan,
    default_output_dir,
    load_eval_dataset,
    load_plan,
    resolve_case_filters,
    run_benchmark,
    select_cases,
)
from progressive_disclosure.config import load_project_env
from progressive_disclosure.prompts import load_prompt_artifact


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run the progressive-disclosure held-out benchmark.")
    parser.add_argument("--config", default="experiments/eval-v1.yaml")
    parser.add_argument("--runs", type=int, help="Override runs per case")
    parser.add_argument("--model", action="append", help="Override/add model; repeat for multiple models")
    parser.add_argument("--prompt", action="append", help="Override/add prompt artifact; repeat for multiple prompts")
    parser.add_argument("--max-documents", type=int, help="Override document-read budget")
    parser.add_argument("--case", action="append", help="Run only case ID; repeatable")
    parser.add_argument("--tag", action="append", help="Require tag; repeatable (AND semantics)")
    parser.add_argument("--limit", type=int, help="Limit selected cases (smoke testing only)")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds between case trials")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved trial count without calling a model")
    args = parser.parse_args()
    if args.runs is not None and args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.max_documents is not None and args.max_documents < 1:
        parser.error("--max-documents must be >= 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    if args.sleep < 0:
        parser.error("--sleep must be >= 0")

    plan = load_plan(args.config)
    plan = BenchmarkPlan(
        name=plan.name,
        dataset=plan.dataset,
        corpus_name=plan.corpus_name,
        corpus_root=plan.corpus_root,
        runs_per_case=args.runs if args.runs is not None else plan.runs_per_case,
        max_documents=(
            args.max_documents if args.max_documents is not None else plan.max_documents
        ),
        max_selection_rounds=plan.max_selection_rounds,
        prompts=tuple(Path(x) for x in args.prompt) if args.prompt else plan.prompts,
        models=tuple(args.model) if args.model else plan.models,
        case_ids=plan.case_ids,
        case_tags=plan.case_tags,
    )
    dataset = load_eval_dataset(plan.dataset)
    effective_case_ids, effective_tags = resolve_case_filters(
        plan,
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
    )
    selected = select_cases(
        dataset["cases"],
        case_ids=effective_case_ids,
        tags=effective_tags,
        limit=args.limit,
    )
    if not selected:
        parser.error("case selection is empty")
    trial_count = len(plan.models) * len(plan.prompts) * plan.runs_per_case * len(selected)
    if args.dry_run:
        print(f"experiment: {plan.name}")
        print(f"dataset: {dataset['name']} v{dataset['version']}")
        print(f"corpus: {plan.corpus_name} ({plan.corpus_root})")
        print(f"cases: {len(selected)}")
        print(f"models: {len(plan.models)} ({', '.join(plan.models)})")
        print(f"prompts: {len(plan.prompts)}")
        for prompt_path in plan.prompts:
            artifact = load_prompt_artifact(prompt_path)
            print(f"  - {artifact.id}@v{artifact.version}: {prompt_path}")
        print(f"runs per case: {plan.runs_per_case}")
        print(f"max selection rounds: {plan.max_selection_rounds}")
        if plan.case_tags:
            print(f"config case tags: {', '.join(plan.case_tags)}")
        if plan.case_ids:
            print(f"config case ids: {', '.join(plan.case_ids)}")
        print(f"case trials: {trial_count}")
        nominal_max = trial_count * (2 * plan.max_selection_rounds)
        print(f"model calls (nominal): {trial_count * 2} minimum, {nominal_max} maximum")
        print(f"model calls (including one protocol retry per stage): up to {nominal_max * 2}")
        return 0

    output_dir = args.output or default_output_dir(plan.name)
    trials = run_benchmark(
        plan,
        output_dir=output_dir,
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
        limit=args.limit,
        fail_fast=args.fail_fast,
        sleep_seconds=args.sleep,
        quiet=args.quiet,
    )
    records = load_records([trials])
    summary = aggregate(records)["overall"]
    summary_path, report_path = write_aggregate(records, output_dir)
    def pct(value):
        return "n/a" if value is None else f"{100 * value:.1f}%"

    mean_docs = summary["mean_document_reads"]
    mean_docs_text = "n/a" if mean_docs is None else f"{mean_docs:.2f}"
    print(
        "aggregate: "
        f"completed={summary['completed']}/{summary['trials']} "
        f"task_success={pct(summary['overall_success_rate'])} "
        f"discovery={pct(summary['discovery_success_rate'])} "
        f"first_read={pct(summary['first_read_hit_rate'])} "
        f"stop_after_evidence={pct(summary['evidence_stopping_rate'])} "
        f"mean_docs={mean_docs_text}"
    )
    print(f"trials: {trials}")
    print(f"summary: {summary_path}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
