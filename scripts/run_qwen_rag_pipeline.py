#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, log, env: dict[str, str]) -> None:
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"\n$ {printable}", flush=True)
    log.write(f"\n$ {printable}\n")
    log.flush()
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        log.write(line)
    return_code = process.wait()
    log.flush()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete reproducible Qwen hierarchical-RAG pipeline."
    )
    parser.add_argument("--device", default="mps", help="sentence-transformers device: mps, cpu, cuda")
    parser.add_argument("--download-models", action="store_true", help="Download the pinned Qwen models first")
    parser.add_argument("--with-paid-evals", action="store_true", help="After local retrieval checks, run the paid gpt-5-nano E2E suite")
    parser.add_argument("--skip-checks", action="store_true", help="Skip pytest/check_all/git diff checks")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Print the pipeline plan without loading models or running checks")
    args = parser.parse_args()

    if args.dry_run:
        print("Qwen RAG pipeline plan")
        print(f"device: {args.device}")
        print(f"download_models: {args.download_models}")
        print(f"with_paid_evals: {args.with_paid_evals}")
        print("stages: checks -> model plan/download -> suite dry-run -> build indexes -> retrieval evals" + (" -> paid smoke -> paid E2E" if args.with_paid_evals else ""))
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = args.output or PROJECT_ROOT / "results" / f"{stamp}-qwen-rag-pipeline"
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / "pipeline.log"
    summary_path = root / "pipeline-summary.json"
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    stages: list[str] = []
    try:
        with log_path.open("w", encoding="utf-8") as log:
            if not args.skip_checks:
                _run([sys.executable, "-m", "pytest"], log=log, env=env)
                stages.append("pytest")
                _run([sys.executable, "scripts/check_all.py"], log=log, env=env)
                stages.append("check_all")
                if (PROJECT_ROOT / ".git").exists():
                    _run(["git", "diff", "--check"], log=log, env=env)
                    stages.append("git_diff_check")

            _run(
                [
                    sys.executable,
                    "scripts/download_qwen_rag_models.py",
                    "--dry-run",
                ],
                log=log,
                env=env,
            )
            stages.append("model_plan")
            if args.download_models:
                _run([sys.executable, "scripts/download_qwen_rag_models.py"], log=log, env=env)
                stages.append("download_models")

            _run(
                [
                    sys.executable,
                    "scripts/run_qwen_rag_suite.py",
                    "--suite",
                    "experiments/suites/qwen-rag-all.yaml",
                    "--device",
                    args.device,
                    "--dry-run",
                ],
                log=log,
                env=env,
            )
            stages.append("suite_dry_run")

            _run(
                [
                    sys.executable,
                    "scripts/build_qwen_rag_index.py",
                    "--all",
                    "--device",
                    args.device,
                ],
                log=log,
                env=env,
            )
            stages.append("build_indexes")

            retrieval_configs = (
                ("northstar", "experiments/qwen-rag/northstar.yaml"),
                ("tell-aster", "experiments/qwen-rag/tell-aster.yaml"),
            )
            for label, config in retrieval_configs:
                _run(
                    [
                        sys.executable,
                        "scripts/run_qwen_rag_retrieval_eval.py",
                        "--config",
                        config,
                        "--device",
                        args.device,
                        "--output",
                        str(root / f"retrieval-{label}"),
                    ],
                    log=log,
                    env=env,
                )
                stages.append(f"retrieval_{label}")

            if args.with_paid_evals:
                _run(
                    [
                        sys.executable,
                        "scripts/run_qwen_rag_evals.py",
                        "--config",
                        "experiments/qwen-rag/northstar.yaml",
                        "--device",
                        args.device,
                        "--limit",
                        "1",
                        "--output",
                        str(root / "e2e-smoke"),
                    ],
                    log=log,
                    env=env,
                )
                stages.append("paid_smoke")
                _run(
                    [
                        sys.executable,
                        "scripts/run_qwen_rag_suite.py",
                        "--suite",
                        "experiments/suites/qwen-rag-all.yaml",
                        "--device",
                        args.device,
                        "--output",
                        str(root / "e2e"),
                    ],
                    log=log,
                    env=env,
                )
                stages.append("paid_e2e")
    except Exception as exc:
        summary_path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "completed_stages": stages,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "log": str(log_path),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise

    summary_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_stages": stages,
                "device": args.device,
                "download_models": args.download_models,
                "with_paid_evals": args.with_paid_evals,
                "log": str(log_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nQwen RAG pipeline completed: {root}")
    print(f"summary: {summary_path}")
    print(f"log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
