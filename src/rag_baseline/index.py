from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from progressive_disclosure.corpora import get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase

from .chunking import chunk_document
from .models import RagChunk


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DEFAULT_INDEX_ROOT = Path("results/rag-indexes")


@dataclass(frozen=True)
class RagIndexManifest:
    schema_version: int
    corpus_name: str
    corpus_root: str
    corpus_sha256: str
    embedding_model: str
    query_prefix: str
    chunk_words: int
    overlap_words: int
    document_count: int
    chunk_count: int
    embedding_dimensions: int
    created_at: str


def corpus_sha256(root: Path | str) -> str:
    root_path = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root_path.rglob("*.md")):
        relative = path.relative_to(root_path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def index_dir_for(corpus_name: str, root: Path | str = DEFAULT_INDEX_ROOT) -> Path:
    return Path(root) / corpus_name


def _sentence_transformer(
    model_name: str,
    *,
    device: str | None = None,
    offline: bool = False,
):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "local RAG requires the optional rag dependencies; "
            "install with: pip install -r requirements-rag.txt"
        ) from exc
    kwargs: dict[str, Any] = {"local_files_only": offline}
    if device:
        kwargs["device"] = device
    return SentenceTransformer(model_name, **kwargs)


def build_index(
    corpus_name: str,
    *,
    output_dir: Path | str | None = None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    query_prefix: str = DEFAULT_QUERY_PREFIX,
    chunk_words: int = 320,
    overlap_words: int = 64,
    batch_size: int = 32,
    device: str | None = None,
    offline: bool = False,
) -> Path:
    """Build one fully local dense index for a configured corpus.

    The same saved embeddings/chunks are used by both dense and hybrid retrieval.
    Hybrid BM25 statistics are derived from the saved chunk text at query time, so
    there is no second index format to keep in sync.
    """

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "local RAG requires numpy; install with: pip install -r requirements-rag.txt"
        ) from exc

    spec = get_corpus_spec(corpus_name)
    knowledge = KnowledgeBase(spec.root)
    chunks: list[RagChunk] = []
    for document_id in knowledge.document_ids:
        chunks.extend(
            chunk_document(
                knowledge.read(document_id),
                target_words=chunk_words,
                overlap_words=overlap_words,
            )
        )
    if not chunks:
        raise ValueError(f"no chunks produced for corpus {corpus_name}")

    encoder = _sentence_transformer(
        embedding_model,
        device=device,
        offline=offline,
    )
    embeddings = encoder.encode(
        [chunk.search_text for chunk in chunks],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
        raise RuntimeError("embedding model returned an unexpected matrix shape")

    target = Path(output_dir) if output_dir is not None else index_dir_for(corpus_name)
    target.mkdir(parents=True, exist_ok=True)
    chunks_path = target / "chunks.jsonl"
    embeddings_path = target / "embeddings.npy"
    manifest_path = target / "manifest.json"

    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    np.save(embeddings_path, embeddings, allow_pickle=False)

    manifest = RagIndexManifest(
        schema_version=1,
        corpus_name=corpus_name,
        corpus_root=str(spec.root),
        corpus_sha256=corpus_sha256(spec.root),
        embedding_model=embedding_model,
        query_prefix=query_prefix,
        chunk_words=chunk_words,
        overlap_words=overlap_words,
        document_count=len(knowledge.document_ids),
        chunk_count=len(chunks),
        embedding_dimensions=int(embeddings.shape[1]),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), indent=2) + "\n",
        encoding="utf-8",
    )
    return target


@dataclass
class LoadedRagIndex:
    directory: Path
    manifest: RagIndexManifest
    chunks: list[RagChunk]
    embeddings: Any


def load_index(directory: Path | str, *, verify_corpus: bool = True) -> LoadedRagIndex:
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "local RAG requires numpy; install with: pip install -r requirements-rag.txt"
        ) from exc

    root = Path(directory)
    raw = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest = RagIndexManifest(**raw)
    chunks = [
        RagChunk(**json.loads(line))
        for line in (root / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    embeddings = np.load(root / "embeddings.npy", allow_pickle=False)
    if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
        raise ValueError("RAG index embeddings/chunk count mismatch")
    if embeddings.shape[1] != manifest.embedding_dimensions:
        raise ValueError("RAG index embedding dimension does not match manifest")
    if len(chunks) != manifest.chunk_count:
        raise ValueError("RAG index chunk count does not match manifest")

    if verify_corpus:
        spec = get_corpus_spec(manifest.corpus_name)
        current = corpus_sha256(spec.root)
        if current != manifest.corpus_sha256:
            raise ValueError(
                "RAG index is stale for the current corpus; rebuild it with "
                f"python scripts/build_rag_index.py --corpus {manifest.corpus_name}"
            )
    return LoadedRagIndex(
        directory=root,
        manifest=manifest,
        chunks=chunks,
        embeddings=embeddings,
    )
