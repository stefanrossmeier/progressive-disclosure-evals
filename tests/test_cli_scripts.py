from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["OPENAI_MODEL"] = "test-model"
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_run_evals_direct_script_dry_run_works():
    result = run_cli(
        "scripts/run_evals.py",
        "--dry-run",
        "--runs",
        "1",
        "--limit",
        "1",
    )

    assert result.returncode == 0, result.stderr
    assert "cases: 1" in result.stdout
    assert "models: 1 (test-model)" in result.stdout
    assert "progressive-disclosure-agent-system@v14" in result.stdout
    assert "runs per case: 1" in result.stdout
    assert "case trials: 1" in result.stdout
    assert "model calls (nominal): 2 minimum, 4 maximum" in result.stdout


def test_run_evals_rejects_non_positive_overrides():
    result = run_cli("scripts/run_evals.py", "--dry-run", "--runs", "0")
    assert result.returncode != 0
    assert "--runs must be >= 1" in result.stderr


def test_aggregate_results_direct_script_help_works():
    result = run_cli("scripts/aggregate_results.py", "--help")
    assert result.returncode == 0, result.stderr
    assert "Aggregate progressive-disclosure benchmark JSONL results" in result.stdout


def test_validate_dataset_direct_script_works_without_editable_install_assumptions():
    result = run_cli("scripts/validate_dataset.py")
    assert result.returncode == 0, result.stderr
    assert "Dataset validation PASSED" in result.stdout


def test_run_diagnostics_direct_script_dry_run_works():
    result = run_cli(
        "scripts/run_diagnostics.py",
        "--mode",
        "selection",
        "--tag",
        "single_doc",
        "--runs",
        "1",
        "--limit",
        "3",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "mode: selection" in result.stdout
    assert "cases: 3" in result.stdout
    assert "prompt: progressive-disclosure-agent-system@v14" in result.stdout
    assert "model calls: 3" in result.stdout


def test_single_and_multi_validation_configs_have_expected_dry_run_counts():
    single = run_cli("scripts/run_evals.py", "--config", "experiments/eval-single-v1.yaml", "--dry-run")
    assert single.returncode == 0, single.stderr
    assert "cases: 40" in single.stdout
    assert "config case tags: single_doc" in single.stdout
    assert "case trials: 200" in single.stdout

    multi = run_cli("scripts/run_evals.py", "--config", "experiments/eval-multi-v1.yaml", "--dry-run")
    assert multi.returncode == 0, multi.stderr
    assert "cases: 20" in multi.stdout
    assert "config case tags: multi_doc" in multi.stdout
    assert "case trials: 100" in multi.stdout


def test_small_verification_configs_have_expected_dry_run_counts():
    single = run_cli("scripts/run_evals.py", "--config", "experiments/verify-single-v1.yaml", "--dry-run")
    assert single.returncode == 0, single.stderr
    assert "cases: 8" in single.stdout
    assert "case trials: 24" in single.stdout

    multi = run_cli("scripts/run_evals.py", "--config", "experiments/verify-multi-v1.yaml", "--dry-run")
    assert multi.returncode == 0, multi.stderr
    assert "cases: 8" in multi.stdout
    assert "case trials: 16" in multi.stdout


def test_multi_dev_v2_dataset_and_verification_config_are_valid():
    validation = run_cli("scripts/validate_dataset.py", "--dataset", "datasets/multi-dev-v2.yaml")
    assert validation.returncode == 0, validation.stderr
    assert "Cases:              10" in validation.stdout
    assert "Multi-document:     10" in validation.stdout

    dry_run = run_cli("scripts/run_evals.py", "--config", "experiments/verify-multi-v2.yaml", "--dry-run")
    assert dry_run.returncode == 0, dry_run.stderr
    assert "dataset: multi-dev-v2 v2" in dry_run.stdout
    assert "cases: 10" in dry_run.stdout
    assert "case trials: 20" in dry_run.stdout
    assert "model calls (nominal): 40 minimum, 80 maximum" in dry_run.stdout
