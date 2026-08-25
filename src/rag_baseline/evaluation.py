from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from evals.aggregate import aggregate, load_records, write_aggregate
from evals.benchmark import load_eval_dataset, select_cases
from evals.grading import answer_matches_expected
from progressive_disclosure.config import (
    get_openai_reasoning_effort,
    get_openai_text_verbosity,
)
from progressive_disclosure.corpora import corpus_name_from_dataset, get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.llm import OpenAIResponsesBackend
from progressive_disclosure.prompts import load_prompt_artifact

from .answering import RagAnswerer
from .index import corpus_sha256, index_dir_for, load_index
from .retrieval import LocalRetriever


@dataclass(frozen=True)
class RagEvalPlan:
    name: str
    dataset: Path
    corpus_name: str
    corpus_root: Path
    index_dir: Path
    strategy: str
    top_k: int
    max_chunks_per_document: int
    rrf_k: int
    runs_per_case: int
    model: str
    prompt: Path
    case_ids: tuple[str, ...] = ()
    case_tags: tuple[str, ...] = ()
    device: str | None = None
    offline: bool = False


def _resolve_env(value: str) -> str:
    if value.startswith("env:"):
        env_name = value.split(":", 1)[1]
        resolved = os.getenv(env_name)
        if not resolved:
            raise ValueError(f"environment variable is not set: {env_name}")
        return resolved
    return value


def load_rag_plan(path: Path | str) -> RagEvalPlan:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("RAG experiment config root must be a mapping")
    dataset_path = Path(data.get("dataset") or "datasets/eval-v1.yaml")
    dataset = load_eval_dataset(dataset_path)
    corpus_name = str(data.get("corpus") or corpus_name_from_dataset(dataset))
    spec = get_corpus_spec(corpus_name)
    corpus_root = Path(data.get("corpus_root") or spec.root)
    strategy = str(data.get("strategy") or "dense")
    if strategy not in {"dense", "hybrid"}:
        raise ValueError("RAG strategy must be 'dense' or 'hybrid'")
    top_k = int(data.get("top_k", 6))
    max_per_doc = int(data.get("max_chunks_per_document", 2))
    rrf_k = int(data.get("rrf_k", 60))
    runs = int(data.get("runs_per_case", 1))
    if min(top_k, max_per_doc, rrf_k, runs) < 1:
        raise ValueError("top_k, max_chunks_per_document, rrf_k, and runs_per_case must be >= 1")
    model = str(data.get("model") or "env:OPENAI_MODEL")
    prompt = Path(data.get("prompt") or "prompts/rag/system-v1.md")
    return RagEvalPlan(
        name=str(data.get("name") or config_path.stem),
        dataset=dataset_path,
        corpus_name=corpus_name,
        corpus_root=corpus_root,
        index_dir=Path(data.get("index_dir") or index_dir_for(corpus_name)),
        strategy=strategy,
        top_k=top_k,
        max_chunks_per_document=max_per_doc,
        rrf_k=rrf_k,
        runs_per_case=runs,
        model=model,
        prompt=prompt,
        case_ids=tuple(str(x) for x in data.get("case_ids", [])),
        case_tags=tuple(str(x) for x in data.get("case_tags", [])),
        device=str(data["device"]) if data.get("device") else None,
        offline=bool(data.get("offline", False)),
    )


def _sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _unique_document_order(results) -> tuple[str, ...]:
    return tuple(dict.fromkeys(result.chunk.document_id for result in results))


def _discovery(read_order: tuple[str, ...], required: set[str]) -> dict[str, Any]:
    read_set = set(read_order)
    matched = read_set & required
    recall = len(matched) / len(required) if required else 1.0
    precision = len(matched) / len(read_set) if read_set else (1.0 if not required else 0.0)
    first_gold = next((i for i, doc_id in enumerate(read_order) if doc_id in required), None)
    complete_at: int | None = 0 if not required else None
    seen: set[str] = set()
    for index, doc_id in enumerate(read_order, start=1):
        if doc_id in required:
            seen.add(doc_id)
        if required and seen == required:
            complete_at = index
            break
    return {
        "document_reads": len(read_order),
        "required_document_recall": recall,
        "document_precision": precision,
        "wrong_documents_before_first_gold": first_gold if first_gold is not None else len(read_order),
        "reads_to_complete_discovery": complete_at,
        "reads_after_complete_discovery": len(read_order) - complete_at if complete_at is not None else None,
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


def _evidence_excerpts(results, expected: tuple[str, ...]) -> dict[str, list[str]]:
    folded = [value.casefold() for value in expected]
    excerpts: dict[str, list[str]] = {}
    for result in results:
        lines = [line.strip() for line in result.chunk.text.splitlines() if line.strip()]
        matches = [line for line in lines if any(value in line.casefold() for value in folded)]
        if matches:
            excerpts.setdefault(result.chunk.document_id, []).extend(matches[:5])
    return {key: value[:10] for key, value in excerpts.items()}


def evaluate_rag_case(
    case: dict[str, Any],
    *,
    retriever: LocalRetriever,
    answerer: RagAnswerer,
    strategy: str,
    top_k: int,
    max_chunks_per_document: int,
    rrf_k: int,
    knowledge: KnowledgeBase,
) -> dict[str, Any]:
    started = time.perf_counter()
    results = retriever.search(
        case["question"],
        strategy=strategy,
        top_k=top_k,
        max_chunks_per_document=max_chunks_per_document,
        rrf_k=rrf_k,
    )
    retrieval_ms = (time.perf_counter() - started) * 1000.0
    answer = answerer.answer(case["question"], results)

    required = set(case.get("required_documents", []))
    expected = tuple(str(value) for value in case.get("expected_contains", []))
    documents = _unique_document_order(results)
    discovery = _discovery(documents, required)
    answer_ok = answer_matches_expected(answer.answer, expected, question=case["question"])
    sources_ok = required.issubset(set(answer.cited_sources))
    overall = answer.termination == "answer" and answer_ok and discovery["complete_discovery"] and sources_ok

    retrieved_chars = sum(len(result.chunk.text) for result in results)
    full_chars = knowledge.full_content_characters
    read_trace = [
        {
            "action": "retrieve_chunk",
            "rank": result.rank,
            "chunk_id": result.chunk.id,
            "document_id": result.chunk.document_id,
            "score": result.score,
            "dense_rank": result.dense_rank,
            "lexical_rank": result.lexical_rank,
            "content_characters": len(result.chunk.text),
        }
        for result in results
    ]
    read_trace.append(
        {
            "action": "submit_answer" if answer.termination == "answer" else answer.termination,
            "sources": list(answer.cited_sources),
        }
    )

    return {
        "case_id": case["id"],
        "question": case["question"].strip(),
        "eval_criteria": {
            "expected_answer_values": list(expected),
            "required_documents": list(required),
            "ideal_model_calls": 1,
            "gold_visible_to_agent": False,
            "answer_rule": "Same deterministic answer matcher as progressive disclosure.",
            "discovery_rule": "Every required document must be represented by at least one retrieved chunk.",
            "source_rule": "The answer must cite all required documents.",
            "overall_rule": "Answer correct AND all required documents retrieved AND all required documents cited.",
        },
        "runtime_policy": {
            "mechanism": f"local_{strategy}_rag_then_one_answer_call",
            "embedding_model": retriever.index.manifest.embedding_model,
            "top_k": top_k,
            "max_chunks_per_document": max_chunks_per_document,
            "rrf_k": rrf_k if strategy == "hybrid" else None,
            "retrieval_llm_calls": 0,
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
        "opened_documents": list(documents),
        "evidence_excerpts": _evidence_excerpts(results, expected),
        "answer_contains_expected": answer_ok,
        "required_sources_cited": sources_ok,
        "overall_success": overall,
        "failure_classification": _failure_classification(
            answer_ok=answer_ok,
            discovery=discovery,
            sources_ok=sources_ok,
            termination=answer.termination,
        ),
        "termination": answer.termination,
        "discovery": discovery,
        "read_trace": read_trace,
        "model_turns": answer.model_turns,
        "tool_calls": answer.tool_calls,
        "document_reads": len(documents),
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
            "catalog_documents": 0,
            "catalog_characters": 0,
            "opened_document_characters": retrieved_chars,
            "retrieved_chunk_characters": retrieved_chars,
            "full_corpus_characters": full_chars,
            "knowledge_content_fraction_loaded": retrieved_chars / full_chars if full_chars else 0.0,
        },
        "retrieval": {
            "strategy": strategy,
            "top_k": top_k,
            "retrieved_chunks": len(results),
            "retrieved_unique_documents": len(documents),
            "retrieval_ms": retrieval_ms,
            "chunks": [
                {
                    "rank": result.rank,
                    "chunk_id": result.chunk.id,
                    "document_id": result.chunk.document_id,
                    "score": result.score,
                    "dense_rank": result.dense_rank,
                    "lexical_rank": result.lexical_rank,
                }
                for result in results
            ],
        },
    }


def default_output_dir(name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("results") / f"{stamp}-{name}"


def run_rag_benchmark(
    plan: RagEvalPlan,
    *,
    output_dir: Path,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
    quiet: bool = False,
) -> Path:
    dataset = load_eval_dataset(plan.dataset)
    configured_ids = set(plan.case_ids) or None
    effective_ids = configured_ids
    if case_ids is not None:
        effective_ids = case_ids if configured_ids is None else configured_ids & case_ids
    effective_tags = set(plan.case_tags)
    if tags:
        effective_tags.update(tags)
    cases = select_cases(
        dataset["cases"],
        case_ids=effective_ids,
        tags=effective_tags or None,
        limit=limit,
    )
    if not cases:
        raise ValueError("case selection is empty")

    index = load_index(plan.index_dir, verify_corpus=True)
    if index.manifest.corpus_name != plan.corpus_name:
        raise ValueError(
            f"RAG index corpus {index.manifest.corpus_name!r} does not match plan corpus {plan.corpus_name!r}"
        )
    prompt = load_prompt_artifact(plan.prompt)
    knowledge = KnowledgeBase(plan.corpus_root)
    retriever = LocalRetriever(index, device=plan.device, offline=plan.offline)
    resolved_model = _resolve_env(plan.model)
    backend = OpenAIResponsesBackend(
        resolved_model,
        reasoning_effort=get_openai_reasoning_effort(),
        text_verbosity=get_openai_text_verbosity(),
    )
    answerer = RagAnswerer(backend, prompt=prompt)

    output_dir.mkdir(parents=True, exist_ok=True)
    trials_path = output_dir / "trials.jsonl"
    if trials_path.exists() and trials_path.stat().st_size > 0:
        raise FileExistsError(f"refusing to append to existing RAG results: {trials_path}")
    dataset_hash = _sha256_file(plan.dataset)
    corpus_hash = corpus_sha256(plan.corpus_root)
    prompt_hash = _sha256_file(plan.prompt)
    index_manifest_hash = _sha256_file(plan.index_dir / "manifest.json")
    manifest = {
        "schema_version": 1,
        "experiment_name": plan.name,
        "retrieval_method": f"rag-{plan.strategy}",
        "dataset": str(plan.dataset),
        "dataset_name": dataset["name"],
        "dataset_version": dataset["version"],
        "corpus_name": plan.corpus_name,
        "corpus_root": str(plan.corpus_root),
        "dataset_sha256": dataset_hash,
        "corpus_sha256": corpus_hash,
        "index_dir": str(plan.index_dir),
        "index_manifest_sha256": index_manifest_hash,
        "embedding_model": index.manifest.embedding_model,
        "strategy": plan.strategy,
        "top_k": plan.top_k,
        "max_chunks_per_document": plan.max_chunks_per_document,
        "rrf_k": plan.rrf_k if plan.strategy == "hybrid" else None,
        "runs_per_case": plan.runs_per_case,
        "model": resolved_model,
        "prompt": str(plan.prompt),
        "prompt_sha256": prompt_hash,
        "selected_cases": [case["id"] for case in cases],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    total = len(cases) * plan.runs_per_case
    completed = 0
    with trials_path.open("w", encoding="utf-8") as handle:
        for repeat_index in range(1, plan.runs_per_case + 1):
            for case in cases:
                base = {
                    "schema_version": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "experiment_name": plan.name,
                    "retrieval_method": f"rag-{plan.strategy}",
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
                    "model": resolved_model,
                    "prompt_id": prompt.id,
                    "prompt_version": prompt.version,
                    "prompt_path": str(plan.prompt),
                    "prompt_sha256": prompt_hash,
                    "dataset_sha256": dataset_hash,
                    "corpus_sha256": corpus_hash,
                    "index_manifest_sha256": index_manifest_hash,
                    "embedding_model": index.manifest.embedding_model,
                    "reasoning_effort": backend.reasoning_effort,
                    "text_verbosity": backend.text_verbosity,
                }
                try:
                    result = evaluate_rag_case(
                        case,
                        retriever=retriever,
                        answerer=answerer,
                        strategy=plan.strategy,
                        top_k=plan.top_k,
                        max_chunks_per_document=plan.max_chunks_per_document,
                        rrf_k=plan.rrf_k,
                        knowledge=knowledge,
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
                        error_message = str(record.get("error_message") or "").replace("\n", " ")
                        if len(error_message) > 240:
                            error_message = error_message[:237] + "..."
                        outcome = f"ERROR {record.get('error_type', 'Error')}: {error_message}"
                    else:
                        outcome = "PASS" if record["result"].get("overall_success") else "FAIL"
                    print(
                        f"[{completed}/{total}] rag-{plan.strategy} {resolved_model} "
                        f"repeat={repeat_index} {case['id']} {outcome}"
                    )
    return trials_path


def write_rag_aggregate(trials: Path, output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    records = load_records([trials])
    summary = aggregate(records)
    summary_path, report_path = write_aggregate(records, output_dir)
    return summary_path, report_path, summary
