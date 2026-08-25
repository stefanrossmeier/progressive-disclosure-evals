# Local RAG baselines

This repository contains two deliberately small RAG baselines for direct comparison with the progressive-disclosure runtime:

- **Dense RAG** — local BGE embeddings + cosine similarity.
- **Hybrid RAG** — the same dense retrieval plus an in-repository BM25 implementation combined with reciprocal-rank fusion (RRF).

The retrieval side is fully local. The end-to-end benchmark deliberately keeps the same OpenAI answer model used by progressive disclosure so the experiment changes the **retrieval mechanism**, not both retrieval and generation at once.

## What the comparison is testing

The experiment asks whether a conventional RAG pipeline can outperform progressive disclosure on the same corpora and evaluator while using comparable amounts of answer context.

The comparison holds these constant:

- Northstar and Tell Aster corpora;
- Northstar `eval-v1` and Tell Aster `tell-aster-eval-v2` datasets;
- deterministic answer grading;
- required-document discovery semantics;
- source-attribution requirements;
- the answer model and its reasoning/text settings.

Only retrieval changes.

```text
Progressive disclosure
question
  -> metadata evidence plan
  -> selected document bodies
  -> answer

Dense RAG
question
  -> local embedding
  -> cosine similarity
  -> top-K chunks
  -> answer

Hybrid RAG
question
  -> dense ranking -----\
                         -> reciprocal-rank fusion -> top-K chunks -> answer
  -> BM25 ranking ------/
```

## Important locality boundary

Indexing and retrieval are fully local. The default embedding model is `BAAI/bge-small-en-v1.5`, run through `sentence-transformers`; saved embeddings are searched with NumPy. No hosted vector database, embedding API, LangChain, or LlamaIndex is required.

The **retrieval-only** evaluation is therefore fully local and makes no OpenAI calls.

The **end-to-end** RAG evaluation still calls the configured OpenAI answer model once per normal trial. This is intentional: it keeps the generator equal to the progressive-disclosure benchmark. A future experiment can replace the answer model with a local LLM, but that would answer a different question.

## Installation

RAG dependencies are kept separate because `sentence-transformers` pulls in PyTorch and a larger local ML stack.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-rag.txt
```

The first model load downloads the embedding model from Hugging Face unless it is already cached. The model is around the size of a small BERT encoder, but PyTorch and Transformers add substantially more installation weight.

An unauthenticated Hugging Face warning is harmless for this experiment. Setting `HF_TOKEN` is optional and only affects Hub rate limits/download behavior.

### Apple Silicon

Use MPS if available:

```bash
python scripts/build_rag_index.py --all --device mps
```

CPU is also fast enough for these corpora:

```bash
python scripts/build_rag_index.py --all --device cpu
```

After the model is cached, `--offline` enforces local-only model loading:

```bash
python scripts/build_rag_index.py --all --device mps --offline
```

## Environment for paid E2E evaluation

Retrieval-only runs do **not** need OpenAI credentials.

End-to-end runs do. Use the same settings as the progressive-disclosure evaluation, for example in `.env`:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-nano
OPENAI_REASONING_EFFORT=low
OPENAI_TEXT_VERBOSITY=low
```

RAG config files contain:

```yaml
model: env:OPENAI_MODEL
```

The runner resolves that environment reference only when an answer-model run starts. Retrieval-only evaluation can therefore load the same config without requiring `OPENAI_MODEL`.

## Chunking and index contents

The chunker is deterministic and Markdown-aware. Defaults:

```text
target size: 320 words
overlap:      64 words
```

The indexed/search representation contains compact routing context:

```text
document ID
title
description
path
heading context
body chunk
```

The answer model receives only the retrieved source labels and body excerpts. Evaluator-only fields such as required document IDs, expected values, and gold evidence never enter the index or answer prompt.

Each chunk records its original `document_id`, which allows the existing evaluator to score RAG at the same document-evidence level as progressive disclosure.

Generated indexes live under:

```text
results/rag-indexes/
  northstar/
    manifest.json
    chunks.jsonl
    embeddings.npy
  tell-aster/
    manifest.json
    chunks.jsonl
    embeddings.npy
```

The manifest includes a corpus fingerprint. Evaluation refuses to use an index after its source corpus changes, so rebuild the index whenever corpus files or frontmatter change.

## Build the indexes

Build both corpora:

```bash
python scripts/build_rag_index.py \
  --all \
  --device mps
```

Or individually:

```bash
python scripts/build_rag_index.py --corpus northstar --device mps
python scripts/build_rag_index.py --corpus tell-aster --device mps
```

One index per corpus supports both dense and hybrid retrieval. BM25 is generated in memory from `chunks.jsonl`; it does not need a separate persisted index.

## Retrieval configuration

The initial benchmark uses `top_k: 6` and at most two chunks from a single document.

### Dense

```yaml
strategy: dense
top_k: 6
max_chunks_per_document: 2
```

Dense retrieval embeds the question using the BGE retrieval query prefix and computes cosine similarity against normalized saved chunk embeddings.

### Hybrid

```yaml
strategy: hybrid
top_k: 6
max_chunks_per_document: 2
rrf_k: 60
```

Hybrid retrieval combines:

1. BGE dense rank;
2. local BM25 lexical rank;
3. reciprocal-rank fusion.

The lexical tokenizer preserves exact identifiers such as `MIG-2`, `C-511`, `TA-EXC-06`, and `Lattice-3`, which are useful signals that semantic embeddings may underweight.

## Run retrieval-only evaluation first

This stage is cheap and fully local. Run it before spending answer-model calls.

Dense Northstar:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/dense-northstar.yaml \
  --device mps
```

Dense Tell Aster:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/dense-tell-aster.yaml \
  --device mps
```

Hybrid Northstar:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-northstar.yaml \
  --device mps
```

Hybrid Tell Aster:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-tell-aster.yaml \
  --device mps
```

A larger retrieval window can be tested without changing the config file:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-tell-aster.yaml \
  --top-k 10 \
  --device mps
```

The retrieval-only report measures:

- complete required-document discovery;
- required-document recall;
- document precision;
- first required chunk rank;
- unique documents represented by retrieved chunks;
- retrieved chunk count;
- corpus-body fraction loaded.

The main precondition for a useful paid benchmark is **complete required-document discovery**. If retrieval itself cannot match the progressive-disclosure discovery rate, answer generation cannot repair that strict E2E failure.

## Run end-to-end evaluation

Once retrieval-only results are worth testing, run dense RAG:

```bash
python scripts/run_rag_suite.py \
  --suite experiments/suites/rag-dense-all.yaml \
  --device mps
```

Then hybrid RAG:

```bash
python scripts/run_rag_suite.py \
  --suite experiments/suites/rag-hybrid-all.yaml \
  --device mps
```

Run one corpus/config directly when debugging:

```bash
python scripts/run_rag_evals.py \
  --config experiments/rag/hybrid-tell-aster.yaml \
  --device mps
```

Limit an E2E run while validating API setup:

```bash
python scripts/run_rag_evals.py \
  --config experiments/rag/dense-northstar.yaml \
  --device mps \
  --limit 1
```

This one-case smoke test is recommended before launching a full 180-case suite.

## Strict E2E semantics

A RAG trial passes strict E2E only when all three conditions hold:

1. the answer satisfies the same deterministic semantic grader as progressive disclosure;
2. every evaluator-required document is represented by at least one retrieved chunk;
3. every evaluator-required document is cited by the answer model.

This is intentionally stricter than ordinary RAG answer accuracy. It prevents an apparently correct answer from hiding a retrieval miss or unsupported inference.

## Context accounting

RAG does not count an entire source document as loaded merely because one chunk was retrieved. Its knowledge fraction is based on the actual retrieved body excerpts.

Useful comparison metrics are therefore:

- strict E2E success;
- answer accuracy;
- complete discovery;
- attribution;
- document precision;
- unique documents represented;
- chunk count;
- mean/p95 context loaded;
- model calls;
- retrieval latency;
- corpus-body fraction loaded.

## Compare RAG with progressive disclosure

After running the V18 progressive-disclosure result plus dense and hybrid RAG:

```bash
python scripts/compare_retrieval_results.py \
  --result progressive=results/<eval-all-v18> \
  --result dense=results/<rag-dense-result> \
  --result hybrid=results/<rag-hybrid-result> \
  --output results/retrieval-comparison.md
```

The intended first experiment is:

| System | Retrieval | Answer calls | Initial K |
| --- | --- | ---: | ---: |
| Progressive disclosure V18 | metadata planning + bounded disclosure | ~2 normally | n/a |
| Dense RAG | local BGE cosine search | 1 | 6 chunks |
| Hybrid RAG | local BGE + BM25 + RRF | 1 | 6 chunks |

If K6 has insufficient discovery, evaluate K10 **before** adding rerankers or other machinery.

## Troubleshooting

### Every paid RAG trial immediately prints `ERROR`

First run a one-case smoke test:

```bash
python scripts/run_rag_evals.py \
  --config experiments/rag/dense-northstar.yaml \
  --device mps \
  --limit 1
```

The runner prints the exception type and message for API/runtime errors. Do not continue a full suite until the smoke test succeeds.

Check:

```bash
python - <<'PY'
import os
print("OPENAI_API_KEY set:", bool(os.getenv("OPENAI_API_KEY")))
print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL"))
PY
```

The RAG answer tool uses OpenAI strict function calling. Strict mode supports only a subset of JSON Schema, so provider-facing schemas deliberately avoid unsupported validation keywords such as `uniqueItems` and string/array length constraints. Non-empty answers, valid source IDs, and source de-duplication are enforced client-side instead.

### Console showed `env:OPENAI_MODEL`

That text is the configuration reference, not a model identifier. Paid runs now print the resolved model name in per-case output. The manifest also records the resolved model.

### Index fingerprint mismatch

The corpus changed after the index was built. Rebuild:

```bash
python scripts/build_rag_index.py --all --device mps
```

### Hugging Face warning about unauthenticated requests

This does not affect local retrieval correctness. Set `HF_TOKEN` if desired, or use `--offline` after the embedding model is cached.

### MPS problems

Retry with CPU:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-tell-aster.yaml \
  --device cpu
```

These corpora are small enough that CPU retrieval is still practical.

## Design intentionally omitted from the first baseline

The initial RAG comparison does not include:

- vector databases;
- rerankers;
- query rewriting;
- HyDE;
- multi-query retrieval;
- parent/child retrieval;
- knowledge graphs;
- agent loops;
- LangChain/LlamaIndex abstractions.

The point is to establish what a small, inspectable dense or hybrid RAG system achieves before attributing gains to a more complicated retrieval stack.

## Measured baseline results

The first complete dense and hybrid K6 runs are documented in [`rag-comparison.md`](rag-comparison.md).

Headline results over the shared 180-case benchmark:

| System | Answer accuracy | Complete discovery | Answer + discovery | Mean docs | Knowledge loaded | Generation calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dense RAG K6 | 86.1% | 91.1% | 86.1% | 4.12 | 5.3% | 1.00 |
| Hybrid RAG K6 | **96.1%** | **98.3%** | **96.1%** | 4.40 | 5.5% | 1.00 |

Hybrid retrieval is therefore the meaningful conventional-RAG baseline for this repository. Dense-only retrieval remains useful as an ablation showing how much exact lexical matching contributes.

### Attribution comparability warning

The RAG result files also report citation-strict E2E values of 81.1% (dense) and 91.1% (hybrid). The current RAG answer tool must explicitly emit every required source ID. Progressive disclosure derives attribution from its earlier evidence plan instead.

Do not compare those raw RAG citation-strict values to progressive disclosure without stating this asymmetry. For the common retrieval+answer question, report **answer correctness + complete required-document discovery** as well.

### Chunk evidence coverage

`complete_discovery` currently means that at least one retrieved chunk belongs to every required document. It does **not** prove that the retrieved chunks contain every answer-bearing passage from those documents.

This distinction matters for chunk RAG and should be considered when debugging a case classified as an answer/application failure. Inspect the actual top-K excerpts before deciding that the answer model failed despite sufficient evidence.
