from __future__ import annotations

from pathlib import Path

from progressive_disclosure.models import KnowledgeDocument
from progressive_disclosure.prompts import load_prompt_artifact
from rag_baseline.chunking import chunk_document
from rag_baseline.evaluation import load_rag_plan
from rag_baseline.index import DEFAULT_EMBEDDING_MODEL, DEFAULT_QUERY_PREFIX, index_dir_for
from rag_baseline.retrieval import Bm25Index, lexical_tokens, reciprocal_rank_fusion


def _doc(content: str) -> KnowledgeDocument:
    return KnowledgeDocument(
        id="TA-TEST-01",
        title="Test report",
        description="Use for testing local RAG chunking.",
        path="test/ta-test-01.md",
        content=content,
    )


def test_chunk_document_is_deterministic_and_carries_routing_metadata() -> None:
    content = "# Main\n\n" + " ".join(f"word{i}" for i in range(180)) + "\n\n## Detail\n\n" + " ".join(
        f"detail{i}" for i in range(180)
    )
    first = chunk_document(_doc(content), target_words=160, overlap_words=32)
    second = chunk_document(_doc(content), target_words=160, overlap_words=32)
    assert first == second
    assert len(first) >= 2
    assert first[0].id == "TA-TEST-01::c001"
    assert "Document ID: TA-TEST-01" in first[0].search_text
    assert "Description: Use for testing local RAG chunking." in first[0].search_text
    assert all(chunk.document_id == "TA-TEST-01" for chunk in first)


def test_chunk_document_rejects_invalid_overlap() -> None:
    try:
        chunk_document(_doc("body " * 100), target_words=64, overlap_words=64)
    except ValueError as exc:
        assert "overlap_words" in str(exc)
    else:  # pragma: no cover - assertion helper
        raise AssertionError("expected ValueError")


def test_lexical_tokenizer_preserves_exact_identifiers() -> None:
    tokens = lexical_tokens("MIG-2 applies to TA-EXC-06 and context C-511; Atlas Lattice-3.")
    assert "mig-2" in tokens
    assert "ta-exc-06" in tokens
    assert "c-511" in tokens
    assert "lattice-3" in tokens


def test_rrf_rewards_items_ranked_high_by_both_retrievers() -> None:
    fused = reciprocal_rank_fusion([0, 1, 2], [1, 0, 2], rrf_k=10)
    assert fused[0] == fused[1]
    assert fused[0] > fused[2]


def test_bm25_prefers_exact_identifier_match() -> None:
    index = Bm25Index((
        tuple(lexical_tokens("general migration policy")),
        tuple(lexical_tokens("MIG-2 migration credit policy")),
        tuple(lexical_tokens("archaeological excavation report")),
    ))
    scores = index.scores(lexical_tokens("MIG-2 credit"))
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]


def test_rag_configs_use_current_release_datasets() -> None:
    dense_ns = load_rag_plan("experiments/rag/dense-northstar.yaml")
    dense_ta = load_rag_plan("experiments/rag/dense-tell-aster.yaml")
    hybrid_ns = load_rag_plan("experiments/rag/hybrid-northstar.yaml")
    hybrid_ta = load_rag_plan("experiments/rag/hybrid-tell-aster.yaml")

    assert dense_ns.strategy == "dense"
    assert hybrid_ns.strategy == "hybrid"
    assert dense_ns.dataset == Path("datasets/eval-v1.yaml")
    assert dense_ta.dataset == Path("datasets/tell-aster-eval-v2.yaml")
    assert hybrid_ta.dataset == Path("datasets/tell-aster-eval-v2.yaml")
    assert {dense_ns.top_k, dense_ta.top_k, hybrid_ns.top_k, hybrid_ta.top_k} == {6}
    assert all(
        plan.max_chunks_per_document == 2
        for plan in (dense_ns, dense_ta, hybrid_ns, hybrid_ta)
    )


def test_retrieval_only_config_loading_does_not_require_openai_model_env(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    plan = load_rag_plan("experiments/rag/dense-northstar.yaml")
    assert plan.model == "env:OPENAI_MODEL"


def test_rag_prompt_is_versioned_and_corpus_neutral() -> None:
    prompt = load_prompt_artifact("prompts/rag/system-v1.md")
    assert prompt.id == "local-rag-answer-system"
    assert prompt.version == 1
    folded = prompt.content.casefold()
    assert "northstar" not in folded
    assert "tell aster" not in folded
    assert "required_documents" not in folded
    assert "expected_contains" not in folded


def test_default_index_location_is_under_ignored_results_tree() -> None:
    assert index_dir_for("northstar") == Path("results/rag-indexes/northstar")
    assert DEFAULT_EMBEDDING_MODEL == "BAAI/bge-small-en-v1.5"
    assert DEFAULT_QUERY_PREFIX.startswith("Represent this sentence")


def test_local_index_build_and_load_with_fake_encoder(tmp_path, monkeypatch) -> None:
    np = __import__("pytest").importorskip("numpy")
    from types import SimpleNamespace
    import rag_baseline.index as index_module

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text(
        "---\nid: DOC-A\ntitle: Alpha\ndescription: Use for alpha facts.\n---\n# Alpha\n\nAlpha fact one. "
        + "more words " * 80,
        encoding="utf-8",
    )
    (corpus / "b.md").write_text(
        "---\nid: DOC-B\ntitle: Beta\ndescription: Use for beta facts.\n---\n# Beta\n\nBeta fact two. "
        + "other words " * 80,
        encoding="utf-8",
    )

    monkeypatch.setattr(
        index_module,
        "get_corpus_spec",
        lambda name: SimpleNamespace(root=corpus),
    )

    class FakeEncoder:
        def encode(self, texts, **kwargs):
            rows = []
            for text in texts:
                folded = text.casefold()
                row = np.array(
                    [
                        1.0 if "alpha" in folded else 0.0,
                        1.0 if "beta" in folded else 0.0,
                        0.5,
                    ],
                    dtype=np.float32,
                )
                row /= np.linalg.norm(row)
                rows.append(row)
            return np.vstack(rows)

    monkeypatch.setattr(index_module, "_sentence_transformer", lambda *args, **kwargs: FakeEncoder())
    target = index_module.build_index(
        "fake",
        output_dir=tmp_path / "index",
        chunk_words=64,
        overlap_words=8,
    )
    loaded = index_module.load_index(target)
    assert loaded.manifest.corpus_name == "fake"
    assert loaded.manifest.document_count == 2
    assert loaded.manifest.chunk_count == len(loaded.chunks)
    assert loaded.embeddings.shape[0] == len(loaded.chunks)
    assert loaded.embeddings.shape[1] == 3


def test_local_retriever_dense_and_hybrid_rank_expected_document(tmp_path) -> None:
    pytest = __import__("pytest")
    np = pytest.importorskip("numpy")
    from rag_baseline.index import LoadedRagIndex, RagIndexManifest
    from rag_baseline.models import RagChunk
    from rag_baseline.retrieval import LocalRetriever

    chunks = [
        RagChunk(
            id="DOC-A::c001",
            document_id="DOC-A",
            title="General",
            description="general policy",
            path="a.md",
            heading="",
            text="general policy",
            search_text="general policy",
        ),
        RagChunk(
            id="DOC-B::c001",
            document_id="DOC-B",
            title="Migration",
            description="MIG-2 migration credit",
            path="b.md",
            heading="",
            text="MIG-2 migration credit",
            search_text="MIG-2 migration credit",
        ),
    ]
    embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    manifest = RagIndexManifest(
        schema_version=1,
        corpus_name="fake",
        corpus_root="fake",
        corpus_sha256="abc",
        embedding_model="fake",
        query_prefix="",
        chunk_words=320,
        overlap_words=64,
        document_count=2,
        chunk_count=2,
        embedding_dimensions=2,
        created_at="now",
    )
    loaded = LoadedRagIndex(tmp_path, manifest, chunks, embeddings)
    retriever = LocalRetriever(loaded)

    class FakeEncoder:
        def encode(self, texts, **kwargs):
            return np.asarray([[0.0, 1.0]], dtype=np.float32)

    retriever._encoder = FakeEncoder()
    assert retriever.dense("MIG-2", top_k=1)[0].chunk.document_id == "DOC-B"
    assert retriever.hybrid("MIG-2", top_k=1)[0].chunk.document_id == "DOC-B"


def test_rag_answerer_uses_one_forced_answer_action() -> None:
    from progressive_disclosure.llm import ModelTurn, ModelUsage, ToolCall
    from rag_baseline.answering import RagAnswerer
    from rag_baseline.models import RagChunk, RagSearchResult

    class FakeBackend:
        def respond(self, *, instructions, user_input, tools, tool_choice):
            assert "retrieved evidence" in instructions.casefold()
            assert "DOC-A" in user_input
            assert tool_choice == {"type": "function", "name": "submit_rag_answer"}
            return ModelTurn(
                response_id="r1",
                text="",
                tool_calls=(
                    ToolCall(
                        call_id="c1",
                        name="submit_rag_answer",
                        arguments={"answer": "Alpha.", "sources": ["DOC-A"]},
                    ),
                ),
                usage=ModelUsage(input_tokens=10, output_tokens=3),
            )

    chunk = RagChunk(
        id="DOC-A::c001",
        document_id="DOC-A",
        title="Alpha",
        description="Use for alpha.",
        path="a.md",
        heading="Facts",
        text="The answer is Alpha.",
        search_text="Alpha",
    )
    result = RagAnswerer(
        FakeBackend(),
        prompt=load_prompt_artifact("prompts/rag/system-v1.md"),
    ).answer(
        "What is the answer?",
        [RagSearchResult(rank=1, chunk=chunk, score=1.0, dense_rank=1)],
    )
    assert result.answer == "Alpha."
    assert result.cited_sources == ("DOC-A",)
    assert result.model_turns == 1
    assert result.termination == "answer"


def test_rag_answer_tool_uses_openai_strict_schema_subset() -> None:
    from rag_baseline.answering import _answer_tool

    tool = _answer_tool(("DOC-A", "DOC-B"))
    assert tool["strict"] is True
    parameters = tool["parameters"]
    assert parameters["additionalProperties"] is False
    assert set(parameters["required"]) == set(parameters["properties"])

    # OpenAI strict function calling supports only a subset of JSON Schema.
    # Value/array constraints such as minLength and uniqueItems can make the
    # provider reject the request before the model is invoked. Keep those
    # checks client-side instead.
    serialized = __import__("json").dumps(tool)
    for unsupported in (
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "multipleOf",
        "minItems",
        "maxItems",
        "uniqueItems",
    ):
        assert unsupported not in serialized


def test_rag_answerer_deduplicates_sources_client_side() -> None:
    from progressive_disclosure.llm import ModelTurn, ModelUsage, ToolCall
    from rag_baseline.answering import RagAnswerer
    from rag_baseline.models import RagChunk, RagSearchResult

    class FakeBackend:
        def respond(self, *, instructions, user_input, tools, tool_choice):
            return ModelTurn(
                response_id="r1",
                text="",
                tool_calls=(
                    ToolCall(
                        call_id="c1",
                        name="submit_rag_answer",
                        arguments={"answer": "Alpha.", "sources": ["DOC-A", "DOC-A"]},
                    ),
                ),
                usage=ModelUsage(input_tokens=10, output_tokens=3),
            )

    chunk = RagChunk(
        id="DOC-A::c001",
        document_id="DOC-A",
        title="Alpha",
        description="Use for alpha.",
        path="a.md",
        heading="Facts",
        text="The answer is Alpha.",
        search_text="Alpha",
    )
    result = RagAnswerer(
        FakeBackend(),
        prompt=load_prompt_artifact("prompts/rag/system-v1.md"),
    ).answer(
        "What is the answer?",
        [RagSearchResult(rank=1, chunk=chunk, score=1.0, dense_rank=1)],
    )
    assert result.cited_sources == ("DOC-A",)


def test_hybrid_rerank_configs_are_bounded_and_local() -> None:
    northstar = load_rag_plan("experiments/rag/hybrid-rerank-northstar.yaml")
    tell_aster = load_rag_plan("experiments/rag/hybrid-rerank-tell-aster.yaml")
    for plan in (northstar, tell_aster):
        assert plan.strategy == "hybrid_rerank"
        assert plan.top_k == 6
        assert plan.candidate_k == 24
        assert plan.max_chunks_per_document == 2
        assert plan.candidate_max_chunks_per_document == 4
        assert plan.reranker_model == "cross-encoder/ms-marco-MiniLM-L6-v2"
        assert plan.rerank_batch_size == 16


def test_hybrid_reranker_can_promote_better_candidate(tmp_path) -> None:
    pytest = __import__("pytest")
    np = pytest.importorskip("numpy")
    from rag_baseline.index import LoadedRagIndex, RagIndexManifest
    from rag_baseline.models import RagChunk
    from rag_baseline.retrieval import LocalRetriever

    chunks = [
        RagChunk(
            id="DOC-A::c001",
            document_id="DOC-A",
            title="Alpha",
            description="alpha lexical match",
            path="a.md",
            heading="",
            text="Alpha is mentioned but this is not the requested evidence.",
            search_text="Alpha alpha alpha unrelated.",
        ),
        RagChunk(
            id="DOC-B::c001",
            document_id="DOC-B",
            title="Beta",
            description="answer passage",
            path="b.md",
            heading="",
            text="This passage directly answers the complete question.",
            search_text="This passage directly answers the complete question.",
        ),
    ]
    embeddings = np.asarray([[1.0, 0.0], [0.7, 0.7]], dtype=np.float32)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
    manifest = RagIndexManifest(
        schema_version=1,
        corpus_name="fake",
        corpus_root="fake",
        corpus_sha256="abc",
        embedding_model="fake",
        query_prefix="",
        chunk_words=320,
        overlap_words=64,
        document_count=2,
        chunk_count=2,
        embedding_dimensions=2,
        created_at="now",
    )
    retriever = LocalRetriever(LoadedRagIndex(tmp_path, manifest, chunks, embeddings))

    class FakeEncoder:
        def encode(self, texts, **kwargs):
            return np.asarray([[1.0, 0.0]], dtype=np.float32)

    class FakeReranker:
        def scores(self, question, candidate_chunks):
            return [0.1 if chunk.document_id == "DOC-A" else 0.9 for chunk in candidate_chunks]

    retriever._encoder = FakeEncoder()
    retriever._reranker = FakeReranker()
    result = retriever.hybrid_rerank(
        "alpha question",
        top_k=1,
        candidate_k=2,
        max_chunks_per_document=1,
        candidate_max_chunks_per_document=1,
    )
    assert result[0].chunk.document_id == "DOC-B"
    assert result[0].rerank_score == 0.9
    assert result[0].fusion_rank is not None


def test_hybrid_rerank_rejects_candidate_window_smaller_than_final_window(tmp_path) -> None:
    pytest = __import__("pytest")
    np = pytest.importorskip("numpy")
    from rag_baseline.index import LoadedRagIndex, RagIndexManifest
    from rag_baseline.models import RagChunk
    from rag_baseline.retrieval import LocalRetriever

    chunk = RagChunk(
        id="DOC-A::c001",
        document_id="DOC-A",
        title="Alpha",
        description="alpha",
        path="a.md",
        heading="",
        text="alpha",
        search_text="alpha",
    )
    manifest = RagIndexManifest(
        schema_version=1,
        corpus_name="fake",
        corpus_root="fake",
        corpus_sha256="abc",
        embedding_model="fake",
        query_prefix="",
        chunk_words=320,
        overlap_words=64,
        document_count=1,
        chunk_count=1,
        embedding_dimensions=1,
        created_at="now",
    )
    retriever = LocalRetriever(LoadedRagIndex(tmp_path, manifest, [chunk], np.asarray([[1.0]], dtype=np.float32)))
    with pytest.raises(ValueError, match="candidate_k"):
        retriever.hybrid_rerank("alpha", top_k=2, candidate_k=1)


def test_local_cross_encoder_reranker_uses_cached_model_and_predict_contract(monkeypatch) -> None:
    pytest = __import__("pytest")
    np = pytest.importorskip("numpy")
    import sys
    from types import SimpleNamespace
    from rag_baseline.models import RagChunk
    from rag_baseline.reranking import LocalCrossEncoderReranker

    calls = {}

    class FakeCrossEncoder:
        def __init__(self, model_name, **kwargs):
            calls["init"] = (model_name, kwargs)

        def predict(self, pairs, **kwargs):
            calls["predict"] = (pairs, kwargs)
            return np.asarray([[0.25], [0.75]], dtype=np.float32)

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=FakeCrossEncoder))
    chunks = [
        RagChunk("A::c001", "A", "A", "", "a.md", "", "alpha", "alpha"),
        RagChunk("B::c001", "B", "B", "", "b.md", "", "beta", "beta"),
    ]
    reranker = LocalCrossEncoderReranker(
        model_name="fake-reranker",
        device="mps",
        offline=True,
        batch_size=7,
    )
    assert reranker.scores("question", chunks) == pytest.approx([0.25, 0.75])
    assert calls["init"] == (
        "fake-reranker",
        {"local_files_only": True, "device": "mps"},
    )
    pairs, kwargs = calls["predict"]
    assert pairs == [("question", "alpha"), ("question", "beta")]
    assert kwargs == {
        "batch_size": 7,
        "show_progress_bar": False,
        "convert_to_numpy": True,
    }
