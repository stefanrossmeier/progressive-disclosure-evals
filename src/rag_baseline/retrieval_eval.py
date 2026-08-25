from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.benchmark import load_eval_dataset, select_cases
from progressive_disclosure.knowledge import KnowledgeBase

from .evaluation import RagEvalPlan
from .index import load_index
from .retrieval import LocalRetriever


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def run_retrieval_eval(
    plan: RagEvalPlan,
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
    retriever = LocalRetriever(index, device=plan.device, offline=plan.offline)
    knowledge = KnowledgeBase(plan.corpus_root)
    full_chars = knowledge.full_content_characters
    records: list[dict[str, Any]] = []
    for case in cases:
        results = retriever.search(
            case["question"],
            strategy=plan.strategy,
            top_k=plan.top_k,
            max_chunks_per_document=plan.max_chunks_per_document,
            rrf_k=plan.rrf_k,
        )
        required = set(case.get("required_documents", []))
        documents = list(dict.fromkeys(result.chunk.document_id for result in results))
        retrieved = set(documents)
        recall = len(required & retrieved) / len(required) if required else 1.0
        precision = len(required & retrieved) / len(retrieved) if retrieved else (1.0 if not required else 0.0)
        first_required_rank = next(
            (result.rank for result in results if result.chunk.document_id in required),
            None,
        )
        chunk_chars = sum(len(result.chunk.text) for result in results)
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
    ranks = [float(record["first_required_chunk_rank"]) for record in records if record["first_required_chunk_rank"] is not None]
    summary = {
        "schema_version": 1,
        "experiment_name": plan.name,
        "retrieval_method": f"rag-{plan.strategy}",
        "corpus_name": plan.corpus_name,
        "dataset": str(plan.dataset),
        "cases": len(records),
        "complete_discovery_rate": sum(bool(record["complete_discovery"]) for record in records) / len(records),
        "mean_required_document_recall": statistics.fmean(recalls),
        "mean_document_precision": statistics.fmean(precisions),
        "mean_unique_documents": statistics.fmean(docs),
        "p95_unique_documents": _p95(docs),
        "mean_first_required_chunk_rank": statistics.fmean(ranks) if ranks else None,
        "mean_knowledge_content_fraction_loaded": statistics.fmean(fractions),
        "top_k": plan.top_k,
        "max_chunks_per_document": plan.max_chunks_per_document,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report = [
        f"# RAG retrieval-only report — {plan.strategy}",
        "",
        f"- Corpus: `{plan.corpus_name}`",
        f"- Dataset: `{plan.dataset}`",
        f"- Cases: {len(records)}",
        f"- Complete required-document discovery: **{100 * summary['complete_discovery_rate']:.1f}%**",
        f"- Mean required-document recall: **{100 * summary['mean_required_document_recall']:.1f}%**",
        f"- Mean document precision: **{100 * summary['mean_document_precision']:.1f}%**",
        f"- Mean unique documents represented: **{summary['mean_unique_documents']:.2f}**",
        f"- Mean corpus body fraction loaded: **{100 * summary['mean_knowledge_content_fraction_loaded']:.2f}%**",
        "",
        "This stage performs no answer-model calls; retrieval is fully local.",
    ]
    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary_path, report_path
