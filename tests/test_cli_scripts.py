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


def test_all_registered_corpora_and_datasets_validate_from_cli():
    corpora = run_cli("scripts/validate_corpus.py", "--all")
    assert corpora.returncode == 0, corpora.stderr
    assert "Corpus validation PASSED [northstar]" in corpora.stdout
    assert "Corpus validation PASSED [tell-aster]" in corpora.stdout

    datasets = run_cli("scripts/validate_dataset.py", "--all")
    assert datasets.returncode == 0, datasets.stderr
    assert "Dataset validation PASSED [northstar]" in datasets.stdout
    assert "Dataset validation PASSED [tell-aster]" in datasets.stdout
    assert "Cases:              120" in datasets.stdout


def test_tell_aster_individual_eval_configs_have_expected_dry_run_counts():
    single = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/tell-aster/eval-single-v1.yaml",
        "--dry-run",
    )
    assert single.returncode == 0, single.stderr
    assert "corpus: tell-aster" in single.stdout
    assert "cases: 80" in single.stdout
    assert "case trials: 80" in single.stdout

    multi = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/tell-aster/eval-multi-v1.yaml",
        "--dry-run",
    )
    assert multi.returncode == 0, multi.stderr
    assert "corpus: tell-aster" in multi.stdout
    assert "cases: 40" in multi.stdout
    assert "case trials: 40" in multi.stdout


def test_all_corpora_suite_dry_runs_are_resolved_without_model_calls():
    verify = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/verify-all-v14.yaml",
        "--dry-run",
    )
    assert verify.returncode == 0, verify.stderr
    assert "suite: verify-all-v14" in verify.stdout
    assert "corpus=northstar" in verify.stdout
    assert "corpus=tell-aster" in verify.stdout
    assert "case trials: 84" in verify.stdout

    full = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/eval-all-v14.yaml",
        "--runs",
        "1",
        "--dry-run",
    )
    assert full.returncode == 0, full.stderr
    assert "suite: eval-all-v14" in full.stdout
    assert "case trials: 180" in full.stdout


def test_v15_cross_corpus_suites_dry_run_without_model_calls():
    verify = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/verify-all-v15.yaml",
        "--dry-run",
    )
    assert verify.returncode == 0, verify.stderr
    assert "suite: verify-all-v15" in verify.stdout
    assert "experiments/v15/verify-single-v1.yaml" in verify.stdout
    assert "corpus=northstar" in verify.stdout
    assert "corpus=tell-aster" in verify.stdout

    full = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/eval-all-v15.yaml",
        "--runs",
        "1",
        "--dry-run",
    )
    assert full.returncode == 0, full.stderr
    assert "suite: eval-all-v15" in full.stdout
    assert "experiments/v15/eval-single-v1.yaml" in full.stdout
    assert "case trials: 180" in full.stdout


def test_v15_individual_config_resolves_v15_prompt():
    result = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/v15/tell-aster/verify-single-v1.yaml",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "progressive-disclosure-agent-system@v15" in result.stdout


def test_v16_cross_corpus_suites_dry_run_without_model_calls():
    verify = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/verify-all-v16.yaml",
        "--dry-run",
    )
    assert verify.returncode == 0, verify.stderr
    assert "suite: verify-all-v16" in verify.stdout
    assert "experiments/v16/verify-single-v1.yaml" in verify.stdout
    assert "corpus=northstar" in verify.stdout
    assert "corpus=tell-aster" in verify.stdout
    assert "case trials: 84" in verify.stdout

    full = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/eval-all-v16.yaml",
        "--runs",
        "1",
        "--dry-run",
    )
    assert full.returncode == 0, full.stderr
    assert "suite: eval-all-v16" in full.stdout
    assert "experiments/v16/eval-single-v1.yaml" in full.stdout
    assert "case trials: 180" in full.stdout


def test_v16_individual_config_resolves_v16_prompt():
    result = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/v16/tell-aster/verify-single-v1.yaml",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "progressive-disclosure-agent-system@v16" in result.stdout



def test_v17_cross_corpus_suites_dry_run_without_model_calls():
    verify = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/verify-all-v17.yaml",
        "--dry-run",
    )
    assert verify.returncode == 0, verify.stderr
    assert "suite: verify-all-v17" in verify.stdout
    assert "experiments/v17/verify-single-v1.yaml" in verify.stdout
    assert "corpus=northstar" in verify.stdout
    assert "corpus=tell-aster" in verify.stdout
    assert "case trials: 84" in verify.stdout

    full = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/eval-all-v17.yaml",
        "--runs",
        "1",
        "--dry-run",
    )
    assert full.returncode == 0, full.stderr
    assert "suite: eval-all-v17" in full.stdout
    assert "experiments/v17/eval-single-v1.yaml" in full.stdout
    assert "case trials: 180" in full.stdout


def test_v17_individual_config_resolves_v17_prompt():
    result = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/v17/tell-aster/verify-single-v1.yaml",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "progressive-disclosure-agent-system@v17" in result.stdout


def test_v18_cross_corpus_suites_use_release_dataset_and_three_selection_rounds():
    verify = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/verify-all-v18.yaml",
        "--dry-run",
    )
    assert verify.returncode == 0, verify.stderr
    assert "suite: verify-all-v18" in verify.stdout
    assert "corpus=northstar" in verify.stdout
    assert "corpus=tell-aster" in verify.stdout
    assert "case trials: 84" in verify.stdout
    assert "model calls (nominal): 168 minimum, 504 maximum" in verify.stdout

    tell = run_cli(
        "scripts/run_evals.py",
        "--config",
        "experiments/v18/tell-aster/eval-multi-v1.yaml",
        "--dry-run",
    )
    assert tell.returncode == 0, tell.stderr
    assert "dataset: tell-aster-eval-v2 v2" in tell.stdout
    assert "progressive-disclosure-agent-system@v18" in tell.stdout
    assert "max selection rounds: 3" in tell.stdout

    full = run_cli(
        "scripts/run_eval_suite.py",
        "--suite",
        "experiments/suites/eval-all-v18.yaml",
        "--runs",
        "1",
        "--dry-run",
    )
    assert full.returncode == 0, full.stderr
    assert "suite: eval-all-v18" in full.stdout
    assert "case trials: 180" in full.stdout
    assert "model calls (nominal): 360 minimum, 1080 maximum" in full.stdout
