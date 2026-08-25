from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .models import RagChunk


DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"


def _cross_encoder(
    model_name: str,
    *,
    device: str | None = None,
    offline: bool = False,
):
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "local RAG reranking requires the optional rag dependencies; "
            "install with: pip install -r requirements-rag.txt"
        ) from exc
    kwargs: dict[str, Any] = {"local_files_only": offline}
    if device:
        kwargs["device"] = device
    return CrossEncoder(model_name, **kwargs)


@dataclass
class LocalCrossEncoderReranker:
    model_name: str = DEFAULT_RERANKER_MODEL
    device: str | None = None
    offline: bool = False
    batch_size: int = 16

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError("rerank batch_size must be >= 1")
        self._model: Any | None = None

    @property
    def model(self):
        if self._model is None:
            self._model = _cross_encoder(
                self.model_name,
                device=self.device,
                offline=self.offline,
            )
        return self._model

    def scores(self, question: str, chunks: Sequence[RagChunk]) -> list[float]:
        if not chunks:
            return []
        pairs = [(question.strip(), chunk.search_text) for chunk in chunks]
        raw = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - numpy is part of the RAG extra
            raise RuntimeError(
                "local RAG reranking requires numpy; install with: pip install -r requirements-rag.txt"
            ) from exc
        values = np.asarray(raw).reshape(-1)
        if values.size != len(chunks):
            raise RuntimeError("reranker returned an unexpected number of scores")
        return [float(value) for value in values]
