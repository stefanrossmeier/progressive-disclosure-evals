#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from evals.aggregate import load_records, write_aggregate  # noqa: E402
from evals.benchmark import load_eval_dataset, select_cases  # noqa: E402
from evals.grading import answer_matches_expected  # noqa: E402
from progressive_disclosure.config import (  # noqa: E402
    get_openai_reasoning_effort,
    get_openai_text_verbosity,
    load_project_env,
)
from progressive_disclosure.corpora import get_corpus_spec  # noqa: E402
from progressive_disclosure.knowledge import KnowledgeBase  # noqa: E402
from progressive_disclosure.llm import OpenAIResponsesBackend  # noqa: E402
from progressive_disclosure.prompts import load_prompt_artifact  # noqa: E402
from rag_baseline.answering import RagAnswerer  # noqa: E402
from rag_baseline.models import RagChunk, RagSearchResult  # noqa: E402

BACKENDS = ("basic-memory", "openviking", "hindsight")
CORPORA = ("northstar", "tell-aster")
DATASETS = {
    "northstar": Path("datasets/eval-v1.yaml"),
    "tell-aster": Path("datasets/tell-aster-eval-v2.yaml"),
}
DEFAULT_PROMPT = Path("prompts/rag/system-v1.md")
DEFAULT_TOP_K_DOCUMENTS = 6
DEFAULT_PROVIDER_HIT_LIMIT = 24
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DocumentInfo:
    document_id: str
    title: str
    path: str


@dataclass(frozen=True)
class WorkerConfig:
    backend: str
    python: Path
    worker: Path
    runtime_root: Path
    memory_root: Path


class WorkerSession:
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.process: subprocess.Popen[str] | None = None
        self.stderr_handle: Any | None = None
        self.stderr_path = self.config.runtime_root / "worker.stderr.log"
        self.hello: dict[str, Any] | None = None

    def _stderr_tail(self, size: int = 12000) -> str:
        if not self.stderr_path.is_file():
            return ""
        text = self.stderr_path.read_text(encoding="utf-8", errors="replace")
        return text[-size:]

    def __enter__(self) -> "WorkerSession":
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self.config.runtime_root.mkdir(parents=True, exist_ok=True)
        self.stderr_handle = self.stderr_path.open("a", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(self.config.python), str(self.config.worker)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr_handle,
            text=True,
            bufsize=1,
            env=env,
        )
        self.hello = self.request({"op": "hello", "runtime_root": str(self.config.runtime_root)})
        return self

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("worker session is not running")
        if self.process.poll() is not None:
            raise RuntimeError(
                f"{self.config.backend} worker exited with {self.process.returncode}: "
                f"{self._stderr_tail().strip()}"
            )
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(
                f"{self.config.backend} worker returned no response: {self._stderr_tail().strip()}"
            )
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{self.config.backend} worker emitted invalid JSON: {line!r}\n"
                f"stderr: {self._stderr_tail()}"
            ) from exc
        if not response.get("ok"):
            trace = response.get("traceback")
            suffix = f"\n{trace}" if isinstance(trace, str) and trace.strip() else ""
            raise RuntimeError(
                f"{self.config.backend} worker error: {response.get('error_type')}: "
                f"{response.get('error_message')}{suffix}"
            )
        return response

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.process is None:
            return
        try:
            if self.process.stdin and self.process.poll() is None:
                self.process.stdin.write(json.dumps({"op": "close"}) + "\n")
                self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            self.process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate()
        finally:
            if self.stderr_handle is not None:
                self.stderr_handle.close()
                self.stderr_handle = None


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _backend_dir(backend: str) -> Path:
    return EXPERIMENT_ROOT / backend


def _memory_root(backend: str, corpus: str) -> Path:
    return _backend_dir(backend) / "memory" / corpus


def _runtime_root(backend: str) -> Path:
    return _backend_dir(backend) / "runtime"


def _venv_python(backend: str) -> Path:
    if os.name == "nt":
        return EXPERIMENT_ROOT / ".venvs" / backend / "Scripts" / "python.exe"
    return EXPERIMENT_ROOT / ".venvs" / backend / "bin" / "python"


def _worker_path(backend: str) -> Path:
    return EXPERIMENT_ROOT / "workers" / f"{backend.replace('-', '_')}_worker.py"


def _worker_config(backend: str) -> WorkerConfig:
    return WorkerConfig(
        backend=backend,
        python=_venv_python(backend),
        worker=_worker_path(backend),
        runtime_root=_runtime_root(backend),
        memory_root=_backend_dir(backend) / "memory",
    )


def _selected_backends(value: str) -> tuple[str, ...]:
    if value == "all":
        return BACKENDS
    if value not in BACKENDS:
        raise ValueError(value)
    return (value,)


def _copy_markdown_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*.md")):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def prepare_memories(backends: Iterable[str], *, reset_memory: bool) -> None:
    for backend in backends:
        memory_parent = _backend_dir(backend) / "memory"
        if reset_memory and memory_parent.exists():
            shutil.rmtree(memory_parent)
        memory_parent.mkdir(parents=True, exist_ok=True)
        for corpus in CORPORA:
            spec = get_corpus_spec(corpus)
            source = PROJECT_ROOT / spec.root
            destination = _memory_root(backend, corpus)
            if destination.exists() and any(destination.rglob("*.md")):
                source_hash = _sha256_tree(source)
                destination_hash = _sha256_tree(destination)
                if source_hash != destination_hash:
                    raise RuntimeError(
                        f"{destination} differs from {source}; use --reset-memory to recreate the snapshot"
                    )
            else:
                _copy_markdown_tree(source, destination)
            print(
                f"prepared {backend}/{corpus}: "
                f"{len(list(destination.rglob('*.md')))} markdown files"
            )


def _catalog(memory_root: Path) -> tuple[KnowledgeBase, dict[str, DocumentInfo]]:
    kb = KnowledgeBase(memory_root)
    catalog = {
        item.id: DocumentInfo(document_id=item.id, title=item.title, path=item.path)
        for item in kb.catalog()
    }
    return kb, catalog


def _normalize(value: str) -> str:
    return "".join(ch.casefold() for ch in value if ch.isalnum())


def _flatten_strings(value: Any, *, key: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, str):
        out.append((key, value))
    elif isinstance(value, dict):
        for child_key, child in value.items():
            out.extend(_flatten_strings(child, key=str(child_key)))
    elif isinstance(value, list):
        for child in value:
            out.extend(_flatten_strings(child, key=key))
    return out


def _map_hit_to_document(hit: dict[str, Any], catalog: dict[str, DocumentInfo]) -> tuple[str | None, str]:
    explicit = hit.get("document_id")
    if isinstance(explicit, str) and explicit in catalog:
        return explicit, "provider_document_id"

    strings = _flatten_strings(hit)
    source_keys = {
        "document_id",
        "doc_id",
        "external_id",
        "file_path",
        "filepath",
        "path",
        "uri",
        "permalink",
        "title",
        "source",
        "source_id",
    }
    ordered = [pair for pair in strings if pair[0].casefold() in source_keys] + [
        pair for pair in strings if pair[0].casefold() not in source_keys
    ]

    path_aliases: dict[str, str] = {}
    basename_aliases: dict[str, list[str]] = defaultdict(list)
    title_aliases: dict[str, list[str]] = defaultdict(list)
    for doc_id, doc in catalog.items():
        path_aliases[doc.path.casefold()] = doc_id
        basename_aliases[Path(doc.path).name.casefold()].append(doc_id)
        title_aliases[_normalize(doc.title)].append(doc_id)

    for key, value in ordered:
        folded = value.casefold()
        if value in catalog:
            return value, f"exact_id:{key or 'value'}"
        for doc_id in sorted(catalog, key=len, reverse=True):
            if doc_id.casefold() in folded:
                return doc_id, f"id_in_{key or 'value'}"
        for path, doc_id in path_aliases.items():
            if path and path in folded:
                return doc_id, f"path_in_{key or 'value'}"
        for basename, doc_ids in basename_aliases.items():
            if len(doc_ids) == 1 and basename and basename in folded:
                return doc_ids[0], f"basename_in_{key or 'value'}"
        normalized = _normalize(value)
        for title, doc_ids in title_aliases.items():
            if len(doc_ids) == 1 and title and (title == normalized or title in normalized):
                return doc_ids[0], f"title_in_{key or 'value'}"
    return None, "unresolved"


def _score_from_hit(hit: dict[str, Any], rank: int) -> float:
    for key in ("score", "similarity", "relevance_score", "distance"):
        value = hit.get(key)
        if isinstance(value, (int, float)):
            if key == "distance":
                return 1.0 / (1.0 + float(value))
            return float(value)
    return 1.0 / rank


def _provider_results_to_rag(
    hits: list[dict[str, Any]],
    *,
    knowledge: KnowledgeBase,
    catalog: dict[str, DocumentInfo],
    top_k_documents: int,
) -> tuple[list[RagSearchResult], list[dict[str, Any]], list[str]]:
    mapped_hits: list[dict[str, Any]] = []
    selected: list[tuple[str, float]] = []
    seen: set[str] = set()
    unresolved = 0

    for provider_rank, raw_hit in enumerate(hits, start=1):
        doc_id, reason = _map_hit_to_document(raw_hit, catalog)
        mapped = dict(raw_hit)
        mapped["provider_rank"] = provider_rank
        mapped["mapped_document_id"] = doc_id
        mapped["mapping_reason"] = reason
        mapped_hits.append(mapped)
        if doc_id is None:
            unresolved += 1
            continue
        if doc_id in seen:
            continue
        seen.add(doc_id)
        if len(selected) < top_k_documents:
            selected.append((doc_id, _score_from_hit(raw_hit, provider_rank)))

    results: list[RagSearchResult] = []
    document_order: list[str] = []
    for rank, (doc_id, score) in enumerate(selected, start=1):
        info = catalog[doc_id]
        doc = knowledge.read(doc_id)
        document_order.append(doc_id)
        results.append(
            RagSearchResult(
                rank=rank,
                chunk=RagChunk(
                    id=f"memory:{doc_id}",
                    document_id=doc_id,
                    title=info.title,
                    description="",
                    path=info.path,
                    heading="",
                    text=doc.content,
                    search_text=doc.content,
                ),
                score=score,
            )
        )

    if unresolved:
        # Kept in trial JSON; this short field makes it easy to grep aggregate failures later.
        for item in mapped_hits:
            item.setdefault("mapping_summary", f"unresolved_provider_hits={unresolved}")
    return results, mapped_hits, document_order


def _discovery(document_order: tuple[str, ...], required: set[str]) -> dict[str, Any]:
    read_set = set(document_order)
    matched = read_set & required
    recall = len(matched) / len(required) if required else 1.0
    precision = len(matched) / len(read_set) if read_set else (1.0 if not required else 0.0)
    first_gold = next((i for i, doc_id in enumerate(document_order) if doc_id in required), None)
    complete_at: int | None = 0 if not required else None
    seen: set[str] = set()
    for index, doc_id in enumerate(document_order, start=1):
        if doc_id in required:
            seen.add(doc_id)
        if required and seen == required:
            complete_at = index
            break
    return {
        "document_reads": len(document_order),
        "required_document_recall": recall,
        "document_precision": precision,
        "wrong_documents_before_first_gold": first_gold if first_gold is not None else len(document_order),
        "reads_to_complete_discovery": complete_at,
        "reads_after_complete_discovery": len(document_order) - complete_at if complete_at is not None else None,
        "complete_discovery": recall == 1.0,
    }


def _failure_classification(*, answer_ok: bool, discovery: dict[str, Any], sources_ok: bool, termination: str) -> str:
    if not discovery["complete_discovery"]:
        return "knowledge_discovery_failure"
    if termination != "answer":
        return "incomplete_run"
    if not sources_ok:
        return "evidence_attribution_failure"
    if not answer_ok:
        return "knowledge_application_failure"
    if discovery["document_precision"] < 1.0 or (discovery["reads_after_complete_discovery"] or 0) > 0:
        return "success_with_discovery_inefficiency"
    return "success"


def _evidence_excerpts(knowledge: KnowledgeBase, document_order: Iterable[str], expected: tuple[str, ...]) -> dict[str, list[str]]:
    folded = [value.casefold() for value in expected]
    out: dict[str, list[str]] = {}
    for doc_id in document_order:
        lines = [line.strip() for line in knowledge.read(doc_id).content.splitlines() if line.strip()]
        matches = [line for line in lines if any(value in line.casefold() for value in folded)]
        if matches:
            out[doc_id] = matches[:10]
    return out


def _answer_model() -> str:
    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise RuntimeError("OPENAI_MODEL is not set; use the same model as the frozen benchmark (currently gpt-5-nano)")
    return model


def _evaluate_case(
    *,
    backend_name: str,
    case: dict[str, Any],
    corpus: str,
    memory_root: Path,
    provider_response: dict[str, Any],
    answerer: RagAnswerer,
    knowledge: KnowledgeBase,
    catalog: dict[str, DocumentInfo],
    top_k_documents: int,
) -> dict[str, Any]:
    raw_hits = provider_response.get("hits") or []
    if not isinstance(raw_hits, list):
        raise TypeError(f"provider hits must be a list, got {type(raw_hits).__name__}")
    normalized_hits = [item if isinstance(item, dict) else {"value": item} for item in raw_hits]
    rag_results, mapped_hits, document_order = _provider_results_to_rag(
        normalized_hits,
        knowledge=knowledge,
        catalog=catalog,
        top_k_documents=top_k_documents,
    )
    answer = answerer.answer(case["question"], rag_results)
    required = set(case.get("required_documents", []))
    expected = tuple(str(value) for value in case.get("expected_contains", []))
    discovery = _discovery(tuple(document_order), required)
    answer_ok = answer_matches_expected(answer.answer, expected, question=case["question"])
    sources_ok = required.issubset(set(answer.cited_sources))
    overall = answer.termination == "answer" and answer_ok and discovery["complete_discovery"] and sources_ok
    answer_and_discovery = answer.termination == "answer" and answer_ok and discovery["complete_discovery"]
    opened_chars = sum(len(knowledge.read(doc_id).content) for doc_id in document_order)
    full_chars = knowledge.full_content_characters
    retrieval_ms = float(provider_response.get("elapsed_ms") or 0.0)
    unresolved = sum(1 for hit in mapped_hits if hit.get("mapped_document_id") is None)

    return {
        "case_id": case["id"],
        "question": case["question"].strip(),
        "eval_criteria": {
            "expected_answer_values": list(expected),
            "required_documents": sorted(required),
            "ideal_model_calls": 1,
            "gold_visible_to_agent": False,
            "answer_rule": "Same deterministic answer matcher as the frozen progressive-disclosure/RAG benchmark.",
            "discovery_rule": "All required documents must appear in the provider-ranked unique-document set.",
            "source_rule": "The shared RAG answerer must cite all required documents.",
            "overall_rule": "Answer correct AND all required documents retrieved AND all required documents cited.",
        },
        "runtime_policy": {
            "mechanism": f"{backend_name}_retrieval_then_shared_whole_document_rag_answer",
            "memory_ground_truth": "backend-specific copied Markdown snapshot",
            "top_k_documents": top_k_documents,
            "provider_hit_limit": provider_response.get("requested_limit"),
            "retrieval_llm_calls": provider_response.get("retrieval_llm_calls"),
        },
        "eval_dimensions": {
            "discovery": {
                "status": "complete" if discovery["complete_discovery"] else "incomplete",
                "required_document_recall": discovery["required_document_recall"],
                "document_precision": discovery["document_precision"],
                "wrong_documents_before_first_gold": discovery["wrong_documents_before_first_gold"],
            },
            "answer": {"status": "correct" if answer_ok else "incorrect", "expected_values_present": answer_ok},
            "attribution": {"status": "complete" if sources_ok else "incomplete", "required_sources_cited": sources_ok},
        },
        "answer": answer.answer,
        "cited_sources": list(answer.cited_sources),
        "opened_documents": document_order,
        "evidence_excerpts": _evidence_excerpts(knowledge, document_order, expected),
        "answer_contains_expected": answer_ok,
        "required_sources_cited": sources_ok,
        "answer_and_discovery": answer_and_discovery,
        "overall_success": overall,
        "failure_classification": _failure_classification(
            answer_ok=answer_ok,
            discovery=discovery,
            sources_ok=sources_ok,
            termination=answer.termination,
        ),
        "termination": answer.termination,
        "discovery": discovery,
        "read_trace": [
            {
                "action": "retrieve_document",
                "rank": rank,
                "document_id": doc_id,
                "content_characters": len(knowledge.read(doc_id).content),
            }
            for rank, doc_id in enumerate(document_order, start=1)
        ]
        + [{"action": "submit_answer", "sources": list(answer.cited_sources)}],
        "model_turns": answer.model_turns,
        "tool_calls": answer.tool_calls,
        "document_reads": len(document_order),
        "answer_attempts": 1 if answer.model_turns else 0,
        "selection_rounds": 0,
        "input_tokens": answer.usage.input_tokens,
        "output_tokens": answer.usage.output_tokens,
        "prompt_id": answerer.prompt.id,
        "prompt_version": answerer.prompt.version,
        "model_calls_to_complete_discovery": 0 if discovery["complete_discovery"] else None,
        "extra_model_calls_after_complete_discovery": 0 if discovery["complete_discovery"] else None,
        "model_call_overhead": float(answer.model_turns),
        "context": {
            "catalog_documents": len(catalog),
            "catalog_characters": knowledge.catalog_characters,
            "opened_document_characters": opened_chars,
            "retrieved_chunk_characters": opened_chars,
            "full_corpus_characters": full_chars,
            "knowledge_content_fraction_loaded": opened_chars / full_chars if full_chars else 0.0,
        },
        "retrieval": {
            "provider": backend_name,
            "retrieval_ms": retrieval_ms,
            "provider_version": provider_response.get("provider_version"),
            "provider_hit_count": len(normalized_hits),
            "mapped_unique_documents": len(document_order),
            "unresolved_provider_hits": unresolved,
            "provider_metadata": provider_response.get("metadata", {}),
            "raw_hits": mapped_hits,
        },
        "memory_snapshot": {
            "root": str(memory_root.relative_to(PROJECT_ROOT)),
            "sha256": _sha256_tree(memory_root),
        },
    }


def _marker_path(backend: str, corpus: str) -> Path:
    return _runtime_root(backend) / "markers" / f"{corpus}.json"


def _write_marker(backend: str, corpus: str, response: dict[str, Any]) -> None:
    path = _marker_path(backend, corpus)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "backend": backend,
        "corpus": corpus,
        "memory_sha256": _sha256_tree(_memory_root(backend, corpus)),
        "provider_version": response.get("provider_version"),
        "ingest": response,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate_marker(backend: str, corpus: str) -> dict[str, Any]:
    path = _marker_path(backend, corpus)
    if not path.is_file():
        raise RuntimeError(f"missing ingest marker {path}; run the ingest command first")
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = _sha256_tree(_memory_root(backend, corpus))
    if data.get("memory_sha256") != expected:
        raise RuntimeError(
            f"{backend}/{corpus} Markdown changed after ingestion; run ingest again before evaluating"
        )
    return data


def reset_runtime(backend: str) -> None:
    root = _runtime_root(backend)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def ingest_backend(backend: str, *, reset: bool) -> dict[str, Any]:
    config = _worker_config(backend)
    if not config.python.is_file():
        raise RuntimeError(f"missing backend environment: {config.python}; run scripts/bootstrap.sh")
    if reset:
        reset_runtime(backend)
    summaries: dict[str, Any] = {}
    with WorkerSession(config) as worker:
        for corpus in CORPORA:
            memory_root = _memory_root(backend, corpus)
            if not memory_root.is_dir():
                raise RuntimeError(f"missing {memory_root}; run prepare first")
            started = time.perf_counter()
            response = worker.request(
                {
                    "op": "ingest",
                    "corpus": corpus,
                    "memory_root": str(memory_root.resolve()),
                    "runtime_root": str(config.runtime_root.resolve()),
                }
            )
            response["harness_elapsed_seconds"] = time.perf_counter() - started
            _write_marker(backend, corpus, response)
            summaries[corpus] = response
            print(
                f"ingested {backend}/{corpus}: provider={response.get('provider_version')} "
                f"elapsed={response['harness_elapsed_seconds']:.1f}s"
            )
    ingest_path = config.runtime_root / "ingest-summary.json"
    ingest_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summaries


def _base_record(
    *, backend: str,
    dataset: dict[str, Any],
    corpus: str,
    case: dict[str, Any],
    model: str,
    prompt_path: Path,
    prompt: Any,
    memory_root: Path,
) -> dict[str, Any]:
    dataset_path = PROJECT_ROOT / DATASETS[corpus]
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_name": f"memory-system-{backend}",
        "retrieval_method": f"memory-{backend}",
        "dataset_name": dataset["name"],
        "dataset_version": dataset["version"],
        "corpus_name": corpus,
        "corpus_root": str(memory_root.relative_to(PROJECT_ROOT)),
        "repeat_index": 1,
        "case_id": case["id"],
        "case_title": case.get("title", ""),
        "tags": case.get("tags", []),
        "question": case["question"].strip(),
        "required_documents": case.get("required_documents", []),
        "expected_contains": [str(x) for x in case.get("expected_contains", [])],
        "model": model,
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "prompt_path": str(prompt_path),
        "prompt_sha256": _sha256_file(PROJECT_ROOT / prompt_path),
        "dataset_sha256": _sha256_file(dataset_path),
        "corpus_sha256": _sha256_tree(memory_root),
        "reasoning_effort": get_openai_reasoning_effort(),
        "text_verbosity": get_openai_text_verbosity(),
    }


def evaluate_backend(
    backend: str,
    *,
    output_root: Path,
    top_k_documents: int,
    provider_hit_limit: int,
    limit: int | None,
    case_ids: set[str] | None,
    tags: set[str] | None,
    quiet: bool,
) -> Path:
    config = _worker_config(backend)
    if not config.python.is_file():
        raise RuntimeError(f"missing backend environment: {config.python}; run scripts/bootstrap.sh")
    for corpus in CORPORA:
        _validate_marker(backend, corpus)

    model = _answer_model()
    prompt_path = DEFAULT_PROMPT
    prompt = load_prompt_artifact(PROJECT_ROOT / prompt_path)
    answer_backend = OpenAIResponsesBackend(
        model,
        reasoning_effort=get_openai_reasoning_effort(),
        text_verbosity=get_openai_text_verbosity(),
    )
    answerer = RagAnswerer(answer_backend, prompt=prompt)
    backend_output = output_root / backend
    backend_output.mkdir(parents=True, exist_ok=False)
    trials_path = backend_output / "trials.jsonl"

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "experiment_name": f"memory-system-{backend}",
        "backend": backend,
        "top_k_documents": top_k_documents,
        "provider_hit_limit": provider_hit_limit,
        "answer_model": model,
        "answer_prompt": str(prompt_path),
        "answer_prompt_sha256": _sha256_file(PROJECT_ROOT / prompt_path),
        "datasets": {corpus: str(DATASETS[corpus]) for corpus in CORPORA},
        "memory_snapshots": {
            corpus: {
                "path": str(_memory_root(backend, corpus).relative_to(PROJECT_ROOT)),
                "sha256": _sha256_tree(_memory_root(backend, corpus)),
            }
            for corpus in CORPORA
        },
        "ingest_markers": {
            corpus: json.loads(_marker_path(backend, corpus).read_text(encoding="utf-8"))
            for corpus in CORPORA
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (backend_output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    selected_by_corpus: dict[str, list[dict[str, Any]]] = {}
    total = 0
    for corpus in CORPORA:
        dataset = load_eval_dataset(PROJECT_ROOT / DATASETS[corpus])
        selected = select_cases(dataset["cases"], case_ids=case_ids, tags=tags, limit=limit)
        selected_by_corpus[corpus] = selected
        total += len(selected)
    if total == 0:
        raise RuntimeError("no benchmark cases selected")

    completed = 0
    with WorkerSession(config) as worker, trials_path.open("w", encoding="utf-8") as handle:
        for corpus in CORPORA:
            dataset = load_eval_dataset(PROJECT_ROOT / DATASETS[corpus])
            memory_root = _memory_root(backend, corpus)
            knowledge, catalog = _catalog(memory_root)
            for case in selected_by_corpus[corpus]:
                base = _base_record(
                    backend=backend,
                    dataset=dataset,
                    corpus=corpus,
                    case=case,
                    model=model,
                    prompt_path=prompt_path,
                    prompt=prompt,
                    memory_root=memory_root,
                )
                try:
                    provider = worker.request(
                        {
                            "op": "query",
                            "corpus": corpus,
                            "query": case["question"],
                            "limit": provider_hit_limit,
                            "memory_root": str(memory_root.resolve()),
                            "runtime_root": str(config.runtime_root.resolve()),
                        }
                    )
                    result = _evaluate_case(
                        backend_name=backend,
                        case=case,
                        corpus=corpus,
                        memory_root=memory_root,
                        provider_response=provider,
                        answerer=answerer,
                        knowledge=knowledge,
                        catalog=catalog,
                        top_k_documents=top_k_documents,
                    )
                    record = {**base, "status": "completed", "result": result}
                except Exception as exc:
                    record = {
                        **base,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                completed += 1
                if not quiet:
                    if record["status"] == "error":
                        outcome = f"ERROR {record['error_type']}: {record['error_message']}"
                    else:
                        result = record["result"]
                        outcome = (
                            "PASS"
                            if result.get("answer_and_discovery")
                            else f"FAIL answer={result.get('answer_contains_expected')} "
                            f"discovery={result.get('discovery', {}).get('complete_discovery')}"
                        )
                    print(f"[{completed}/{total}] {backend} {corpus} {case['id']} {outcome}")

    records = load_records([trials_path])
    write_aggregate(records, backend_output)
    _copy_runtime_logs(backend, backend_output)
    return trials_path


def _rate(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _summary_for(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in records if r.get("status") == "completed" and isinstance(r.get("result"), dict)]
    return {
        "trials": len(records),
        "completed": len(completed),
        "errors": len(records) - len(completed),
        "answer_accuracy": _rate([bool(r["result"].get("answer_contains_expected")) for r in completed]),
        "complete_discovery": _rate([
            bool(r["result"].get("discovery", {}).get("complete_discovery")) for r in completed
        ]),
        "answer_and_discovery": _rate([bool(r["result"].get("answer_and_discovery")) for r in completed]),
        "attribution": _rate([bool(r["result"].get("required_sources_cited")) for r in completed]),
        "mean_documents": _mean([float(r["result"].get("document_reads", 0)) for r in completed]),
        "mean_input_tokens": _mean([float(r["result"].get("input_tokens", 0)) for r in completed]),
        "mean_retrieval_ms": _mean([
            float(r["result"].get("retrieval", {}).get("retrieval_ms", 0.0)) for r in completed
        ]),
        "mean_unresolved_provider_hits": _mean([
            float(r["result"].get("retrieval", {}).get("unresolved_provider_hits", 0)) for r in completed
        ]),
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def _num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def write_comparison(output_root: Path, trial_files: list[Path]) -> tuple[Path, Path]:
    records = load_records(trial_files)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        backend = str(record.get("retrieval_method") or "unknown").removeprefix("memory-")
        groups[backend].append(record)

    summary: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "backends": {}}
    for backend, backend_records in sorted(groups.items()):
        single = [r for r in backend_records if "single_doc" in r.get("tags", [])]
        multi = [r for r in backend_records if "multi_doc" in r.get("tags", [])]
        by_corpus: dict[str, Any] = {}
        for corpus in CORPORA:
            corpus_records = [r for r in backend_records if r.get("corpus_name") == corpus]
            by_corpus[corpus] = {
                "overall": _summary_for(corpus_records),
                "single_doc": _summary_for([r for r in corpus_records if "single_doc" in r.get("tags", [])]),
                "multi_doc": _summary_for([r for r in corpus_records if "multi_doc" in r.get("tags", [])]),
            }
        summary["backends"][backend] = {
            "overall": _summary_for(backend_records),
            "single_doc": _summary_for(single),
            "multi_doc": _summary_for(multi),
            "by_corpus": by_corpus,
        }

    json_path = output_root / "comparison.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Memory-system comparison",
        "",
        "The primary cross-system metric is **Answer + discovery**: the shared answer grader passes and every evaluator-required document is present in the provider-ranked unique-document set. Attribution is reported separately.",
        "",
        "| Backend | Answer | Discovery | Answer + discovery | Attribution | Single-doc A+D | Multi-doc A+D | Mean docs | Retrieval ms | Unresolved hits |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for backend, data in sorted(summary["backends"].items()):
        overall = data["overall"]
        lines.append(
            "| " + " | ".join(
                [
                    backend,
                    _pct(overall["answer_accuracy"]),
                    _pct(overall["complete_discovery"]),
                    _pct(overall["answer_and_discovery"]),
                    _pct(overall["attribution"]),
                    _pct(data["single_doc"]["answer_and_discovery"]),
                    _pct(data["multi_doc"]["answer_and_discovery"]),
                    _num(overall["mean_documents"]),
                    _num(overall["mean_retrieval_ms"], 1),
                    _num(overall["mean_unresolved_provider_hits"]),
                ]
            ) + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Every backend is scored on the same Northstar + Tell Aster cases and the repository's deterministic answer matcher.",
            "- The final answer stage is the repository's existing `RagAnswerer` with `prompts/rag/system-v1.md` and `OPENAI_MODEL`.",
            "- Provider retrieval is mapped to unique source documents; the full Markdown body of each mapped document is supplied to the common answerer.",
            "- Provider ingestion cost and provider-internal model calls are not normalized because the three products expose different telemetry. Ingest wall time and raw provider metadata are preserved in manifests/markers.",
            "- Northstar and Tell Aster are development corpora, so this experiment compares behavior on the existing benchmark rather than establishing untouched generalization.",
        ]
    )
    md_path = output_root / "comparison.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _copy_runtime_logs(backend: str, destination: Path) -> None:
    runtime = _runtime_root(backend)
    if not runtime.is_dir():
        return
    log_root = destination / "runtime-logs"
    for source in sorted(runtime.rglob("*.log")):
        if not source.is_file():
            continue
        target = log_root / source.relative_to(runtime)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def doctor(backends: Iterable[str]) -> int:
    errors = 0
    print(f"project root: {PROJECT_ROOT}")
    print(f"experiment root: {EXPERIMENT_ROOT}")
    print(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL') or '<missing>'}")
    print(f"OPENAI_API_KEY: {'set' if os.getenv('OPENAI_API_KEY') else '<missing>'}")
    for corpus in CORPORA:
        spec = get_corpus_spec(corpus)
        root = PROJECT_ROOT / spec.root
        dataset = PROJECT_ROOT / DATASETS[corpus]
        print(f"{corpus}: corpus={'ok' if root.is_dir() else 'MISSING'} dataset={'ok' if dataset.is_file() else 'MISSING'}")
        if not root.is_dir() or not dataset.is_file():
            errors += 1
    for backend in backends:
        config = _worker_config(backend)
        print(
            f"{backend}: python={'ok' if config.python.is_file() else 'MISSING'} "
            f"worker={'ok' if config.worker.is_file() else 'MISSING'}"
        )
        if not config.python.is_file() or not config.worker.is_file():
            errors += 1
        else:
            try:
                with WorkerSession(config) as worker:
                    hello = worker.hello or {}
                    print(f"  provider-version: {hello.get('provider_version', 'unknown')}")
            except Exception as exc:
                print(f"  worker-start: ERROR {exc}")
                errors += 1
        for corpus in CORPORA:
            mem = _memory_root(backend, corpus)
            marker = _marker_path(backend, corpus)
            print(
                f"  {corpus}: memory={'ok' if mem.is_dir() and any(mem.rglob('*.md')) else 'not-prepared'} "
                f"ingest-marker={'ok' if marker.is_file() else 'not-ingested'}"
            )
    if not os.getenv("OPENAI_MODEL") or not os.getenv("OPENAI_API_KEY"):
        errors += 1
    return 0 if errors == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Basic Memory, OpenViking, and Hindsight on the existing 180-question benchmark."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_backend(p: argparse.ArgumentParser) -> None:
        p.add_argument("--backend", choices=("all",) + BACKENDS, default="all")

    p = sub.add_parser("doctor", help="Check repository, credentials, snapshots, and backend environments")
    add_backend(p)

    p = sub.add_parser("prepare", help="Copy current corpora into backend-specific Markdown memory roots")
    add_backend(p)
    p.add_argument("--reset-memory", action="store_true", help="Replace existing backend memory snapshots")

    p = sub.add_parser("ingest", help="Build each backend's derived/runtime memory state from its Markdown snapshot")
    add_backend(p)
    p.add_argument("--reset-runtime", action="store_true", help="Delete backend runtime/index state before ingest")

    p = sub.add_parser("eval", help="Run the existing questions through already-ingested memory systems")
    add_backend(p)
    p.add_argument("--top-k-documents", type=int, default=DEFAULT_TOP_K_DOCUMENTS)
    p.add_argument("--provider-hit-limit", type=int, default=DEFAULT_PROVIDER_HIT_LIMIT)
    p.add_argument("--limit", type=int, help="Per-corpus case limit for smoke tests")
    p.add_argument("--case", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--output", type=Path)
    p.add_argument("--quiet", action="store_true")

    p = sub.add_parser("all", help="Prepare, ingest, then evaluate in one command")
    add_backend(p)
    p.add_argument("--reset-memory", action="store_true")
    p.add_argument("--reset-runtime", action="store_true")
    p.add_argument("--top-k-documents", type=int, default=DEFAULT_TOP_K_DOCUMENTS)
    p.add_argument("--provider-hit-limit", type=int, default=DEFAULT_PROVIDER_HIT_LIMIT)
    p.add_argument("--limit", type=int, help="Per-corpus case limit for smoke tests")
    p.add_argument("--case", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--output", type=Path)
    p.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def _run_eval(args: argparse.Namespace, backends: tuple[str, ...]) -> Path:
    if args.top_k_documents < 1:
        raise ValueError("--top-k-documents must be >= 1")
    if args.provider_hit_limit < args.top_k_documents:
        raise ValueError("--provider-hit-limit must be >= --top-k-documents")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be >= 1")
    output_root = args.output or (EXPERIMENT_ROOT / "results" / _utc_stamp())
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite existing result directory: {output_root}")
    output_root.mkdir(parents=True)
    trial_files: list[Path] = []
    for backend in backends:
        trial_files.append(
            evaluate_backend(
                backend,
                output_root=output_root,
                top_k_documents=args.top_k_documents,
                provider_hit_limit=args.provider_hit_limit,
                limit=args.limit,
                case_ids=set(args.case) if args.case else None,
                tags=set(args.tag) if args.tag else None,
                quiet=args.quiet,
            )
        )
    if len(trial_files) > 1:
        write_aggregate(load_records(trial_files), output_root)
    comparison_json, comparison_md = write_comparison(output_root, trial_files)
    print(f"results: {output_root}")
    print(f"comparison: {comparison_md}")
    print(f"comparison json: {comparison_json}")
    return output_root


def main() -> int:
    load_project_env()
    args = _parse_args()
    backends = _selected_backends(args.backend)
    if args.command == "doctor":
        return doctor(backends)
    if args.command == "prepare":
        prepare_memories(backends, reset_memory=args.reset_memory)
        return 0
    if args.command == "ingest":
        for backend in backends:
            ingest_backend(backend, reset=args.reset_runtime)
        return 0
    if args.command == "eval":
        _run_eval(args, backends)
        return 0
    if args.command == "all":
        prepare_memories(backends, reset_memory=args.reset_memory)
        for backend in backends:
            ingest_backend(backend, reset=args.reset_runtime)
        _run_eval(args, backends)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
