# Qwen hierarchical-hybrid RAG pipeline

This document describes the separate Qwen RAG experiment under `src/qwen_rag_pipeline/`.
It does **not** replace or modify the measured `rag_baseline` implementations. Dense K6,
hybrid K6, and the global cross-encoder reranking experiment remain frozen for comparison.

The purpose of this pipeline is to test a more production-shaped local retrieval stack after
the original hybrid baseline reached high document recall but still showed two recurring
multi-document problems:

1. the right document can be retrieved while the wrong chunk from that document is sent to
   the answer model;
2. globally reranking chunks by pointwise relevance can collapse evidence diversity and
   remove one of the documents needed for a compound question.

The Qwen pipeline addresses both problems structurally rather than by tuning individual eval
cases.

## Measured result

The complete Qwen pipeline has now been run over all 180 Northstar + Tell Aster cases.

| Metric | Result |
| --- | ---: |
| Answer accuracy | 92.2% |
| Complete document discovery | **99.4%** |
| Answer + discovery | 92.2% |
| Citation-strict E2E | 87.8% |
| Mean documents represented | 5.27 |
| Mean answer-model input tokens | 3,720 |
| Mean corpus body loaded | 6.5% |
| Generation calls | 1.00 |

The architecture succeeds extremely well at **finding candidate documents**, but does not
improve end-to-end answering over the simpler hybrid K6 baseline. The main regression is
multi-document composition:

| Slice | Answer accuracy | Complete discovery | Answer + discovery |
| --- | ---: | ---: | ---: |
| Northstar single | 97.5% | 100% | 97.5% |
| Northstar multi | 90% | 100% | 90% |
| Tell Aster single | **100%** | **100%** | **100%** |
| Tell Aster multi | **72.5%** | 97.5% | **72.5%** |

Retrieval-only evaluation also shows the distinction between document recall and usable
passage coverage. Northstar reaches 100% answer-evidence coverage, while Tell Aster overall
reaches 93.3%; Tell Aster multi reaches only 80% answer-evidence coverage.

The current measured conclusion is therefore:

> **Do not continue optimizing the complete Qwen hierarchical K8 architecture as the primary
> RAG branch.** Preserve it as an experiment showing that near-perfect source recall does not
> guarantee a good multi-document answer context.

The Qwen models remain useful for controlled component ablations. In particular,
`Qwen3-Embedding-0.6B` should be tested as a drop-in embedding replacement inside the frozen
hybrid K6 architecture without also changing chunking, K, context packing, or reranking.

See [`approach-selection.md`](approach-selection.md) for the current architecture decision.

## Architecture

```text
                               LOCAL
question
   |
   +--> Qwen3-Embedding-0.6B query embedding
   |
   +--> document dense search ----+
   |                              |
   +--> document BM25 ------------+--> RRF --> candidate documents
                                             (document order is preserved)
                                                        |
                              +-------------------------+-------------------------+
                              |                         |                         |
                         document A                document B                document C ...
                              |                         |                         |
                    dense + BM25 chunks       dense + BM25 chunks       dense + BM25 chunks
                              |                         |                         |
                         local RRF                  local RRF                  local RRF
                              |                         |                         |
                              +------------ Qwen3-Reranker-0.6B ---------------+
                                           inside each document only
                                                        |
                                      coverage-aware context packing
                                      - distinct documents first
                                      - extra passages second
                                                        |
                                                   top-K chunks
                                                        |
                               HOSTED ANSWER MODEL       |
                                                        v
                                                   gpt-5-nano
                                                        |
                                                      answer
```

The critical difference from the previous `hybrid_rerank` experiment is that the Qwen
reranker **never decides which documents survive globally**. Dense + BM25 + reciprocal-rank
fusion chooses and orders candidate documents. The Qwen reranker is used only to choose the
best passages *inside* each candidate document.

This preserves multi-document coverage while still attacking the `right document / wrong
chunk` failure mode.

## Models

The experiment uses two official Qwen models:

| Role | Model | Pinned revision | Relevant properties |
| --- | --- | --- | --- |
| Embedding | `Qwen/Qwen3-Embedding-0.6B` | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | 0.6B, 32K context, 1024 dimensions, instruction-aware |
| Reranking | `Qwen/Qwen3-Reranker-0.6B` | `e61197ed45024b0ed8a2d74b80b4d909f1255473` | 0.6B, 32K context, instruction-aware |

Both upstream models are Apache-2.0 licensed.

Sources:

- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- https://arxiv.org/abs/2506.05176

Qwen recommends using an English task instruction for retrieval. The index manifest stores the
exact query instruction used by this experiment:

```text
Given a knowledge-base question, retrieve all documents and passages that contain
 evidence needed to answer it. Favor complementary evidence for multi-part questions.
```

The query embedding input is formatted as:

```text
Instruct: <instruction>
Query: <question>
```

Documents and chunks are embedded without a query instruction.

The reranker also uses a task-specific English instruction:

```text
Given a knowledge-base question and a passage from a candidate document, judge whether
the passage contains evidence needed to answer any part of the question.
```

## Explicit, reproducible model downloads

Unlike the earlier RAG baseline, normal Qwen indexing and retrieval never resolve a Hugging
Face model name at runtime. Models are downloaded explicitly into a repository-local model
folder and every subsequent model load uses that local path with `local_files_only=True`.

Install the optional dependencies:

```bash
pip install -r requirements-qwen-rag.txt
```

Show exactly what will be downloaded without network access:

```bash
python scripts/download_qwen_rag_models.py --dry-run
```

Download the two pinned snapshots:

```bash
python scripts/download_qwen_rag_models.py
```

The default layout is:

```text
models/qwen-rag/
├── model-manifest.json
├── Qwen3-Embedding-0.6B/
└── Qwen3-Reranker-0.6B/
```

`models/` is gitignored. Do not commit model weights to this repository.

`model-manifest.json` records the exact upstream repository, immutable revision, and local
path for both models.

An `HF_TOKEN` is optional for these public models. If present in the environment, the download
script passes it to `huggingface_hub`; it is useful only for Hub rate limits. Corpus content and
eval queries are never sent to Hugging Face.

After the models have been downloaded, the retrieval pipeline itself can run without Hugging
Face network access.

## Index design

Qwen RAG has a separate index namespace:

```text
results/qwen-rag-indexes/
├── northstar/
└── tell-aster/
```

It does not read or overwrite `results/rag-indexes/` from the existing baseline.

Each corpus index contains:

```text
manifest.json
documents.jsonl
chunks.jsonl
document-embeddings.npy
chunk-embeddings.npy
```

### Document index

Each whole document is indexed as:

```text
Document ID
Title
Description
Path
Full Markdown body
```

The current corpora are small enough that whole-document embeddings are practical, while
Qwen3-Embedding-0.6B supports a 32K context window.

The document layer exists to answer the first retrieval question:

> Which documents collectively look capable of satisfying this question?

### Chunk index

The Qwen experiment intentionally reuses the same deterministic Markdown-aware chunker as the
existing RAG baselines. That keeps chunking constant when comparing retrieval models and
retrieval architecture.

Default chunk settings remain:

```text
target:  320 words
overlap: 64 words
```

The chunk layer answers the second retrieval question:

> Which passages inside each candidate document best contain the requested evidence?

### Index fingerprinting

The manifest includes a SHA-256 over the corpus Markdown files. Evaluation refuses to use an
index after the corpus changes.

Rebuild the indexes after any corpus change.

## Build the indexes

Apple Silicon:

```bash
python scripts/build_qwen_rag_index.py \
  --all \
  --device mps
```

CPU:

```bash
python scripts/build_qwen_rag_index.py \
  --all \
  --device cpu
```

The command requires the locally downloaded embedding model. It never downloads model files
implicitly.

## Retrieval algorithm

The default experiment configuration is intentionally identical across both corpora:

```yaml
top_k: 8
document_candidates: 12
chunk_candidates_per_document: 4
unique_document_slots: 5
rrf_k: 60
rerank_batch_size: 8
rerank_instruction: >-
  Given a knowledge-base question and a passage from a candidate document, judge whether
  the passage contains evidence needed to answer any part of the question.
```

No Northstar-specific or Tell-Aster-specific retrieval parameter is used.

### Stage 1: document candidate generation

For every document the pipeline computes:

- cosine similarity from `Qwen3-Embedding-0.6B`;
- BM25 lexical relevance;
- reciprocal-rank fusion over the two rankings.

The top 12 documents become candidates.

Exact identifiers therefore benefit from BM25 while semantic paraphrases benefit from the
embedding model.

### Stage 2: chunk candidates inside each document

For each candidate document, its chunks are ranked using local dense + BM25 + RRF retrieval.
Only the top four chunk candidates from that document go to the reranker.

### Stage 3: within-document Qwen reranking

`Qwen3-Reranker-0.6B` scores the bounded candidate passages. The score is used only to choose
passage order **within the same document**.

This constraint is deliberate. The earlier global reranking experiment improved many
single-document cases but hurt multi-document evidence coverage because multiple individually
relevant chunks from one topic could displace a different required source.

### Stage 4: coverage-aware context packing

The answer context is assembled in two passes.

First, one best chunk is taken from each of the top five candidate documents. This reserves
coverage for complementary evidence sources.

Second, the remaining three K8 slots are filled with the next-best chunks from those documents,
in document-rank order. This gives high-ranked documents room for a second passage where the
answer spans chunk boundaries.

If short documents do not fill all eight positions, best chunks from lower-ranked candidate
documents are admitted as fallback.

The context packer therefore optimizes a different objective from pointwise global reranking:

> preserve strong document-level retrieval diversity, then improve passage choice inside the
> selected documents.

## Why K8?

The measured hybrid K6 baseline was already strong at document discovery but still failed some
multi-document questions because one required fact was absent from the six answer-bearing
chunks. The separate Qwen experiment uses K8 to give hierarchical retrieval room for five
candidate documents plus up to three additional passages.

This is an explicit accuracy/context trade-off and must be reported in the benchmark. It does
not change the existing K6 baseline.

The retrieval-only report measures the resulting corpus-body fraction and unique-document count
so the extra context cost is visible.

## Retrieval-only evaluation

Run this before paying for answer generation.

Northstar:

```bash
python scripts/run_qwen_rag_retrieval_eval.py \
  --config experiments/qwen-rag/northstar.yaml \
  --device mps
```

Tell Aster:

```bash
python scripts/run_qwen_rag_retrieval_eval.py \
  --config experiments/qwen-rag/tell-aster.yaml \
  --device mps
```

The retrieval-only evaluator makes **zero OpenAI calls** and reports:

- complete required-document discovery;
- mean required-document recall;
- document precision;
- retrieved-context answer-evidence coverage;
- unique documents represented;
- corpus-body fraction loaded;
- selected chunks and their document/reranking diagnostics.

The `answer_evidence_coverage` metric is evaluator-only. Expected-answer values are used after
retrieval to diagnose whether the final chunk context actually contains the answer-bearing
evidence. Gold values are never provided to the retriever.

## End-to-end evaluation

A one-case smoke test should precede the paid suite:

```bash
python scripts/run_qwen_rag_evals.py \
  --config experiments/qwen-rag/northstar.yaml \
  --device mps \
  --limit 1
```

Full suite:

```bash
python scripts/run_qwen_rag_suite.py \
  --suite experiments/suites/qwen-rag-all.yaml \
  --device mps
```

This runs the same 180 Northstar + Tell Aster cases used by the existing systems.

Retrieval remains fully local. `gpt-5-nano` is intentionally retained for the answer stage so
retrieval architecture remains the variable under test.

## Evaluation semantics

The Qwen pipeline reports two end-to-end notions.

### Comparable answer + discovery

The primary architecture-comparison metric is:

```text
answer correct
AND
all benchmark-required documents represented in retrieved context
```

This is the closest symmetric comparison between progressive disclosure and RAG.

### Citation-strict success

For compatibility with the existing RAG reports, the final answer is additionally asked to cite
source document IDs. Citation-strict success requires:

```text
answer correct
AND
all required documents retrieved
AND
all required documents explicitly cited by the final answer call
```

Keep this as a secondary metric because progressive disclosure derives attribution from its
evidence plan instead of asking the final answer call to reconstruct the complete source set.

## One-command unattended run

To run deterministic checks, download the pinned models, build both indexes, run both local
retrieval evals, execute a one-case paid smoke test, and then run the full paid suite:

```bash
python scripts/run_qwen_rag_pipeline.py \
  --device mps \
  --download-models \
  --with-paid-evals
```

The combined command stops immediately if an earlier stage fails, so a broken local setup does
not proceed to the paid suite.

Outputs are grouped below one directory:

```text
results/<timestamp>-qwen-rag-pipeline/
├── pipeline.log
├── pipeline-summary.json
├── retrieval-northstar/
├── retrieval-tell-aster/
├── e2e-smoke/
└── e2e/
```

After the initial model download, subsequent runs can omit `--download-models`.

A no-side-effect command-plan check is available as:

```bash
python scripts/run_qwen_rag_pipeline.py \
  --device mps \
  --with-paid-evals \
  --dry-run
```

## Clean setup from a fresh clone

```bash
# 1. Install the Qwen-RAG dependencies.
pip install -r requirements-qwen-rag.txt

# 2. Inspect pinned model inputs.
python scripts/download_qwen_rag_models.py --dry-run

# 3. Download the exact pinned upstream snapshots.
python scripts/download_qwen_rag_models.py

# 4. Run repository validation.
python -m pytest
python scripts/check_all.py

# 5. Build both Qwen indexes.
python scripts/build_qwen_rag_index.py --all --device mps

# 6. Run free retrieval-only evaluation.
python scripts/run_qwen_rag_retrieval_eval.py \
  --config experiments/qwen-rag/northstar.yaml --device mps
python scripts/run_qwen_rag_retrieval_eval.py \
  --config experiments/qwen-rag/tell-aster.yaml --device mps

# 7. Smoke-test answer generation.
python scripts/run_qwen_rag_evals.py \
  --config experiments/qwen-rag/northstar.yaml --device mps --limit 1

# 8. Run the full paid benchmark.
python scripts/run_qwen_rag_suite.py \
  --suite experiments/suites/qwen-rag-all.yaml --device mps
```

## What this experiment does not do

The pipeline intentionally does not add:

- an external vector database;
- LangChain, LlamaIndex, or an agent framework;
- LLM query rewriting;
- HyDE;
- LLM-generated query decomposition;
- a local Qwen chat model for final answers.

A local generative Qwen model could make the entire application offline, but that would no
longer be a controlled retrieval comparison with the existing `gpt-5-nano` benchmarks. It
should be evaluated separately if fully local generation becomes a product requirement.

## Expected research question

This pipeline should answer whether a more complete conventional RAG design can improve the
remaining multi-document failures while retaining RAG's production advantages:

- local deterministic retrieval;
- one hosted answer-model call;
- no agentic retrieval loop;
- no external search infrastructure.

The important comparison after the run is not merely accuracy. Report together:

- answer accuracy;
- complete required-document discovery;
- answer + discovery;
- answer-evidence coverage;
- unique documents and chunks loaded;
- corpus-body fraction loaded;
- total answer-model input tokens;
- retrieval latency;
- generation calls.
