#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evals.benchmark import load_eval_dataset, select_cases
from evals.diagnostics import evaluate_oracle_answer, evaluate_selection_only
from progressive_disclosure.config import (
    get_openai_model,
    get_openai_reasoning_effort,
    get_openai_text_verbosity,
    load_project_env,
)
from progressive_disclosure.llm import OpenAIResponsesBackend
from progressive_disclosure.prompts import load_prompt_artifact


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(
        description="Run one-call diagnostic baselines for metadata selection or oracle answering."
    )
    parser.add_argument("--mode", choices=("selection", "oracle"), required=True)
    parser.add_argument("--dataset", default="datasets/eval-v1.yaml")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model")
    parser.add_argument("--prompt", default="prompts/agent/system-v14.md")
    parser.add_argument("--max-documents", type=int, default=4)
    parser.add_argument("--case", action="append")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.max_documents < 1:
        parser.error("--max-documents must be >= 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")

    dataset = load_eval_dataset(args.dataset)
    cases = select_cases(
        dataset["cases"],
        case_ids=set(args.case) if args.case else None,
        tags=set(args.tag) if args.tag else None,
        limit=args.limit,
    )
    if not cases:
        parser.error("case selection is empty")
    model = args.model or get_openai_model()
    if not model:
        parser.error("model is not set; use --model or OPENAI_MODEL")
    prompt = load_prompt_artifact(args.prompt)
    call_count = len(cases) * args.runs

    if args.dry_run:
        print(f"mode: {args.mode}")
        print(f"dataset: {dataset['name']} v{dataset['version']}")
        print(f"cases: {len(cases)}")
        print(f"model: {model}")
        print(f"prompt: {prompt.id}@v{prompt.version}")
        print(f"runs per case: {args.runs}")
        print(f"model calls: {call_count}")
        return 0

    backend = OpenAIResponsesBackend(
        model,
        reasoning_effort=get_openai_reasoning_effort(),
        text_verbosity=get_openai_text_verbosity(),
    )
    if args.output:
        output = args.output
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = Path("results") / f"{stamp}-{args.mode}-diagnostic"
    output.mkdir(parents=True, exist_ok=True)
    trials = output / "trials.jsonl"
    if trials.exists() and trials.stat().st_size:
        raise FileExistsError(f"refusing to append to {trials}")

    manifest = {
        "schema_version": 1,
        "mode": args.mode,
        "dataset": args.dataset,
        "dataset_name": dataset["name"],
        "dataset_version": dataset["version"],
        "model": model,
        "prompt": args.prompt,
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "prompt_sha256": hashlib.sha256(Path(args.prompt).read_bytes()).hexdigest(),
        "runs_per_case": args.runs,
        "selected_cases": [c["id"] for c in cases],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    records = []
    with trials.open("w", encoding="utf-8") as handle:
        for repeat in range(1, args.runs + 1):
            for case in cases:
                evaluator = evaluate_selection_only if args.mode == "selection" else evaluate_oracle_answer
                try:
                    result = evaluator(
                        case,
                        backend=backend,
                        prompt=prompt,
                        **({"max_documents": args.max_documents} if args.mode == "selection" else {}),
                    )
                    record = {**result, "repeat_index": repeat, "model": model, "status": "completed"}
                except Exception as exc:
                    record = {
                        "repeat_index": repeat,
                        "model": model,
                        "status": "error",
                        "mode": args.mode,
                        "case_id": case["id"],
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                records.append(record)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()

    completed = [r for r in records if r["status"] == "completed"]
    success = sum(bool(r.get("success")) for r in completed)
    summary = {
        "trials": len(records),
        "completed": len(completed),
        "successes": success,
        "success_rate": success / len(completed) if completed else None,
    }
    if args.mode == "selection":
        summary["top1_hits"] = sum(bool(r.get("top1_hit")) for r in completed)
        summary["top1_rate"] = summary["top1_hits"] / len(completed) if completed else None
        summary["complete_initial_plans"] = sum(bool(r.get("complete_initial_plan")) for r in completed)
        summary["complete_initial_plan_rate"] = (
            summary["complete_initial_plans"] / len(completed) if completed else None
        )
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"trials: {trials}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
