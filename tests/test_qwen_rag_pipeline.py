from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from qwen_rag_pipeline.evaluation import load_plan
from qwen_rag_pipeline.index import LoadedQwenIndex, QwenIndexManifest, format_query
from qwen_rag_pipeline.model_assets import EMBEDDING_ASSET, RERANKER_ASSET
from qwen_rag_pipeline.models import QwenDocumentRecord
from qwen_rag_pipeline.retrieval import QwenHierarchicalRetriever
from rag_baseline.models import RagChunk


class FakeEncoder:
    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)


class FakeReranker:
    def predict(self, pairs, **kwargs):
        scores = []
        for _, passage in pairs:
            if "preferred" in passage:
                scores.append(100.0)
            elif "doc1" in passage:
                scores.append(90.0)
            else:
                scores.append(1.0)
        return np.asarray(scores, dtype=np.float32)


def _fake_index() -> LoadedQwenIndex:
    documents = [
        QwenDocumentRecord(
            id=f"doc{i}",
            title=f"Document {i}",
            description=f"topic {i}",
            path=f"doc{i}.md",
            search_text=f"Document {i} topic {i}",
        )
        for i in range(1, 6)
    ]
    chunks = []
    for i in range(1, 6):
        chunks.extend(
            [
                RagChunk(
                    id=f"doc{i}::c001",
                    document_id=f"doc{i}",
                    title=f"Document {i}",
                    description=f"topic {i}",
                    path=f"doc{i}.md",
                    heading="",
                    text=f"doc{i} first passage",
                    search_text=f"doc{i} first passage",
                ),
                RagChunk(
                    id=f"doc{i}::c002",
                    document_id=f"doc{i}",
                    title=f"Document {i}",
                    description=f"topic {i}",
                    path=f"doc{i}.md",
                    heading="",
                    text=("preferred " if i == 1 else "") + f"doc{i} second passage",
                    search_text=("preferred " if i == 1 else "") + f"doc{i} second passage",
                ),
            ]
        )
    # Stable dense order doc1..doc5 and chunk order by construction.
    doc_embeddings = np.asarray([[1.0 - i * 0.05, 0.0] for i in range(5)], dtype=np.float32)
    chunk_embeddings = np.asarray([[1.0 - i * 0.01, 0.0] for i in range(10)], dtype=np.float32)
    manifest = QwenIndexManifest(
        schema_version=1,
        corpus_name="northstar",
        corpus_root="corpus",
        corpus_sha256="x",
        embedding_repo=EMBEDDING_ASSET.repo_id,
        embedding_revision=EMBEDDING_ASSET.revision,
        embedding_model_path="models/qwen-rag/Qwen3-Embedding-0.6B",
        query_instruction="retrieve evidence",
        chunk_words=320,
        overlap_words=64,
        document_count=5,
        chunk_count=10,
        embedding_dimensions=2,
        created_at="now",
    )
    return LoadedQwenIndex(
        directory=Path("unused"),
        manifest=manifest,
        documents=documents,
        chunks=chunks,
        document_embeddings=doc_embeddings,
        chunk_embeddings=chunk_embeddings,
    )


def test_qwen_models_are_version_pinned() -> None:
    assert EMBEDDING_ASSET.repo_id == "Qwen/Qwen3-Embedding-0.6B"
    assert EMBEDDING_ASSET.revision == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    assert RERANKER_ASSET.repo_id == "Qwen/Qwen3-Reranker-0.6B"
    assert RERANKER_ASSET.revision == "e61197ed45024b0ed8a2d74b80b4d909f1255473"


def test_qwen_query_instruction_is_explicit() -> None:
    query = format_query("Which source applies?", "Retrieve complementary evidence")
    assert query == "Instruct: Retrieve complementary evidence\nQuery: Which source applies?"


def test_hierarchical_packing_preserves_document_coverage() -> None:
    retriever = QwenHierarchicalRetriever(
        _fake_index(),
        document_candidates=5,
        chunk_candidates_per_document=2,
        top_k=6,
        unique_document_slots=5,
    )
    retriever._encoder = FakeEncoder()
    retriever._reranker = FakeReranker()
    results = retriever.search("topic")
    first_five_docs = [result.chunk.document_id for result in results[:5]]
    assert first_five_docs == ["doc1", "doc2", "doc3", "doc4", "doc5"]
    assert results[0].chunk.id == "doc1::c002"  # reranker improves passage choice inside doc1
    assert results[5].chunk.document_id == "doc1"  # spare slot returns detail for highest-ranked doc


def test_qwen_plan_is_separate_from_existing_rag() -> None:
    plan = load_plan("experiments/qwen-rag/northstar.yaml")
    assert plan.index_dir == Path("results/qwen-rag-indexes/northstar")
    assert plan.model_root == Path("models/qwen-rag")
    assert plan.top_k == 8
    assert plan.document_candidates == 12
    assert plan.unique_document_slots == 5


def test_qwen_plan_rejects_more_unique_slots_than_context(tmp_path: Path) -> None:
    config = tmp_path / "bad.yaml"
    config.write_text(
        "\n".join(
            [
                "name: bad",
                "dataset: datasets/eval-v1.yaml",
                "corpus: northstar",
                "top_k: 4",
                "unique_document_slots: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique_document_slots"):
        load_plan(config)


def test_download_script_dry_run_does_not_need_network() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/download_qwen_rag_models.py", "--dry-run"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert EMBEDDING_ASSET.revision in result.stdout
    assert RERANKER_ASSET.revision in result.stdout


def test_qwen_pipeline_has_safe_dry_run() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_qwen_rag_pipeline.py", "--dry-run", "--with-paid-evals"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "paid smoke -> paid E2E" in result.stdout


def test_download_assets_passes_pinned_revisions_without_hub_resolution(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        target = Path(kwargs["local_dir"])
        target.mkdir(parents=True, exist_ok=True)
        (target / "config.json").write_text("{}", encoding="utf-8")
        (target / "model.safetensors").write_bytes(b"fake")
        return str(target)

    class FakeHub:
        snapshot_download = staticmethod(fake_snapshot_download)

    monkeypatch.setitem(sys.modules, "huggingface_hub", FakeHub())
    from qwen_rag_pipeline.model_assets import download_assets

    manifest = download_assets(model_root=tmp_path, max_workers=2)
    assert manifest.is_file()
    assert [call["revision"] for call in calls] == [EMBEDDING_ASSET.revision, RERANKER_ASSET.revision]
    assert all(Path(call["local_dir"]).is_relative_to(tmp_path) for call in calls)


def test_qwen_cross_encoder_receives_local_only_and_task_instruction(monkeypatch) -> None:
    captured = {}

    class FakeCrossEncoder:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured.update(kwargs)

    class FakeSentenceTransformers:
        CrossEncoder = FakeCrossEncoder

    monkeypatch.setitem(sys.modules, "sentence_transformers", FakeSentenceTransformers())
    from qwen_rag_pipeline.retrieval import DEFAULT_RERANK_INSTRUCTION, _cross_encoder

    _cross_encoder("/tmp/local-reranker", device="mps")
    assert captured["model_name"] == "/tmp/local-reranker"
    assert captured["local_files_only"] is True
    assert captured["device"] == "mps"
    assert captured["prompts"] == {"evidence": DEFAULT_RERANK_INSTRUCTION}
    assert captured["default_prompt_name"] == "evidence"


def test_qwen_index_builds_separate_document_and_chunk_matrices(monkeypatch, tmp_path: Path) -> None:
    import qwen_rag_pipeline.index as qindex

    class FakeBatchEncoder:
        def encode(self, texts, **kwargs):
            assert kwargs["normalize_embeddings"] is True
            return np.asarray([[1.0, float(i % 3)] for i, _ in enumerate(texts)], dtype=np.float32)

    monkeypatch.setattr(qindex, "require_model_path", lambda asset, root: tmp_path / "fake-model")
    monkeypatch.setattr(qindex, "_sentence_transformer", lambda model_path, device=None: FakeBatchEncoder())
    target = qindex.build_index("northstar", output_dir=tmp_path / "index")
    loaded = qindex.load_index(target, verify_corpus=True)
    assert len(loaded.documents) == 40
    assert len(loaded.chunks) > 40
    assert loaded.document_embeddings.shape == (40, 2)
    assert loaded.chunk_embeddings.shape == (len(loaded.chunks), 2)
    assert loaded.manifest.embedding_revision == EMBEDDING_ASSET.revision
