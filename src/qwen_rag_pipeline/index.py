from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from progressive_disclosure.corpora import get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase
from rag_baseline.chunking import chunk_document
from rag_baseline.index import corpus_sha256
from rag_baseline.models import RagChunk

from .model_assets import DEFAULT_MODEL_ROOT, EMBEDDING_ASSET, require_model_path
from .models import QwenDocumentRecord


DEFAULT_INDEX_ROOT = Path("results/qwen-rag-indexes")
DEFAULT_QUERY_INSTRUCTION = (
    "Given a knowledge-base question, retrieve all documents and passages that contain "
    "evidence needed to answer it. Favor complementary evidence for multi-part questions."
)


@dataclass(frozen=True)
class QwenIndexManifest:
    schema_version: int
    corpus_name: str
    corpus_root: str
    corpus_sha256: str
    embedding_repo: str
    embedding_revision: str
    embedding_model_path: str
    query_instruction: str
    chunk_words: int
    overlap_words: int
    document_count: int
    chunk_count: int
    embedding_dimensions: int
    created_at: str


def index_dir_for(corpus_name: str, root: Path | str = DEFAULT_INDEX_ROOT) -> Path:
    return Path(root) / corpus_name


def format_query(question: str, instruction: str = DEFAULT_QUERY_INSTRUCTION) -> str:
    return f"Instruct: {instruction.strip()}\nQuery: {question.strip()}"


def document_search_text(document) -> str:
    return "\n".join(
        [
            f"Document ID: {document.id}",
            f"Title: {document.title}",
            f"Description: {document.description}",
            f"Path: {document.path}",
            "",
            document.content.strip(),
        ]
    )


def _sentence_transformer(model_path: Path | str, *, device: str | None = None):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "Qwen RAG requires sentence-transformers; "
            "install with: pip install -r requirements-qwen-rag.txt"
        ) from exc
    kwargs: dict[str, Any] = {"local_files_only": True}
    if device:
        kwargs["device"] = device
    return SentenceTransformer(str(model_path), **kwargs)


def build_index(
    corpus_name: str,
    *,
    output_dir: Path | str | None = None,
    model_root: Path | str = DEFAULT_MODEL_ROOT,
    query_instruction: str = DEFAULT_QUERY_INSTRUCTION,
    chunk_words: int = 320,
    overlap_words: int = 64,
    batch_size: int = 8,
    device: str | None = None,
) -> Path:
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "Qwen RAG requires numpy; install with: pip install -r requirements-qwen-rag.txt"
        ) from exc

    model_path = require_model_path(EMBEDDING_ASSET, model_root)
    spec = get_corpus_spec(corpus_name)
    knowledge = KnowledgeBase(spec.root)

    documents: list[QwenDocumentRecord] = []
    chunks: list[RagChunk] = []
    for document_id in knowledge.document_ids:
        document = knowledge.read(document_id)
        documents.append(
            QwenDocumentRecord(
                id=document.id,
                title=document.title,
                description=document.description,
                path=document.path,
                search_text=document_search_text(document),
            )
        )
        chunks.extend(
            chunk_document(
                document,
                target_words=chunk_words,
                overlap_words=overlap_words,
            )
        )
    if not documents or not chunks:
        raise ValueError(f"no indexable content produced for corpus {corpus_name}")

    encoder = _sentence_transformer(model_path, device=device)
    document_embeddings = encoder.encode(
        [document.search_text for document in documents],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    chunk_embeddings = encoder.encode(
        [chunk.search_text for chunk in chunks],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    document_embeddings = np.asarray(document_embeddings, dtype=np.float32)
    chunk_embeddings = np.asarray(chunk_embeddings, dtype=np.float32)
    if document_embeddings.ndim != 2 or document_embeddings.shape[0] != len(documents):
        raise RuntimeError("embedding model returned an unexpected document matrix shape")
    if chunk_embeddings.ndim != 2 or chunk_embeddings.shape[0] != len(chunks):
        raise RuntimeError("embedding model returned an unexpected chunk matrix shape")
    if document_embeddings.shape[1] != chunk_embeddings.shape[1]:
        raise RuntimeError("document and chunk embedding dimensions differ")

    target = Path(output_dir) if output_dir is not None else index_dir_for(corpus_name)
    target.mkdir(parents=True, exist_ok=True)
    (target / "documents.jsonl").write_text(
        "".join(json.dumps(asdict(document), ensure_ascii=False) + "\n" for document in documents),
        encoding="utf-8",
    )
    (target / "chunks.jsonl").write_text(
        "".join(json.dumps(asdict(chunk), ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    np.save(target / "document-embeddings.npy", document_embeddings, allow_pickle=False)
    np.save(target / "chunk-embeddings.npy", chunk_embeddings, allow_pickle=False)

    manifest = QwenIndexManifest(
        schema_version=1,
        corpus_name=corpus_name,
        corpus_root=str(spec.root),
        corpus_sha256=corpus_sha256(spec.root),
        embedding_repo=EMBEDDING_ASSET.repo_id,
        embedding_revision=EMBEDDING_ASSET.revision,
        embedding_model_path=str(model_path),
        query_instruction=query_instruction,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        document_count=len(documents),
        chunk_count=len(chunks),
        embedding_dimensions=int(chunk_embeddings.shape[1]),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    (target / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2) + "\n",
        encoding="utf-8",
    )
    return target


@dataclass
class LoadedQwenIndex:
    directory: Path
    manifest: QwenIndexManifest
    documents: list[QwenDocumentRecord]
    chunks: list[RagChunk]
    document_embeddings: Any
    chunk_embeddings: Any


def load_index(directory: Path | str, *, verify_corpus: bool = True) -> LoadedQwenIndex:
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "Qwen RAG requires numpy; install with: pip install -r requirements-qwen-rag.txt"
        ) from exc

    root = Path(directory)
    manifest = QwenIndexManifest(**json.loads((root / "manifest.json").read_text(encoding="utf-8")))
    documents = [
        QwenDocumentRecord(**json.loads(line))
        for line in (root / "documents.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunks = [
        RagChunk(**json.loads(line))
        for line in (root / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    document_embeddings = np.load(root / "document-embeddings.npy", allow_pickle=False)
    chunk_embeddings = np.load(root / "chunk-embeddings.npy", allow_pickle=False)
    if len(documents) != manifest.document_count or len(chunks) != manifest.chunk_count:
        raise ValueError("Qwen RAG index record count does not match manifest")
    if document_embeddings.shape != (len(documents), manifest.embedding_dimensions):
        raise ValueError("Qwen RAG document embedding matrix does not match manifest")
    if chunk_embeddings.shape != (len(chunks), manifest.embedding_dimensions):
        raise ValueError("Qwen RAG chunk embedding matrix does not match manifest")
    if verify_corpus:
        spec = get_corpus_spec(manifest.corpus_name)
        if corpus_sha256(spec.root) != manifest.corpus_sha256:
            raise ValueError(
                "Qwen RAG index is stale for the current corpus; rebuild it with "
                f"python scripts/build_qwen_rag_index.py --corpus {manifest.corpus_name}"
            )
    return LoadedQwenIndex(
        directory=root,
        manifest=manifest,
        documents=documents,
        chunks=chunks,
        document_embeddings=document_embeddings,
        chunk_embeddings=chunk_embeddings,
    )
