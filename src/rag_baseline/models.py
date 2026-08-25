from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagChunk:
    id: str
    document_id: str
    title: str
    description: str
    path: str
    heading: str
    text: str
    search_text: str


@dataclass(frozen=True)
class RagSearchResult:
    rank: int
    chunk: RagChunk
    score: float
    dense_rank: int | None = None
    lexical_rank: int | None = None
