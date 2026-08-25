from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.benchmark import load_eval_dataset, select_cases
from evals.grading import answer_matches_expected
from progressive_disclosure.knowledge import KnowledgeBase

from .evaluation import QwenRagPlan
from .index import load_index
from .retrieval import QwenHierarchicalRetriever


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def run_retrieval_eval(
    plan: QwenRagPlan,
    *,
    output_dir: Path,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
) -> tuple[Path, Path]:
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
    knowledge = KnowledgeBase(plan.corpus_root)
    full_chars = knowledge.full_content_characters
    records: list[dict[str, Any]] = []
    for case in cases:
        results = retriever.search(case["question"])
        required = set(case.get("required_documents", []))
        documents = list(dict.fromkeys(result.chunk.document_id for result in results))
        retrieved = set(documents)
        recall = len(required & retrieved) / len(required) if required else 1.0
        precision = len(required & retrieved) / len(retrieved) if retrieved else (1.0 if not required else 0.0)
        first_required_rank = next((result.rank for result in results if result.chunk.document_id in required), None)
        chunk_chars = sum(len(result.chunk.text) for result in results)
        expected = tuple(str(value) for value in case.get("expected_contains", []))
        retrieved_evidence = "\n".join(result.chunk.text for result in results)
        evidence_coverage = answer_matches_expected(retrieved_evidence, expected, question=case["question"])
        records.append(
            {
                "case_id": case["id"],
                "tags": case.get("tags", []),
                "required_documents": sorted(required),
                "retrieved_documents": documents,
                "complete_discovery": recall == 1.0,
                "required_document_recall": recall,
                "document_precision": precision,
                "first_required_chunk_rank": first_required_rank,
                "retrieved_chunks": len(results),
                "retrieved_unique_documents": len(documents),
                "knowledge_content_fraction_loaded": chunk_chars / full_chars if full_chars else 0.0,
                "answer_evidence_coverage": evidence_coverage,
                "chunks": [
                    {
                        "rank": result.rank,
                        "chunk_id": result.chunk.id,
                        "document_id": result.chunk.document_id,
                        "document_rank": result.document_rank,
                        "rerank_score": result.rerank_score,
                        "within_document_rank": result.within_document_rank,
                        "selection_phase": result.selection_phase,
                    }
                    for result in results
                ],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "retrieval.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    recalls = [float(record["required_document_recall"]) for record in records]
    precisions = [float(record["document_precision"]) for record in records]
    docs = [float(record["retrieved_unique_documents"]) for record in records]
    fractions = [float(record["knowledge_content_fraction_loaded"]) for record in records]
    ranks = [
        float(record["first_required_chunk_rank"])
        for record in records
        if record["first_required_chunk_rank"] is not None
    ]
    evidence = [bool(record["answer_evidence_coverage"]) for record in records]
    summary = {
        "schema_version": 1,
        "experiment_name": plan.name,
        "retrieval_method": "qwen-hierarchical-hybrid",
        "corpus_name": plan.corpus_name,
        "dataset": str(plan.dataset),
        "cases": len(records),
        "complete_discovery_rate": sum(bool(record["complete_discovery"]) for record in records) / len(records),
        "mean_required_document_recall": statistics.fmean(recalls),
        "mean_document_precision": statistics.fmean(precisions),
        "answer_evidence_coverage_rate": sum(evidence) / len(evidence),
        "mean_unique_documents": statistics.fmean(docs),
        "p95_unique_documents": _p95(docs),
        "mean_first_required_chunk_rank": statistics.fmean(ranks) if ranks else None,
        "mean_knowledge_content_fraction_loaded": statistics.fmean(fractions),
        "top_k": plan.top_k,
        "document_candidates": plan.document_candidates,
        "chunk_candidates_per_document": plan.chunk_candidates_per_document,
        "unique_document_slots": plan.unique_document_slots,
        "rrf_k": plan.rrf_k,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Qwen hierarchical-hybrid RAG retrieval-only report",
        "",
        f"- Corpus: `{plan.corpus_name}`",
        f"- Dataset: `{plan.dataset}`",
        f"- Cases: {len(records)}",
        f"- Complete required-document discovery: **{100 * summary['complete_discovery_rate']:.1f}%**",
        f"- Mean required-document recall: **{100 * summary['mean_required_document_recall']:.1f}%**",
        f"- Mean document precision: **{100 * summary['mean_document_precision']:.1f}%**",
        f"- Retrieved-context answer-evidence coverage: **{100 * summary['answer_evidence_coverage_rate']:.1f}%**",
        f"- Mean unique documents represented: **{summary['mean_unique_documents']:.2f}**",
        f"- Mean corpus body fraction loaded: **{100 * summary['mean_knowledge_content_fraction_loaded']:.2f}%**",
        "",
        "This stage performs no answer-model calls; embedding, BM25, hierarchy, reranking, and packing are local.",
    ]
    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary_path, report_path
