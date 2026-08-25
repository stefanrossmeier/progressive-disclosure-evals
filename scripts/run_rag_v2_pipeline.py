#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _run(command: list[str], *, log, step: str) -> None:
    pretty = " ".join(command)
    banner = f"\n=== {step} ===\n$ {pretty}\n"
    print(banner, end="", flush=True)
    log.write(banner)
    log.flush()
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log.write(line)
    returncode = process.wait()
    log.flush()
    if returncode:
        raise RuntimeError(f"step failed ({returncode}): {step}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete hybrid-RAG v2 validation pipeline: deterministic checks, "
            "index rebuild, retrieval-only baseline/reranker evaluations, and optionally "
            "the paid one-call-per-case end-to-end suite."
        )
    )
    parser.add_argument("--device", default="cpu", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--offline", action="store_true", help="Require embedding and reranker models to already be cached")
    parser.add_argument("--skip-index-build", action="store_true", help="Reuse existing corpus indexes after fingerprint verification")
    parser.add_argument(
        "--with-paid-evals",
        action="store_true",
        help="After all local checks pass, run a one-case API smoke test and the full 180-case reranked E2E suite",
    )
    parser.add_argument("--output", type=Path, help="Pipeline result directory")
    args = parser.parse_args()

    output = args.output or Path("results") / f"{_stamp()}-rag-hybrid-rerank-v2-pipeline"
    output.mkdir(parents=True, exist_ok=False)
    log_path = output / "pipeline.log"
    summary_path = output / "pipeline-summary.json"

    py = sys.executable
    common_device = ["--device", args.device]
    offline = ["--offline"] if args.offline else []
    steps: list[str] = []
    status = "failed"
    error: str | None = None

    try:
        with log_path.open("w", encoding="utf-8") as log:
            commands: list[tuple[str, list[str]]] = [
                ("deterministic repository checks", [py, "scripts/check_all.py"]),
                ("git whitespace check", ["git", "diff", "--check"]),
                (
                    "reranked suite config dry-run",
                    [py, "scripts/run_rag_suite.py", "--suite", "experiments/suites/rag-hybrid-rerank-all.yaml", "--dry-run"],
                ),
            ]
            for step, command in commands:
                _run(command, log=log, step=step)
                steps.append(step)

            if not args.skip_index_build:
                step = "rebuild local RAG indexes"
                _run(
                    [py, "scripts/build_rag_index.py", "--all", *common_device, *offline],
                    log=log,
                    step=step,
                )
                steps.append(step)

            retrieval_runs = [
                (
                    "hybrid baseline retrieval — northstar",
                    "experiments/rag/hybrid-northstar.yaml",
                    output / "retrieval-hybrid-northstar",
                ),
                (
                    "hybrid baseline retrieval — tell-aster",
                    "experiments/rag/hybrid-tell-aster.yaml",
                    output / "retrieval-hybrid-tell-aster",
                ),
                (
                    "hybrid rerank retrieval — northstar",
                    "experiments/rag/hybrid-rerank-northstar.yaml",
                    output / "retrieval-rerank-northstar",
                ),
                (
                    "hybrid rerank retrieval — tell-aster",
                    "experiments/rag/hybrid-rerank-tell-aster.yaml",
                    output / "retrieval-rerank-tell-aster",
                ),
            ]
            for step, config, target in retrieval_runs:
                _run(
                    [
                        py,
                        "scripts/run_rag_retrieval_eval.py",
                        "--config",
                        config,
                        *common_device,
                        *offline,
                        "--output",
                        str(target),
                    ],
                    log=log,
                    step=step,
                )
                steps.append(step)

            if args.with_paid_evals:
                step = "paid API smoke test — reranked northstar"
                _run(
                    [
                        py,
                        "scripts/run_rag_evals.py",
                        "--config",
                        "experiments/rag/hybrid-rerank-northstar.yaml",
                        *common_device,
                        *offline,
                        "--limit",
                        "1",
                        "--output",
                        str(output / "e2e-smoke"),
                    ],
                    log=log,
                    step=step,
                )
                steps.append(step)

                step = "paid full E2E suite — hybrid rerank"
                _run(
                    [
                        py,
                        "scripts/run_rag_suite.py",
                        "--suite",
                        "experiments/suites/rag-hybrid-rerank-all.yaml",
                        *common_device,
                        *offline,
                        "--output",
                        str(output / "e2e"),
                    ],
                    log=log,
                    step=step,
                )
                steps.append(step)

        status = "passed"
        return 0
    except (RuntimeError, OSError) as exc:
        error = str(exc)
        print(f"\nPIPELINE FAILED: {error}", file=sys.stderr)
        return 1
    finally:
        summary = {
            "schema_version": 1,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": args.device,
            "offline": args.offline,
            "index_build_skipped": args.skip_index_build,
            "paid_evals_requested": args.with_paid_evals,
            "completed_steps": steps,
            "error": error,
            "pipeline_log": str(log_path),
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"\npipeline results: {output}")
        print(f"pipeline summary: {summary_path}")
        print(f"pipeline log: {log_path}")


if __name__ == "__main__":
    raise SystemExit(main())
