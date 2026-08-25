# RAG comparison results

This document records the first full local-RAG comparison against progressive disclosure on the repository's two benchmark corpora.

The purpose of the experiment is not to prove that one retrieval method is universally superior. It is to measure the trade-off between:

- retrieval/answer reliability;
- number of generation calls;
- document and context selectivity;
- single-document versus genuine multi-document behavior.

## Systems compared

All three systems use the same Northstar and Tell Aster datasets and `gpt-5-nano` for answer generation.

### Progressive disclosure V18

```text
question + compact metadata
        -> atomic evidence plan
        -> selected full document bodies
        -> answer
        -> bounded recovery if needed
```

### Dense RAG K6

```text
question
        -> BGE query embedding
        -> cosine ranking
        -> top 6 chunks
        -> answer
```

### Hybrid RAG K6

```text
question
        -> dense rank ----\
                           -> reciprocal-rank fusion -> top 6 chunks -> answer
        -> BM25 rank -----/
```

The RAG retrieval path is local. Only the answer call uses OpenAI.

## Overall results

| System | Trials | Answer accuracy | Complete discovery | Answer + discovery | Raw citation-strict E2E | Mean docs | Corpus body loaded | Generation calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Progressive disclosure V18** | 180 | **97.2%** | 95.6% | 95.6% | **95.6%** | **1.68** | **2.9%** | 2.16 |
| Dense RAG K6 | 180 | 86.1% | 91.1% | 86.1% | 81.1% | 4.12 | 5.3% | **1.00** |
| Hybrid RAG K6 | 180 | 96.1% | **98.3%** | **96.1%** | 91.1% | 4.40 | 5.5% | **1.00** |

The most important result is the jump from dense to hybrid retrieval:

- complete document discovery: **91.1% -> 98.3%**;
- answer accuracy: **86.1% -> 96.1%**;
- answer + complete discovery: **86.1% -> 96.1%**.

Exact lexical signals therefore matter substantially in these corpora. The effect is especially visible for IDs, codes, context numbers, feature labels, sample names, and other domain-specific identifiers that BM25 can match directly.

## Results by corpus and task type

### Dense RAG K6

| Slice | Trials | Answer | Discovery | Answer + discovery | Raw strict E2E |
| --- | ---: | ---: | ---: | ---: | ---: |
| Northstar single | 40 | 100% | 100% | 100% | 100% |
| Northstar multi | 20 | 95% | 100% | 95% | 55% |
| Tell Aster single | 80 | 91.3% | 95% | 91.3% | 91.3% |
| Tell Aster multi | 40 | 57.5% | 70% | 57.5% | 55% |

Dense semantic retrieval is excellent for compact Northstar single-document lookup but degrades sharply on genuine multi-document Tell Aster questions.

### Hybrid RAG K6

| Slice | Trials | Answer | Discovery | Answer + discovery | Raw strict E2E |
| --- | ---: | ---: | ---: | ---: | ---: |
| Northstar single | 40 | 100% | 100% | 100% | 100% |
| Northstar multi | 20 | **100%** | **100%** | **100%** | 65% |
| Tell Aster single | 80 | 96.3% | 98.8% | 96.3% | 96.3% |
| Tell Aster multi | 40 | 90% | 95% | 90% | 85% |

Hybrid retrieval removes most of the dense-retrieval failure modes. It also shows where progressive disclosure remains strongest: Tell Aster's genuine multi-document questions still achieve **95% answer accuracy with progressive disclosure versus 90% with hybrid K6**.

## Why the raw RAG E2E number needs interpretation

The current RAG evaluator requires the final answer tool call to explicitly cite every benchmark-required document.

Progressive disclosure uses a different attribution mechanism: the source set is derived from the model-authored evidence plan created before the bodies are disclosed. The final answer call is not asked to reconstruct that source list.

This makes the raw RAG E2E score stricter in a way that is not symmetric with the progressive-disclosure path.

Northstar hybrid multi is the clearest example:

- complete discovery: **20/20**;
- correct answer: **20/20**;
- citation-strict E2E: **13/20**.

Those seven failures are not retrieval or answer failures. They are failures to repeat every gold source ID in the final answer tool call.

For cross-architecture comparison, the most useful common measure is therefore:

```text
answer correct
AND
all benchmark-required documents retrieved/disclosed
```

The raw citation-strict metric remains useful inside the RAG experiment and should continue to be reported, but it should not be presented as a perfectly symmetric headline against progressive disclosure.

## Document-level discovery is not enough for chunk RAG

A second RAG-specific caveat is that retrieving *a chunk from the correct document* does not guarantee that the answer-bearing passage from that document was retrieved.

Progressive disclosure normally reveals the complete selected Markdown body. Chunk RAG exposes only top-ranked excerpts.

This distinction explains several dense-RAG failures where the evaluator records complete document discovery but the answer model correctly reports that a requested value is absent from the provided excerpts.

Future RAG reporting should distinguish:

1. **required-document discovery** — did any retrieved chunk belong to each required document?
2. **answer-evidence coverage** — did the retrieved chunks actually contain the evidence needed for every requested answer component?

The current document-discovery metric can therefore be optimistic for chunk RAG.

## Efficiency trade-off

Hybrid RAG is competitive on answer/discovery reliability, but it reaches that result by supplying more material to the answer model.

| Metric | Progressive V18 | Hybrid K6 |
| --- | ---: | ---: |
| Mean documents represented/read | **1.68** | 4.40 |
| p95 documents | 3 | 6 |
| Corpus body loaded | **2.9%** | 5.5% |
| Mean document precision | **86.9%** | 32.8% |
| Generation calls | 2.16 | **1.00** |

The production trade-off is therefore clear:

### Progressive disclosure

Advantages:

- much higher document precision;
- substantially less corpus content disclosed;
- explicit decomposition of independent evidence obligations;
- strong genuine multi-document performance;
- whole-document disclosure avoids many chunk-boundary misses.

Costs:

- normally requires a planning generation call before answering;
- retrieval is model-driven and therefore less deterministic;
- metadata quality matters directly.

### Hybrid RAG

Advantages:

- fully local deterministic retrieval;
- one generation call per normal query;
- excellent aggregate required-document discovery;
- exact identifiers benefit strongly from BM25.

Costs:

- more irrelevant documents/chunks in context;
- chunk selection can retrieve the correct document but the wrong passage;
- one-shot top-K retrieval does not explicitly ensure that each independent multi-document obligation gets representation.

## What the result suggests for production

The experiment does **not** support replacing progressive disclosure with dense-only RAG.

Hybrid RAG is different: it is now a credible production candidate. On the aggregate answer+discovery measure it is effectively tied with, and slightly above, progressive disclosure in this one run (**96.1% vs 95.6%**), while requiring one generation call instead of 2.16.

Progressive disclosure remains more context-efficient and retains the better result on the hardest Tell Aster multi-document slice.

A production decision therefore depends on the workload:

- choose **hybrid RAG** when deterministic local retrieval, latency, and one-call operation matter most;
- choose **progressive disclosure** when minimizing irrelevant context and maintaining explicit multi-source evidence coverage matter most;
- consider a future combined design only after the two pure approaches have been measured sufficiently. A plausible hybrid system would use local RAG for candidate generation and progressive evidence planning for obligation coverage, but that is a separate experiment and should not be conflated with these baselines.

## Scientific limitations

These are single full runs over synthetic corpora that have participated in system development. They establish useful engineering behavior, not a universal production guarantee.

Before making a strong generalization claim, evaluate the frozen systems on another untouched corpus and repeat the full benchmark enough times to measure run-to-run variance.

## Next experiment: hybrid reranking v2

The measured table above remains frozen for the original dense K6 and hybrid K6 baselines. The repository now also contains a `hybrid_rerank` experiment that expands the hybrid candidate set locally and applies a compact cross-encoder before selecting the same final six answer chunks.

This new configuration is intentionally **not** added to the measured comparison table until its retrieval-only and end-to-end suites have been run. See [`rag-reranking.md`](rag-reranking.md).
