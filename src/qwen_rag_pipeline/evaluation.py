from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from evals.aggregate import aggregate, load_records, write_aggregate
from evals.benchmark import load_eval_dataset, select_cases
from evals.grading import answer_matches_expected
from progressive_disclosure.config import get_openai_reasoning_effort, get_openai_text_verbosity
from progressive_disclosure.corpora import corpus_name_from_dataset, get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.llm import OpenAIResponsesBackend
from progressive_disclosure.prompts import load_prompt_artifact
from rag_baseline.answering import RagAnswerer

from .index import DEFAULT_INDEX_ROOT, index_dir_for, load_index
from .model_assets import DEFAULT_MODEL_ROOT
from .retrieval import DEFAULT_RERANK_INSTRUCTION, QwenHierarchicalRetriever


@dataclass(frozen=True)
class QwenRagPlan:
    name: str
    dataset: Path
    corpus_name: str
    corpus_root: Path
    index_dir: Path
    model_root: Path
    top_k: int
    document_candidates: int
    chunk_candidates_per_document: int
    unique_document_slots: int
    rrf_k: int
    rerank_batch_size: int
    rerank_instruction: str
    runs_per_case: int
    model: str
    prompt: Path
    case_ids: tuple[str, ...] = ()
    case_tags: tuple[str, ...] = ()
    device: str | None = None


def _resolve_env(value: str) -> str:
    if value.startswith("env:"):
        env_name = value.split(":", 1)[1]
        resolved = os.getenv(env_name)
        if not resolved:
            raise ValueError(f"environment variable is not set: {env_name}")
        return resolved
    return value


def load_plan(path: Path | str) -> QwenRagPlan:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Qwen RAG experiment config root must be a mapping")
    dataset_path = Path(data.get("dataset") or "datasets/eval-v1.yaml")
    dataset = load_eval_dataset(dataset_path)
    corpus_name = str(data.get("corpus") or corpus_name_from_dataset(dataset))
    spec = get_corpus_spec(corpus_name)
    plan = QwenRagPlan(
        name=str(data.get("name") or config_path.stem),
        dataset=dataset_path,
        corpus_name=corpus_name,
        corpus_root=Path(data.get("corpus_root") or spec.root),
        index_dir=Path(data.get("index_dir") or index_dir_for(corpus_name)),
        model_root=Path(data.get("model_root") or DEFAULT_MODEL_ROOT),
        top_k=int(data.get("top_k", 8)),
        document_candidates=int(data.get("document_candidates", 12)),
        chunk_candidates_per_document=int(data.get("chunk_candidates_per_document", 4)),
        unique_document_slots=int(data.get("unique_document_slots", 5)),
        rrf_k=int(data.get("rrf_k", 60)),
        rerank_batch_size=int(data.get("rerank_batch_size", 8)),
        rerank_instruction=str(data.get("rerank_instruction") or DEFAULT_RERANK_INSTRUCTION),
        runs_per_case=int(data.get("runs_per_case", 1)),
        model=str(data.get("model") or "env:OPENAI_MODEL"),
        prompt=Path(data.get("prompt") or "prompts/rag/system-v1.md"),
        case_ids=tuple(str(item) for item in data.get("case_ids", [])),
        case_tags=tuple(str(item) for item in data.get("case_tags", [])),
        device=str(data["device"]) if data.get("device") else None,
    )
    numeric = (
        plan.top_k,
        plan.document_candidates,
        plan.chunk_candidates_per_document,
        plan.unique_document_slots,
        plan.rrf_k,
        plan.rerank_batch_size,
        plan.runs_per_case,
    )
    if min(numeric) < 1:
        raise ValueError("Qwen RAG numeric settings must be >= 1")
    if plan.unique_document_slots > plan.top_k:
        raise ValueError("unique_document_slots must be <= top_k")
    return plan


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


def evaluate_case(
    case: dict[str, Any],
    *,
    retriever: QwenHierarchicalRetriever,
    answerer: RagAnswerer,
    knowledge: KnowledgeBase,
) -> dict[str, Any]:
    started = time.perf_counter()
    results = retriever.search(case["question"])
    retrieval_ms = (time.perf_counter() - started) * 1000.0
    answer = answerer.answer(case["question"], results)

    required = set(case.get("required_documents", []))
    expected = tuple(str(value) for value in case.get("expected_contains", []))
    documents = _unique_document_order(results)
    discovery = _discovery(documents, required)
    answer_ok = answer_matches_expected(answer.answer, expected, question=case["question"])
    sources_ok = required.issubset(set(answer.cited_sources))
    comparable_success = answer.termination == "answer" and answer_ok and discovery["complete_discovery"]
    citation_strict_success = comparable_success and sources_ok

    retrieved_chars = sum(len(result.chunk.text) for result in results)
    full_chars = knowledge.full_content_characters
    retrieved_evidence = "\n".join(result.chunk.text for result in results)
    evidence_coverage = answer_matches_expected(retrieved_evidence, expected, question=case["question"])

    read_trace = [
        {
            "action": "retrieve_chunk",
            "rank": result.rank,
            "chunk_id": result.chunk.id,
            "document_id": result.chunk.document_id,
            "score": result.score,
            "document_rank": result.document_rank,
            "document_dense_rank": result.document_dense_rank,
            "document_lexical_rank": result.document_lexical_rank,
            "chunk_dense_rank": result.chunk_dense_rank,
            "chunk_lexical_rank": result.chunk_lexical_rank,
            "chunk_fusion_rank": result.chunk_fusion_rank,
            "rerank_score": result.rerank_score,
            "within_document_rank": result.within_document_rank,
            "selection_phase": result.selection_phase,
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
            "required_documents": sorted(required),
            "ideal_model_calls": 1,
            "gold_visible_to_agent": False,
            "answer_rule": "Same deterministic answer matcher as progressive disclosure and existing RAG.",
            "discovery_rule": "Every required document must be represented by at least one retrieved chunk.",
            "comparable_rule": "Answer correct AND all required documents retrieved.",
            "citation_strict_rule": "Comparable success AND all required documents explicitly cited by the answer call.",
        },
        "runtime_policy": {
            "mechanism": "local_qwen_hierarchical_hybrid_rag_then_one_answer_call",
            "embedding_repo": retriever.index.manifest.embedding_repo,
            "embedding_revision": retriever.index.manifest.embedding_revision,
            "top_k": retriever.top_k,
            "document_candidates": retriever.document_candidates,
            "chunk_candidates_per_document": retriever.chunk_candidates_per_document,
            "unique_document_slots": retriever.unique_document_slots,
            "rrf_k": retriever.rrf_k,
            "reranker_repo": "Qwen/Qwen3-Reranker-0.6B",
            "rerank_instruction": retriever.rerank_instruction,
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
        "answer_evidence_coverage": evidence_coverage,
        "required_sources_cited": sources_ok,
        "comparable_success": comparable_success,
        "overall_success": citation_strict_success,
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
            "strategy": "qwen_hierarchical_hybrid",
            "top_k": retriever.top_k,
            "retrieved_chunks": len(results),
            "retrieved_unique_documents": len(documents),
            "retrieval_ms": retrieval_ms,
            "answer_evidence_coverage": evidence_coverage,
            "chunks": [
                {
                    "rank": result.rank,
                    "chunk_id": result.chunk.id,
                    "document_id": result.chunk.document_id,
                    "document_rank": result.document_rank,
                    "chunk_dense_rank": result.chunk_dense_rank,
                    "chunk_lexical_rank": result.chunk_lexical_rank,
                    "chunk_fusion_rank": result.chunk_fusion_rank,
                    "rerank_score": result.rerank_score,
                    "within_document_rank": result.within_document_rank,
                    "selection_phase": result.selection_phase,
                }
                for result in results
            ],
        },
    }


def default_output_dir(name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("results") / f"{stamp}-{name}"


def run_benchmark(
    plan: QwenRagPlan,
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
    cases = select_cases(dataset["cases"], case_ids=effective_ids, tags=effective_tags or None, limit=limit)
    if not cases:
        raise ValueError("case selection is empty")

    index = load_index(plan.index_dir, verify_corpus=True)
    retriever = QwenHierarchicalRetriever(
        index,
        model_root=str(plan.model_root),
        device=plan.device,
        document_candidates=plan.document_candidates,
        chunk_candidates_per_document=plan.chunk_candidates_per_document,
        top_k=plan.top_k,
        unique_document_slots=plan.unique_document_slots,
        rrf_k=plan.rrf_k,
        rerank_batch_size=plan.rerank_batch_size,
        rerank_instruction=plan.rerank_instruction,
    )
    resolved_model = _resolve_env(plan.model)
    backend = OpenAIResponsesBackend(
        model=resolved_model,
        reasoning_effort=get_openai_reasoning_effort(),
        text_verbosity=get_openai_text_verbosity(),
    )
    prompt = load_prompt_artifact(plan.prompt)
    answerer = RagAnswerer(backend, prompt=prompt)
    knowledge = KnowledgeBase(plan.corpus_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    trials_path = output_dir / "trials.jsonl"
    total = len(cases) * plan.runs_per_case
    completed = 0
    with trials_path.open("w", encoding="utf-8") as handle:
        for repeat_index in range(1, plan.runs_per_case + 1):
            for case in cases:
                base = {
                    "schema_version": 1,
                    "experiment_name": plan.name,
                    "retrieval_method": "qwen-hierarchical-hybrid",
                    "dataset_path": str(plan.dataset),
                    "dataset_sha256": _sha256_file(plan.dataset),
                    "corpus_name": plan.corpus_name,
                    "corpus_root": str(plan.corpus_root),
                    "corpus_sha256": index.manifest.corpus_sha256,
                    "repeat_index": repeat_index,
                    "case_id": case["id"],
                    "model": resolved_model,
                    "embedding_model": index.manifest.embedding_repo,
                    "reasoning_effort": backend.reasoning_effort,
                    "text_verbosity": backend.text_verbosity,
                }
                try:
                    result = evaluate_case(case, retriever=retriever, answerer=answerer, knowledge=knowledge)
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
                        message = str(record.get("error_message") or "").replace("\n", " ")
                        if len(message) > 240:
                            message = message[:237] + "..."
                        outcome = f"ERROR {record.get('error_type', 'Error')}: {message}"
                    else:
                        outcome = "PASS" if record["result"].get("comparable_success") else "FAIL"
                    print(
                        f"[{completed}/{total}] qwen-rag {resolved_model} repeat={repeat_index} "
                        f"{case['id']} {outcome}"
                    )
    return trials_path


def write_aggregate_report(trials: Path, output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    records = load_records([trials])
    summary = aggregate(records)
    summary_path, report_path = write_aggregate(records, output_dir)
    comparable = [
        bool(record.get("result", {}).get("comparable_success"))
        for record in records
        if record.get("status") == "completed"
    ]
    coverage = [
        bool(record.get("result", {}).get("answer_evidence_coverage"))
        for record in records
        if record.get("status") == "completed"
    ]
    summary["qwen_rag"] = {
        "comparable_success_rate": sum(comparable) / len(comparable) if comparable else None,
        "answer_evidence_coverage_rate": sum(coverage) / len(coverage) if coverage else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n## Qwen RAG comparison metrics\n\n")
        if comparable:
            handle.write(f"- Answer + complete discovery: **{100 * sum(comparable) / len(comparable):.1f}%**\n")
        if coverage:
            handle.write(f"- Retrieved-context answer-evidence coverage: **{100 * sum(coverage) / len(coverage):.1f}%**\n")
        handle.write("- The aggregate report's normal overall-success metric remains citation-strict for compatibility.\n")
    return summary_path, report_path, summary
