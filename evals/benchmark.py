from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from evals.agent_dev import evaluate_case, result_to_dict
from progressive_disclosure.corpora import corpus_name_from_dataset, get_corpus_spec
from progressive_disclosure.config import (
    get_openai_model,
    get_openai_reasoning_effort,
    get_openai_text_verbosity,
    load_project_env,
)
from progressive_disclosure.llm import OpenAIResponsesBackend
from progressive_disclosure.prompts import DEFAULT_AGENT_PROMPT_PATH, load_prompt_artifact


@dataclass(frozen=True)
class BenchmarkPlan:
    name: str
    dataset: Path
    runs_per_case: int
    max_documents: int
    prompts: tuple[Path, ...]
    models: tuple[str, ...]
    max_selection_rounds: int = 2
    case_ids: tuple[str, ...] = ()
    case_tags: tuple[str, ...] = ()
    corpus_name: str = "northstar"
    corpus_root: Path = Path("corpus/northstar-corpus")


def load_eval_dataset(path: Path | str = "datasets/eval-v1.yaml") -> dict[str, Any]:
    dataset_path = Path(path)
    data = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("eval dataset root must be a mapping")
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("eval dataset requires non-empty name")
    if not isinstance(data.get("version"), int):
        raise ValueError("eval dataset requires integer version")
    if not isinstance(data.get("cases"), list) or not data["cases"]:
        raise ValueError("eval dataset requires non-empty cases list")
    return data


def _resolve_model(value: str) -> str:
    if value.startswith("env:"):
        env_name = value.split(":", 1)[1]
        resolved = os.getenv(env_name)
        if not resolved:
            raise ValueError(f"model environment variable is not set: {env_name}")
        return resolved
    return value


def load_plan(path: Path | str = "experiments/eval-v1.yaml") -> BenchmarkPlan:
    load_project_env()
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("experiment config root must be a mapping")

    prompts = data.get("prompts") or [str(DEFAULT_AGENT_PROMPT_PATH)]
    models = data.get("models") or ["env:OPENAI_MODEL"]
    case_ids = data.get("case_ids") or []
    case_tags = data.get("case_tags") or []
    if not isinstance(prompts, list) or not all(isinstance(x, str) for x in prompts):
        raise ValueError("experiment prompts must be a list of paths")
    if not isinstance(models, list) or not all(isinstance(x, str) for x in models):
        raise ValueError("experiment models must be a list")
    if not isinstance(case_ids, list) or not all(isinstance(x, str) and x.strip() for x in case_ids):
        raise ValueError("experiment case_ids must be a list of non-empty strings")
    if not isinstance(case_tags, list) or not all(isinstance(x, str) and x.strip() for x in case_tags):
        raise ValueError("experiment case_tags must be a list of non-empty strings")

    runs = int(data.get("runs_per_case", 1))
    max_documents = int(data.get("max_documents", 4))
    max_selection_rounds = int(data.get("max_selection_rounds", 2))
    if runs < 1:
        raise ValueError("runs_per_case must be >= 1")
    if max_documents < 1:
        raise ValueError("max_documents must be >= 1")
    if max_selection_rounds < 1:
        raise ValueError("max_selection_rounds must be >= 1")

    dataset_path = Path(data.get("dataset", "datasets/eval-v1.yaml"))
    dataset = load_eval_dataset(dataset_path)
    corpus_name = str(data.get("corpus") or corpus_name_from_dataset(dataset))
    corpus_spec = get_corpus_spec(corpus_name)
    corpus_root = Path(data.get("corpus_root") or corpus_spec.root)

    return BenchmarkPlan(
        name=str(data.get("name") or config_path.stem),
        dataset=dataset_path,
        corpus_name=corpus_name,
        corpus_root=corpus_root,
        runs_per_case=runs,
        max_documents=max_documents,
        max_selection_rounds=max_selection_rounds,
        prompts=tuple(Path(x) for x in prompts),
        models=tuple(_resolve_model(x) for x in models),
        case_ids=tuple(dict.fromkeys(x.strip() for x in case_ids)),
        case_tags=tuple(dict.fromkeys(x.strip() for x in case_tags)),
    )


def select_cases(
    cases: Iterable[dict[str, Any]],
    *,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = []
    for case in cases:
        if case_ids and case.get("id") not in case_ids:
            continue
        case_tags = set(case.get("tags", []))
        if tags and not tags.issubset(case_tags):
            continue
        selected.append(case)
    if limit is not None:
        selected = selected[:limit]
    return selected




def resolve_case_filters(
    plan: BenchmarkPlan,
    *,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
) -> tuple[set[str] | None, set[str] | None]:
    """Combine experiment selectors with CLI selectors without exposing them to the agent.

    Experiment selectors define the benchmark slice. CLI selectors may only narrow that slice:
    case IDs are intersected and tags use the existing AND semantics.
    """

    configured_ids = set(plan.case_ids) or None
    if configured_ids is not None and case_ids is not None:
        effective_ids: set[str] | None = configured_ids & case_ids
    else:
        effective_ids = configured_ids if configured_ids is not None else case_ids

    effective_tags = set(plan.case_tags)
    if tags:
        effective_tags.update(tags)
    return effective_ids, (effective_tags or None)

def _sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _corpus_sha256(root: Path | str) -> str:
    root_path = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root_path.rglob("*.md")):
        relative = path.relative_to(root_path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def default_output_dir(experiment_name: str) -> Path:
    # Microseconds prevent accidental append/manifest overwrite when two runs start
    # within the same second. UTC is retained so result directories sort globally.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("results") / f"{stamp}-{experiment_name}"


def run_benchmark(
    plan: BenchmarkPlan,
    *,
    output_dir: Path,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
    fail_fast: bool = False,
    sleep_seconds: float = 0.0,
    quiet: bool = False,
) -> Path:
    dataset = load_eval_dataset(plan.dataset)
    effective_case_ids, effective_tags = resolve_case_filters(
        plan, case_ids=case_ids, tags=tags
    )
    cases = select_cases(
        dataset["cases"],
        case_ids=effective_case_ids,
        tags=effective_tags,
        limit=limit,
    )
    if not cases:
        raise ValueError("case selection is empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    trials_path = output_dir / "trials.jsonl"
    if trials_path.exists() and trials_path.stat().st_size > 0:
        raise FileExistsError(
            f"refusing to append to existing benchmark results: {trials_path}; "
            "choose a new --output directory and aggregate runs afterwards"
        )

    prompt_artifacts = [(path, load_prompt_artifact(path)) for path in plan.prompts]
    dataset_sha256 = _sha256_file(plan.dataset)
    corpus_sha256 = _corpus_sha256(plan.corpus_root)
    manifest = {
        "schema_version": 1,
        "experiment_name": plan.name,
        "dataset": str(plan.dataset),
        "dataset_name": dataset["name"],
        "dataset_version": dataset["version"],
        "corpus_name": plan.corpus_name,
        "corpus_root": str(plan.corpus_root),
        "runs_per_case": plan.runs_per_case,
        "max_documents": plan.max_documents,
        "max_selection_rounds": plan.max_selection_rounds,
        "prompts": [str(x) for x in plan.prompts],
        "prompt_artifacts": [
            {
                "path": str(path),
                "id": prompt.id,
                "version": prompt.version,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path, prompt in prompt_artifacts
        ],
        "models": list(plan.models),
        "configured_case_ids": list(plan.case_ids),
        "configured_case_tags": list(plan.case_tags),
        "effective_case_ids": sorted(effective_case_ids) if effective_case_ids is not None else [],
        "effective_case_tags": sorted(effective_tags) if effective_tags is not None else [],
        "dataset_sha256": dataset_sha256,
        "corpus_sha256": corpus_sha256,
        "selected_cases": [case["id"] for case in cases],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    total_trials = len(plan.models) * len(plan.prompts) * plan.runs_per_case * len(cases)
    completed_trials = 0
    with trials_path.open("a", encoding="utf-8") as handle:
        for model in plan.models:
            backend = OpenAIResponsesBackend(
                model,
                reasoning_effort=get_openai_reasoning_effort(),
                text_verbosity=get_openai_text_verbosity(),
            )
            for prompt_path, prompt in prompt_artifacts:
                prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
                for repeat_index in range(1, plan.runs_per_case + 1):
                    for case in cases:
                        base = {
                            "schema_version": 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "experiment_name": plan.name,
                            "dataset_name": dataset["name"],
                            "dataset_version": dataset["version"],
                            "corpus_name": plan.corpus_name,
                            "corpus_root": str(plan.corpus_root),
                            "repeat_index": repeat_index,
                            "case_id": case["id"],
                            "case_title": case.get("title", ""),
                            "tags": case.get("tags", []),
                            "question": case["question"].strip(),
                            "required_documents": case.get("required_documents", []),
                            "expected_contains": [str(x) for x in case.get("expected_contains", [])],
                            "model": model,
                            "prompt_id": prompt.id,
                            "prompt_version": prompt.version,
                            "prompt_path": str(prompt.path),
                            "prompt_sha256": prompt_sha256,
                            "dataset_sha256": dataset_sha256,
                            "corpus_sha256": corpus_sha256,
                            "reasoning_effort": backend.reasoning_effort,
                            "text_verbosity": backend.text_verbosity,
                        }
                        try:
                            result = evaluate_case(
                                case,
                                backend=backend,
                                corpus_root=plan.corpus_root,
                                max_documents=plan.max_documents,
                                max_selection_rounds=plan.max_selection_rounds,
                                prompt=prompt,
                            )
                            record = {
                                **base,
                                "status": "completed",
                                "result": result_to_dict(result),
                            }
                        except Exception as exc:  # benchmark must preserve partial progress
                            record = {
                                **base,
                                "status": "error",
                                "error_type": type(exc).__name__,
                                "error_message": str(exc),
                            }
                            if fail_fast:
                                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                                handle.flush()
                                raise
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        handle.flush()
                        completed_trials += 1
                        if not quiet:
                            outcome = (
                                "ERROR" if record["status"] == "error"
                                else ("PASS" if record["result"].get("overall_success") else "FAIL")
                            )
                            print(
                                f"[{completed_trials}/{total_trials}] {model} "
                                f"prompt={prompt.id}@v{prompt.version} repeat={repeat_index} "
                                f"{case['id']} {outcome}"
                            )
                        if sleep_seconds > 0:
                            time.sleep(sleep_seconds)
    return trials_path
