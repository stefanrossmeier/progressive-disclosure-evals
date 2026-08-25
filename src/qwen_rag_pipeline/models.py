from __future__ import annotations

from dataclasses import dataclass

from rag_baseline.models import RagChunk


@dataclass(frozen=True)
class QwenDocumentRecord:
    id: str
    title: str
    description: str
    path: str
    search_text: str


@dataclass(frozen=True)
class QwenSearchResult:
    rank: int
    chunk: RagChunk
    score: float
    document_rank: int
    document_dense_rank: int | None = None
    document_lexical_rank: int | None = None
    chunk_dense_rank: int | None = None
    chunk_lexical_rank: int | None = None
    chunk_fusion_rank: int | None = None
    rerank_score: float | None = None
    within_document_rank: int | None = None
    selection_phase: str = ""
