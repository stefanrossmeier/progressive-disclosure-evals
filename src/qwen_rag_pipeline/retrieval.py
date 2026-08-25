from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from rag_baseline.retrieval import Bm25Index, lexical_tokens, reciprocal_rank_fusion

from .index import LoadedQwenIndex, _sentence_transformer, format_query
from .model_assets import DEFAULT_MODEL_ROOT, RERANKER_ASSET, require_model_path
from .models import QwenSearchResult


DEFAULT_RERANK_INSTRUCTION = (
    "Given a knowledge-base question and a passage from a candidate document, judge whether "
    "the passage contains evidence needed to answer any part of the question."
)


def _rank_map(order: list[int]) -> dict[int, int]:
    return {index: rank for rank, index in enumerate(order, start=1)}


def _cross_encoder(model_path, *, device: str | None = None, instruction: str = DEFAULT_RERANK_INSTRUCTION):
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "Qwen RAG reranking requires sentence-transformers; "
            "install with: pip install -r requirements-qwen-rag.txt"
        ) from exc
    kwargs: dict[str, Any] = {
        "local_files_only": True,
        "prompts": {"evidence": instruction},
        "default_prompt_name": "evidence",
    }
    if device:
        kwargs["device"] = device
    return CrossEncoder(str(model_path), **kwargs)


@dataclass
class QwenHierarchicalRetriever:
    index: LoadedQwenIndex
    model_root: str = str(DEFAULT_MODEL_ROOT)
    device: str | None = None
    document_candidates: int = 12
    chunk_candidates_per_document: int = 4
    top_k: int = 8
    unique_document_slots: int = 5
    rrf_k: int = 60
    rerank_batch_size: int = 8
    rerank_instruction: str = DEFAULT_RERANK_INSTRUCTION

    def __post_init__(self) -> None:
        if min(
            self.document_candidates,
            self.chunk_candidates_per_document,
            self.top_k,
            self.unique_document_slots,
            self.rrf_k,
            self.rerank_batch_size,
        ) < 1:
            raise ValueError("Qwen RAG retrieval settings must be >= 1")
        if self.unique_document_slots > self.top_k:
            raise ValueError("unique_document_slots must be <= top_k")
        self._encoder = None
        self._reranker = None
        self._document_bm25 = None
        self._chunk_bm25 = None
        self._chunks_by_document: dict[str, list[int]] = defaultdict(list)
        for index, chunk in enumerate(self.index.chunks):
            self._chunks_by_document[chunk.document_id].append(index)

    @property
    def encoder(self):
        if self._encoder is None:
            model_path = self.index.manifest.embedding_model_path
            self._encoder = _sentence_transformer(model_path, device=self.device)
        return self._encoder

    @property
    def reranker(self):
        if self._reranker is None:
            model_path = require_model_path(RERANKER_ASSET, self.model_root)
            self._reranker = _cross_encoder(
                model_path, device=self.device, instruction=self.rerank_instruction
            )
        return self._reranker

    @property
    def document_bm25(self) -> Bm25Index:
        if self._document_bm25 is None:
            tokenized = tuple(tuple(lexical_tokens(document.search_text)) for document in self.index.documents)
            self._document_bm25 = Bm25Index(tokenized)
        return self._document_bm25

    @property
    def chunk_bm25(self) -> Bm25Index:
        if self._chunk_bm25 is None:
            tokenized = tuple(tuple(lexical_tokens(chunk.search_text)) for chunk in self.index.chunks)
            self._chunk_bm25 = Bm25Index(tokenized)
        return self._chunk_bm25

    def _query_vector(self, question: str):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - optional install
            raise RuntimeError(
                "Qwen RAG requires numpy; install with: pip install -r requirements-qwen-rag.txt"
            ) from exc
        encoded = self.encoder.encode(
            [format_query(question, self.index.manifest.query_instruction)],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(encoded[0], dtype=np.float32)

    def _document_order(self, question: str, query_vector):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("numpy is required") from exc
        dense_scores = self.index.document_embeddings @ query_vector
        dense_order = np.argsort(-dense_scores, kind="stable").tolist()
        lexical_scores = np.asarray(self.document_bm25.scores(lexical_tokens(question)), dtype=np.float32)
        lexical_order = np.argsort(-lexical_scores, kind="stable").tolist()
        fused = reciprocal_rank_fusion(dense_order, lexical_order, rrf_k=self.rrf_k)
        fused_order = sorted(fused, key=lambda idx: (-fused[idx], idx))
        return dense_order, lexical_order, fused_order

    def _chunk_orders(self, question: str, query_vector):
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("numpy is required") from exc
        dense_scores = self.index.chunk_embeddings @ query_vector
        dense_order = np.argsort(-dense_scores, kind="stable").tolist()
        lexical_scores = np.asarray(self.chunk_bm25.scores(lexical_tokens(question)), dtype=np.float32)
        lexical_order = np.argsort(-lexical_scores, kind="stable").tolist()
        return dense_order, lexical_order

    def search(self, question: str) -> list[QwenSearchResult]:
        query_vector = self._query_vector(question)
        document_dense_order, document_lexical_order, document_order = self._document_order(
            question, query_vector
        )
        chunk_dense_order, chunk_lexical_order = self._chunk_orders(question, query_vector)
        document_dense_ranks = _rank_map(document_dense_order)
        document_lexical_ranks = _rank_map(document_lexical_order)
        chunk_dense_ranks = _rank_map(chunk_dense_order)
        chunk_lexical_ranks = _rank_map(chunk_lexical_order)

        candidate_document_indices = document_order[: self.document_candidates]
        candidate_doc_ids = [self.index.documents[index].id for index in candidate_document_indices]
        candidate_doc_rank = {doc_id: rank for rank, doc_id in enumerate(candidate_doc_ids, start=1)}

        per_document_candidates: dict[str, list[int]] = {}
        chunk_fusion_rank: dict[int, int] = {}
        rerank_pairs: list[tuple[str, str]] = []
        rerank_chunk_indices: list[int] = []

        for doc_id in candidate_doc_ids:
            allowed = set(self._chunks_by_document.get(doc_id, []))
            dense_local = [index for index in chunk_dense_order if index in allowed]
            lexical_local = [index for index in chunk_lexical_order if index in allowed]
            fused = reciprocal_rank_fusion(dense_local, lexical_local, rrf_k=self.rrf_k)
            fused_order = sorted(fused, key=lambda idx: (-fused[idx], idx))
            selected = fused_order[: self.chunk_candidates_per_document]
            per_document_candidates[doc_id] = selected
            for rank, chunk_index in enumerate(fused_order, start=1):
                chunk_fusion_rank[chunk_index] = rank
            for chunk_index in selected:
                rerank_chunk_indices.append(chunk_index)
                rerank_pairs.append((question.strip(), self.index.chunks[chunk_index].search_text))

        raw_scores = self.reranker.predict(
            rerank_pairs,
            batch_size=self.rerank_batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("numpy is required") from exc
        scores = np.asarray(raw_scores).reshape(-1)
        if scores.size != len(rerank_chunk_indices):
            raise RuntimeError("Qwen reranker returned an unexpected number of scores")
        rerank_score = {
            chunk_index: float(scores[position])
            for position, chunk_index in enumerate(rerank_chunk_indices)
        }

        ranked_within_document: dict[str, list[int]] = {}
        within_document_rank: dict[int, int] = {}
        for doc_id, candidates in per_document_candidates.items():
            order = sorted(
                candidates,
                key=lambda idx: (-rerank_score[idx], chunk_fusion_rank.get(idx, 10**9), idx),
            )
            ranked_within_document[doc_id] = order
            for rank, chunk_index in enumerate(order, start=1):
                within_document_rank[chunk_index] = rank

        # Coverage-aware packing: preserve document-level hybrid order, use Qwen
        # only to choose the best passage *within* each document. This prevents
        # pointwise reranking from collapsing a multi-document evidence set.
        chosen: list[tuple[int, str]] = []
        unique_slots = min(self.unique_document_slots, self.top_k, len(candidate_doc_ids))
        for doc_id in candidate_doc_ids[:unique_slots]:
            candidates = ranked_within_document.get(doc_id, [])
            if candidates:
                chosen.append((candidates[0], "unique_document"))

        if len(chosen) < self.top_k:
            for depth in range(1, self.chunk_candidates_per_document):
                for doc_id in candidate_doc_ids[:unique_slots]:
                    candidates = ranked_within_document.get(doc_id, [])
                    if depth < len(candidates):
                        chosen.append((candidates[depth], "document_detail"))
                        if len(chosen) >= self.top_k:
                            break
                if len(chosen) >= self.top_k:
                    break

        # If short documents did not fill K, admit one best chunk from lower-ranked
        # candidate documents without disturbing the already-covered top documents.
        if len(chosen) < self.top_k:
            selected_ids = {index for index, _ in chosen}
            for doc_id in candidate_doc_ids[unique_slots:]:
                candidates = ranked_within_document.get(doc_id, [])
                if candidates and candidates[0] not in selected_ids:
                    chosen.append((candidates[0], "fallback_document"))
                    if len(chosen) >= self.top_k:
                        break

        chosen = chosen[: self.top_k]
        document_index_by_id = {document.id: index for index, document in enumerate(self.index.documents)}
        results: list[QwenSearchResult] = []
        for rank, (chunk_index, phase) in enumerate(chosen, start=1):
            chunk = self.index.chunks[chunk_index]
            doc_index = document_index_by_id[chunk.document_id]
            results.append(
                QwenSearchResult(
                    rank=rank,
                    chunk=chunk,
                    score=rerank_score[chunk_index],
                    document_rank=candidate_doc_rank[chunk.document_id],
                    document_dense_rank=document_dense_ranks[doc_index],
                    document_lexical_rank=document_lexical_ranks[doc_index],
                    chunk_dense_rank=chunk_dense_ranks[chunk_index],
                    chunk_lexical_rank=chunk_lexical_ranks[chunk_index],
                    chunk_fusion_rank=chunk_fusion_rank.get(chunk_index),
                    rerank_score=rerank_score[chunk_index],
                    within_document_rank=within_document_rank[chunk_index],
                    selection_phase=phase,
                )
            )
        return results
