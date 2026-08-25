from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from .index import LoadedRagIndex, _sentence_transformer
from .models import RagSearchResult
from .reranking import DEFAULT_RERANKER_MODEL, LocalCrossEncoderReranker


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*")


def lexical_tokens(text: str) -> list[str]:
    """BM25 tokenizer that deliberately preserves identifiers such as TA-EXC-06."""

    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class Bm25Index:
    tokenized_documents: tuple[tuple[str, ...], ...]
    k1: float = 1.5
    b: float = 0.75

    def __post_init__(self) -> None:
        if not self.tokenized_documents:
            raise ValueError("BM25 requires at least one document")
        if self.k1 <= 0:
            raise ValueError("BM25 k1 must be > 0")
        if not 0 <= self.b <= 1:
            raise ValueError("BM25 b must be between 0 and 1")
        lengths = tuple(len(document) for document in self.tokenized_documents)
        object.__setattr__(self, "_lengths", lengths)
        object.__setattr__(self, "_avgdl", sum(lengths) / len(lengths))
        term_frequencies = tuple(Counter(document) for document in self.tokenized_documents)
        object.__setattr__(self, "_term_frequencies", term_frequencies)
        doc_frequency: Counter[str] = Counter()
        for document in self.tokenized_documents:
            doc_frequency.update(set(document))
        n = len(self.tokenized_documents)
        idf = {
            term: math.log(1.0 + (n - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in doc_frequency.items()
        }
        object.__setattr__(self, "_idf", idf)

    def scores(self, query_tokens: list[str]) -> list[float]:
        query_terms = Counter(query_tokens)
        result = [0.0] * len(self.tokenized_documents)
        for index, frequencies in enumerate(self._term_frequencies):
            document_length = self._lengths[index]
            norm = self.k1 * (1.0 - self.b + self.b * document_length / (self._avgdl or 1.0))
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                idf = self._idf.get(term, 0.0)
                score += query_frequency * idf * (frequency * (self.k1 + 1.0)) / (frequency + norm)
            result[index] = score
        return result


def reciprocal_rank_fusion(
    dense_order: Iterable[int],
    lexical_order: Iterable[int],
    *,
    rrf_k: int = 60,
) -> dict[int, float]:
    if rrf_k < 1:
        raise ValueError("rrf_k must be >= 1")
    scores: dict[int, float] = {}
    for order in (dense_order, lexical_order):
        for rank, index in enumerate(order, start=1):
            scores[index] = scores.get(index, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def _rank_map(order: list[int]) -> dict[int, int]:
    return {index: rank for rank, index in enumerate(order, start=1)}


def _cap_per_document(order: Iterable[int], index: LoadedRagIndex, *, top_k: int, max_per_doc: int) -> list[int]:
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if max_per_doc < 1:
        raise ValueError("max_chunks_per_document must be >= 1")
    selected: list[int] = []
    counts: dict[str, int] = {}
    for chunk_index in order:
        doc_id = index.chunks[chunk_index].document_id
        if counts.get(doc_id, 0) >= max_per_doc:
            continue
        selected.append(chunk_index)
        counts[doc_id] = counts.get(doc_id, 0) + 1
        if len(selected) >= top_k:
            break
    return selected


@dataclass
class LocalRetriever:
    index: LoadedRagIndex
    device: str | None = None
    offline: bool = False
    reranker_model: str = DEFAULT_RERANKER_MODEL
    rerank_batch_size: int = 16

    def __post_init__(self) -> None:
        self._encoder: Any | None = None
        self._bm25: Any | None = None
        self._tokenized_corpus: list[list[str]] | None = None
        self._reranker: LocalCrossEncoderReranker | None = None

    @property
    def encoder(self):
        if self._encoder is None:
            self._encoder = _sentence_transformer(
                self.index.manifest.embedding_model,
                device=self.device,
                offline=self.offline,
            )
        return self._encoder

    @property
    def bm25(self) -> Bm25Index:
        if self._bm25 is None:
            self._tokenized_corpus = [lexical_tokens(chunk.search_text) for chunk in self.index.chunks]
            self._bm25 = Bm25Index(tuple(tuple(tokens) for tokens in self._tokenized_corpus))
        return self._bm25

    @property
    def reranker(self) -> LocalCrossEncoderReranker:
        if self._reranker is None:
            self._reranker = LocalCrossEncoderReranker(
                model_name=self.reranker_model,
                device=self.device,
                offline=self.offline,
                batch_size=self.rerank_batch_size,
            )
        return self._reranker

    def _query_vector(self, question: str):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional install
            raise RuntimeError(
                "local RAG requires numpy; install with: pip install -r requirements-rag.txt"
            ) from exc
        query = f"{self.index.manifest.query_prefix}{question.strip()}"
        vector = self.encoder.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(vector[0], dtype=np.float32)

    def _hybrid_components(self, question: str, *, rrf_k: int):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional install
            raise RuntimeError(
                "local RAG requires numpy; install with: pip install -r requirements-rag.txt"
            ) from exc
        vector = self._query_vector(question)
        dense_scores = self.index.embeddings @ vector
        dense_order = np.argsort(-dense_scores, kind="stable").tolist()
        lexical_scores = np.asarray(self.bm25.scores(lexical_tokens(question)), dtype=np.float32)
        lexical_order = np.argsort(-lexical_scores, kind="stable").tolist()
        fused = reciprocal_rank_fusion(dense_order, lexical_order, rrf_k=rrf_k)
        fused_order = sorted(fused, key=lambda idx: (-fused[idx], idx))
        return dense_order, lexical_order, fused, fused_order

    def dense(
        self,
        question: str,
        *,
        top_k: int = 6,
        max_chunks_per_document: int = 2,
    ) -> list[RagSearchResult]:
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional install
            raise RuntimeError(
                "local RAG requires numpy; install with: pip install -r requirements-rag.txt"
            ) from exc
        vector = self._query_vector(question)
        scores = self.index.embeddings @ vector
        order = np.argsort(-scores, kind="stable").tolist()
        selected = _cap_per_document(
            order,
            self.index,
            top_k=top_k,
            max_per_doc=max_chunks_per_document,
        )
        ranks = _rank_map(order)
        return [
            RagSearchResult(
                rank=rank,
                chunk=self.index.chunks[chunk_index],
                score=float(scores[chunk_index]),
                dense_rank=ranks[chunk_index],
            )
            for rank, chunk_index in enumerate(selected, start=1)
        ]

    def hybrid(
        self,
        question: str,
        *,
        top_k: int = 6,
        max_chunks_per_document: int = 2,
        rrf_k: int = 60,
    ) -> list[RagSearchResult]:
        dense_order, lexical_order, fused, fused_order = self._hybrid_components(question, rrf_k=rrf_k)
        selected = _cap_per_document(
            fused_order,
            self.index,
            top_k=top_k,
            max_per_doc=max_chunks_per_document,
        )
        dense_ranks = _rank_map(dense_order)
        lexical_ranks = _rank_map(lexical_order)
        fusion_ranks = _rank_map(fused_order)
        return [
            RagSearchResult(
                rank=rank,
                chunk=self.index.chunks[chunk_index],
                score=float(fused[chunk_index]),
                dense_rank=dense_ranks[chunk_index],
                lexical_rank=lexical_ranks[chunk_index],
                fusion_rank=fusion_ranks[chunk_index],
                fusion_score=float(fused[chunk_index]),
            )
            for rank, chunk_index in enumerate(selected, start=1)
        ]

    def hybrid_rerank(
        self,
        question: str,
        *,
        top_k: int = 6,
        max_chunks_per_document: int = 2,
        rrf_k: int = 60,
        candidate_k: int = 24,
        candidate_max_chunks_per_document: int = 4,
    ) -> list[RagSearchResult]:
        """Generate broad hybrid candidates, then rerank locally with a cross-encoder.

        Candidate generation remains cheap and high-recall (dense + BM25 + RRF).
        The cross-encoder sees only the bounded candidate set and decides which
        chunks are most relevant to the full question before answer context is
        assembled. Both stages are local; the answer model call remains unchanged.
        """

        if candidate_k < top_k:
            raise ValueError("candidate_k must be >= top_k")
        if candidate_max_chunks_per_document < max_chunks_per_document:
            raise ValueError(
                "candidate_max_chunks_per_document must be >= max_chunks_per_document"
            )
        dense_order, lexical_order, fused, fused_order = self._hybrid_components(question, rrf_k=rrf_k)
        candidates = _cap_per_document(
            fused_order,
            self.index,
            top_k=candidate_k,
            max_per_doc=candidate_max_chunks_per_document,
        )
        chunks = [self.index.chunks[index] for index in candidates]
        rerank_scores = self.reranker.scores(question, chunks)
        rerank_by_index = {index: rerank_scores[pos] for pos, index in enumerate(candidates)}
        fusion_ranks = _rank_map(fused_order)
        reranked_order = sorted(
            candidates,
            key=lambda idx: (-rerank_by_index[idx], fusion_ranks[idx], idx),
        )
        selected = _cap_per_document(
            reranked_order,
            self.index,
            top_k=top_k,
            max_per_doc=max_chunks_per_document,
        )
        dense_ranks = _rank_map(dense_order)
        lexical_ranks = _rank_map(lexical_order)
        return [
            RagSearchResult(
                rank=rank,
                chunk=self.index.chunks[chunk_index],
                score=float(rerank_by_index[chunk_index]),
                dense_rank=dense_ranks[chunk_index],
                lexical_rank=lexical_ranks[chunk_index],
                fusion_rank=fusion_ranks[chunk_index],
                fusion_score=float(fused[chunk_index]),
                rerank_score=float(rerank_by_index[chunk_index]),
            )
            for rank, chunk_index in enumerate(selected, start=1)
        ]

    def search(
        self,
        question: str,
        *,
        strategy: str,
        top_k: int = 6,
        max_chunks_per_document: int = 2,
        rrf_k: int = 60,
        candidate_k: int = 24,
        candidate_max_chunks_per_document: int = 4,
    ) -> list[RagSearchResult]:
        if strategy == "dense":
            return self.dense(
                question,
                top_k=top_k,
                max_chunks_per_document=max_chunks_per_document,
            )
        if strategy == "hybrid":
            return self.hybrid(
                question,
                top_k=top_k,
                max_chunks_per_document=max_chunks_per_document,
                rrf_k=rrf_k,
            )
        if strategy == "hybrid_rerank":
            return self.hybrid_rerank(
                question,
                top_k=top_k,
                max_chunks_per_document=max_chunks_per_document,
                rrf_k=rrf_k,
                candidate_k=candidate_k,
                candidate_max_chunks_per_document=candidate_max_chunks_per_document,
            )
        raise ValueError("strategy must be 'dense', 'hybrid', or 'hybrid_rerank'")
