# Retrieval approach selection after the Qwen experiment

This document records the current architecture decision after measuring five retrieval approaches on the same 180 Northstar + Tell Aster evaluation cases.

The purpose is to prevent the project from continuing to optimize every experimental branch. The evidence now supports two finalists, one promising combined follow-up, and several branches that should remain frozen as negative or baseline results.

## Shared comparison metric

The primary cross-architecture metric is **Answer + discovery**:

```text
correct answer
AND
complete required-document discovery
```

This avoids an attribution asymmetry in the current harness. RAG asks the final answer call to explicitly reconstruct all benchmark-required citations, whereas progressive disclosure derives attribution from its earlier evidence plan.

Citation-strict results remain useful for each architecture, but should not be used as the main architecture ranking.

## Overall measured results

| System | Answer | Discovery | Answer + discovery | Single-doc | Multi-doc | Docs | Input tokens | Body loaded | Calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Progressive disclosure V18 | **97.2%** | 95.6% | 95.6% | 96.7% | **93.3%** | **1.68** | 9,773 | **2.9%** | 2.16 |
| Dense RAG K6 | 86.1% | 91.1% | 86.1% | 94.2% | 70.0% | 4.12 | **3,043** | 5.3% | **1.00** |
| Hybrid RAG K6 | 96.1% | 98.3% | **96.1%** | 97.5% | **93.3%** | 4.40 | 3,102 | 5.5% | **1.00** |
| Hybrid + global reranker | 92.8% | 97.8% | 91.7% | **99.2%** | 76.7% | 4.27 | 3,155 | 5.5% | **1.00** |
| Qwen hierarchical hybrid K8 | 92.2% | **99.4%** | 92.2% | **99.2%** | 78.3% | 5.27 | 3,720 | 6.5% | **1.00** |

## Qwen result

The Qwen pipeline completed the full unattended process successfully, including deterministic checks, model download, index construction, retrieval-only evaluation, smoke test, and all 180 paid E2E cases.

Retrieval-only results:

| Corpus | Complete discovery | Required-doc recall | Answer-evidence coverage | Mean unique docs | Body loaded |
| --- | ---: | ---: | ---: | ---: | ---: |
| Northstar | **100%** | 100% | **100%** | 5.8 | 14.3% |
| Tell Aster | **99.2%** | 99.6% | 93.3% | 5.0 | 2.6% |

E2E by slice:

| Slice | Answer | Discovery | Answer + discovery |
| --- | ---: | ---: | ---: |
| Northstar single | 97.5% | **100%** | 97.5% |
| Northstar multi | 90% | **100%** | 90% |
| Tell Aster single | **100%** | **100%** | **100%** |
| Tell Aster multi | **72.5%** | 97.5% | **72.5%** |

The pipeline therefore validates the retrieval premise but not the full architecture premise. It is possible to achieve nearly perfect document recall while lowering end-to-end answer quality.

### Why the Qwen pipeline regressed

Fourteen cases have incorrect final answers. Only one of them is a complete-document discovery miss. On many of the remaining failures, all required documents are present but one answer-bearing passage is absent, or the answer model is distracted by competing context.

Examples include:

- `TA-M-002`: all required documents are represented, but the final context lacks the date range needed from the correct dating document;
- `TA-M-011`: answer-evidence coverage is marked complete, yet the final answer rejects the correct relation in favor of nearby competing burial evidence;
- `EVAL-010`, `EVAL-049`, `EVAL-053`: required evidence is present, but the answer model applies the wrong branch/override from the broader context.

The Qwen hierarchy also increases final answer context: mean input is about 3.7k tokens versus 3.1k for simple hybrid K6, and it represents about 5.3 documents rather than 4.4.

Measured local retrieval latency is also substantially higher in the current implementation: median Qwen retrieval is about 7.1 seconds per question on the measured MPS setup, versus roughly 52 ms for the original hybrid K6 after warm-up.

The full Qwen hierarchy should therefore remain a measured experiment, not become the main RAG branch.

## Paired Progressive vs Hybrid analysis

The two finalists have complementary failure modes.

Across the 180 cases using Answer + discovery:

```text
both pass:               165
Hybrid only passes:        8
Progressive only passes:   7
both fail:                 0
```

Progressive-only successes:

```text
TA-M-001
TA-M-004
TA-M-015
TA-M-028
TA-S-001
TA-S-043
TA-S-076
```

Hybrid-only successes:

```text
EVAL-041
EVAL-045
TA-M-007
TA-M-023
TA-S-024
TA-S-027
TA-S-065
TA-S-080
```

This union result is a diagnostic, not an implemented 100% system. It is especially important because both corpora have participated in development. The result should be used to motivate a fallback experiment, not as a production accuracy claim.

## Decision

### Finalist A: Hybrid RAG K6

This is the strongest production-shaped baseline.

Why keep it:

- best overall Answer + discovery result at 96.1%;
- 98.3% complete source discovery;
- one answer-model call;
- roughly 3.1k mean answer-model input tokens;
- fast local retrieval;
- much simpler than the Qwen hierarchy;
- no evidence that global reranking improves it.

Recommended next work:

1. Keep the architecture fixed.
2. Test `Qwen3-Embedding-0.6B` as an embedding-only replacement for BGE.
3. Run retrieval-only K/chunk-size/max-chunks-per-document ablations.
4. Select changes by answer-bearing evidence coverage and multi-document recall, not raw document recall alone.
5. Only pay for another 180-case E2E run after a retrieval-only change provides a clear improvement.

The embedding-only Qwen experiment is deliberately not the same as the measured Qwen hierarchy. It would isolate whether the stronger embedding model contributes useful recall without importing K8, hierarchical context packing, or reranker behavior.

### Finalist B: Progressive Disclosure V18

Why keep it:

- highest overall answer accuracy at 97.2%;
- best Tell Aster multi-document answer result at 95%;
- smallest evidence footprint by a wide margin;
- explicit evidence obligations make complex relational questions easier to compose;
- failure modes differ from hybrid RAG.

Recommended next work:

1. Stop case-by-case prompt tuning against the current 180 questions.
2. Add production-oriented abstention/fallback semantics where evidence is unresolved.
3. Investigate reducing planning-token overhead without removing explicit evidence planning.
4. Freeze the architecture before a third-corpus benchmark.

### Combined candidate: Hybrid-first with Progressive fallback

This is the most promising new architecture suggested by the measured results.

The target production behavior is:

```text
simple/high-confidence query
    -> local Hybrid K6
    -> one answer call

ambiguous/compound/incomplete-evidence query
    -> progressive evidence planning
    -> selective disclosure/recovery
    -> answer
```

The hard part is the fallback trigger. It cannot use evaluator gold.

Potential runtime signals worth testing include:

- multiple independent clauses or contrast/counterfactual language in the question;
- low separation between top document scores;
- insufficient document diversity in the retrieved set;
- answer-stage declaration that one or more requested facts are unsupported;
- contradictions among retrieved passages;
- an evidence-coverage verifier operating only on retrieved evidence.

Do not assume that the paired union automatically transfers to such a router. Measure the router as its own system.

## Branches to stop

### Dense RAG K6

Keep it only as the minimal semantic-search baseline. Hybrid retrieval dominates it.

### Global cross-encoder reranking

Do not optimize this branch further. It improves single-document ranking but reduces multi-document diversity and answerability.

### Full Qwen hierarchical hybrid K8

Do not optimize this full architecture further. Its 99.4% discovery result is useful evidence that retrieval recall is not the current bottleneck. Reuse individual Qwen components only in controlled ablations.

## Recommended sequence

With limited optimization budget, use this order:

1. **Hybrid K6 ablation:** Qwen embedding only + small retrieval-only parameter grid.
2. **Freeze the best Hybrid K6 variant.**
3. **Keep Progressive V18 frozen** except for production fallback/abstention work.
4. **Prototype one Hybrid -> Progressive fallback strategy.**
5. Freeze all three.
6. Evaluate them unchanged on a **third untouched corpus**.

The third corpus is more valuable than squeezing another few points from Northstar or Tell Aster, because both current corpora are now development data.
