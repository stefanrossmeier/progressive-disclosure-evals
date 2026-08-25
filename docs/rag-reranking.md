# Hybrid RAG v2: local reranking

The first local-RAG comparison deliberately kept retrieval simple. Dense K6 used BGE embeddings; hybrid K6 added BM25 and reciprocal-rank fusion (RRF). Hybrid K6 already reached high document recall, but the failure analysis showed an important remaining RAG-specific problem:

> retrieving a chunk from the correct document is not the same as retrieving the answer-bearing chunk from that document.

Hybrid RAG v2 therefore adds a **local cross-encoder reranking stage**. It does not add query rewriting, an agent loop, a hosted vector database, or another generation-model call.

## Architecture

```text
question
  |\
  | +--> BGE dense ranking
  |
  +----> BM25 lexical ranking
             |
             v
      reciprocal-rank fusion
             |
      top 24 candidate chunks
             |
      local cross-encoder
             |
        best 6 chunks
             |
      one answer-model call
```

The default reranker is:

```text
cross-encoder/ms-marco-MiniLM-L6-v2
```

It is a compact MS MARCO passage-ranking cross-encoder available through the same `sentence-transformers` dependency already used by the embedding baseline. Retrieval and reranking remain local. The OpenAI model is still used only for the final answer so the generator remains comparable with progressive disclosure and the previous RAG runs.

## Why rerank instead of simply increasing top-K?

Increasing final `top_k` would improve recall by sending more chunks to the answer model, but it would also increase context noise and weaken the comparison with progressive disclosure.

Reranking separates two tasks:

1. **candidate generation** should be broad and high-recall;
2. **answer-context selection** should be narrow and high-precision.

The v2 defaults are intentionally conservative:

```yaml
strategy: hybrid_rerank
top_k: 6
max_chunks_per_document: 2
rrf_k: 60
candidate_k: 24
candidate_max_chunks_per_document: 4
reranker_model: cross-encoder/ms-marco-MiniLM-L6-v2
rerank_batch_size: 16
```

The final answer context therefore remains six chunks, exactly like hybrid K6. Only the local retrieval pipeline becomes more selective.

## Candidate generation

Candidate generation is the existing hybrid retriever:

- BGE dense ranking;
- BM25 exact/lexical ranking;
- reciprocal-rank fusion.

The fused list is capped at four chunks per document while collecting the 24 reranking candidates. This prevents one long document from consuming most of the candidate window while still allowing multiple sections from a promising document to compete.

## Cross-encoder reranking

A bi-encoder embedding model scores the question and passage independently. A cross-encoder instead processes the question/passage pair jointly and returns a direct relevance score.

That is slower than a single cosine search, but the cross-encoder only sees 24 candidates. On these corpora the extra local work is small compared with an additional remote generation-model call.

The reranker receives the same indexed representation used for search:

```text
document ID
title
description
path
heading context
body chunk
```

Evaluator gold is never provided to candidate generation or reranking.

## Retrieval-only evaluation

Run the v2 retriever locally before spending answer-model calls:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-rerank-northstar.yaml \
  --device mps

python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-rerank-tell-aster.yaml \
  --device mps
```

The retrieval-only report now includes two different diagnostics:

- **complete required-document discovery** — did the final six chunks represent every gold document?
- **retrieved-context answer-evidence coverage** — does the final retrieved context contain the expected answer evidence according to the same deterministic semantic matcher used by the benchmark?

The second metric is important for chunk RAG. A system can have 100% document discovery but still retrieve the wrong section from one of those documents.

## End-to-end evaluation

After retrieval-only results look worthwhile:

```bash
python scripts/run_rag_suite.py \
  --suite experiments/suites/rag-hybrid-rerank-all.yaml \
  --device mps
```

The paid suite still uses one normal answer-model call per case. Reranking itself is local.

## One unattended command

The repository also provides an orchestration script for this complete experiment:

```bash
python scripts/run_rag_v2_pipeline.py \
  --device mps \
  --with-paid-evals
```

It runs, in order:

1. `scripts/check_all.py`;
2. `git diff --check`;
3. a dry-run of the new suite configuration;
4. a fresh rebuild of both local embedding indexes;
5. retrieval-only hybrid K6 baselines for both corpora;
6. retrieval-only hybrid-rerank K6 runs for both corpora;
7. a one-case paid API smoke test;
8. the full 180-case hybrid-rerank E2E suite.

All outputs are placed below one timestamped directory under `results/`, including a `pipeline.log` and `pipeline-summary.json`. With `--with-paid-evals`, the normal path makes 181 answer-model calls: one smoke-test case plus the 180-case suite (a protocol retry can add a call if an answer tool response is malformed).

If the embedding and reranker models have already been downloaded, enforce local-only model loading with:

```bash
python scripts/run_rag_v2_pipeline.py \
  --device mps \
  --offline \
  --with-paid-evals
```

If existing indexes should be reused rather than rebuilt:

```bash
python scripts/run_rag_v2_pipeline.py \
  --device mps \
  --skip-index-build \
  --with-paid-evals
```

The index fingerprint is still checked when it is loaded.

## Experiment discipline

This is intentionally one bounded RAG-improvement round. The existing dense and hybrid K6 configurations remain unchanged as historical baselines.

Do not repeatedly tune reranker settings against the full 180-case benchmark and then treat that same score as an untouched test result. Northstar and Tell Aster are now development/validation corpora for both architectures. A later production-readiness comparison should freeze the chosen progressive-disclosure and RAG systems and evaluate both unchanged on a third corpus.
