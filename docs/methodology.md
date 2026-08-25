# Methodology

## What this repository compares

The repository now evaluates two retrieval architectures over the same Markdown corpora and evaluator:

1. **progressive disclosure** — compact metadata -> explicit evidence plan -> selected full document bodies -> answer;
2. **local RAG** — local dense/hybrid candidate retrieval, optionally followed by local cross-encoder reranking -> top-K chunks -> answer.

The experiment is designed to separate retrieval quality from answer quality while keeping corpus content, benchmark questions, and answer generation as comparable as possible.

Evaluator gold is never supplied to either runtime.

## Progressive-disclosure mechanism

The current progressive-disclosure runtime uses this bounded flow:

1. **Activation metadata** — the model receives compact routing metadata for every available document, not the document bodies.
2. **Atomic evidence planning** — a forced selection action decomposes the question into independently scoped evidence obligations and maps those obligations to candidate documents.
3. **Body disclosure** — only selected full Markdown bodies are disclosed, subject to the document budget.
4. **Evidence resolution** — the model either submits an answer from the disclosed evidence or requests one precise missing evidence obligation.
5. **Bounded recovery** — recovery can use metadata plus compact cross-reference hints learned from bodies already disclosed. It is not an open-ended agent loop.

The normal successful path is:

```text
metadata -> complete evidence plan
selected bodies -> answer
```

The runtime is never told whether an eval case is single- or multi-document, how many gold sources exist, which sources are required, or what values the evaluator expects.

There is no embedding search, vector database, reranker, or hidden gold-path assistance in this path.

## Local-RAG mechanism

The RAG baselines use deterministic Markdown-aware chunks and a local `BAAI/bge-small-en-v1.5` embedding index.

Dense retrieval:

```text
question -> local query embedding -> cosine similarity -> top-K chunks
```

Hybrid retrieval:

```text
question -> dense rank -----\
                            -> reciprocal-rank fusion -> top-K chunks
question -> BM25 rank ------/
```

Hybrid rerank v2 keeps the same candidate generator but reranks a bounded top-24 candidate set with a local cross-encoder before selecting the final top-6 chunks.

Retrieval and reranking make no LLM call. End-to-end RAG uses the same configured OpenAI answer model so the comparison changes retrieval rather than both retrieval and generation.

See [`rag-baselines.md`](rag-baselines.md) for implementation and commands and [`rag-comparison.md`](rag-comparison.md) for measured results.

## Metadata policy

Progressive-disclosure metadata may contain routing vocabulary that the user already supplies, including exact entity IDs or domain terms, when those values help identify the document that owns a requested fact.

Metadata must not expose hidden answer values or evaluator gold.

RAG indexing may use corpus frontmatter, headings, document IDs, and document body text. It must not use dataset questions, required-document IDs, expected answers, or required-evidence annotations.

See [`how-to-corpus-metadata.md`](how-to-corpus-metadata.md).

## What the evaluator knows

For each case, the evaluator may know:

- expected answer values;
- required documents;
- evaluator-only evidence requirements;
- case tags and benchmark labels.

None of these may enter runtime prompts, retrieval indexes, document metadata generated from gold, or model-visible diagnostics.

## Core metrics

### Completion

Did the trial finish without runtime/protocol error?

### Answer accuracy

Does the final answer satisfy the deterministic semantic answer matcher?

### Complete required-document discovery

Did the runtime retrieve/disclose every benchmark-required document?

For progressive disclosure, opening a document normally reveals its complete body.

For chunk RAG, discovery currently means that at least one retrieved chunk belongs to each required document. This is a weaker condition than having the answer-bearing passage from that document in context.

### Document precision

What fraction of the unique documents read/represented by retrieval belong to the required set?

### Knowledge fraction loaded

What fraction of total corpus body content was supplied as detailed knowledge context for the trial?

This measures context selectivity independently from model-call count.

### Model calls

How many generation calls were made during the runtime?

Progressive disclosure normally uses a planning call plus an answer call. Local RAG normally uses one answer-generation call because retrieval itself is local.

## Attribution semantics and cross-architecture comparison

Attribution is implemented differently in the two architectures.

### Progressive disclosure

Attribution is derived from the model-authored evidence plan. The answer stage does not need to reproduce the source list again.

### RAG

The current RAG answer tool explicitly returns source document IDs. Its raw strict E2E rule therefore requires:

```text
answer correct
AND
all required documents retrieved
AND
all required documents cited by the answer tool
```

This makes raw RAG strict E2E useful for evaluating the RAG implementation itself, but not perfectly symmetric with progressive disclosure.

For architecture comparison, always report at least these common dimensions separately:

1. answer accuracy;
2. complete required-document discovery;
3. answer correct + complete required-document discovery;
4. document/context efficiency;
5. model calls.

Do not describe a lower RAG citation-strict score as a retrieval failure when retrieval and answer correctness both succeeded.

## Document discovery versus chunk evidence coverage

Chunk RAG introduces an evaluation distinction that full-document progressive disclosure largely avoids.

A retriever may return the correct document but the wrong chunk from that document. In that case:

```text
document discovery = success
answer-bearing evidence in context = failure
```

When diagnosing RAG failures, inspect the retrieved excerpts before classifying the case as an answer-model reasoning failure.

The retrieval-only evaluator now also measures **answer-evidence coverage** at chunk level using the benchmark's deterministic semantic matcher. This is a diagnostic metric only: expected values are evaluator-side and are never exposed to retrieval or reranking.

## Current benchmark interpretation

The first full comparison shows:

- dense RAG is a useful baseline but is not competitive on genuine multi-document Tell Aster questions;
- hybrid dense+BM25 retrieval is substantially stronger and reaches 98.3% complete document discovery;
- progressive disclosure remains much more selective in document/context usage;
- hybrid RAG uses only one generation call;
- progressive disclosure retains an advantage on the hardest Tell Aster multi-document answer slice.

The result should therefore be treated as a trade-off study rather than evidence that one architecture universally dominates the other.

## Reproducibility discipline

When comparing systems:

- freeze the corpus and dataset fingerprints;
- use the same answer model/settings;
- do not tune one system on another system's test failures and still call the set held out;
- inspect raw traces for failures rather than reasoning only from aggregate percentages;
- report retrieval, answer, attribution, context, and cost dimensions separately;
- preserve historical benchmark versions when evaluator semantics change.

The current corpora have participated in development. A stronger production/generalization claim requires another untouched corpus and repeated full runs.

## Research grounding

The progressive-disclosure side follows the broader context-engineering principle of keeping always-visible context small and exposing deeper material only when it becomes relevant.

References:

- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://openai.com/index/harness-engineering/
