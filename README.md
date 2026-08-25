# Progressive Disclosure Evals

An eval-first comparison of **progressive disclosure** and several **local RAG retrieval architectures** for LLM knowledge retrieval.

Every measured system uses the same Northstar + Tell Aster corpora, the same evaluation datasets, and `gpt-5-nano` for final answer generation. The repository is intentionally structured so that retrieval architecture can be changed without changing evaluator gold or answer scoring.

The project asks two practical questions:

> **How far can progressive disclosure go with a compact metadata map and selective body loading?**

> **Which local RAG design provides the strongest production trade-off in reliability, context cost, latency, and model calls?**

## What has been tried

Five retrieval architectures have now been measured over the same 180-question benchmark.

```text
Progressive disclosure V18
question + document metadata
        -> atomic evidence plan
        -> selected document bodies
        -> answer

Dense RAG K6
question
        -> local dense chunk retrieval
        -> top 6 chunks
        -> answer

Hybrid RAG K6
question
        -> dense + BM25
        -> reciprocal-rank fusion
        -> top 6 chunks
        -> answer

Hybrid + global reranker
question
        -> hybrid candidate retrieval
        -> cross-encoder reranking
        -> top 6 chunks
        -> answer

Qwen hierarchical hybrid RAG
question
        -> Qwen document retrieval
        -> per-document chunk retrieval
        -> Qwen within-document reranking
        -> coverage-aware K8 context
        -> answer
```

The later systems were added as controlled experiments. Dense and hybrid K6 remain frozen baselines; the global-reranker and Qwen pipelines test whether more sophisticated local retrieval improves the hard multi-document cases.

## Current results

### Primary comparison

For cross-architecture comparison, **Answer + discovery** means:

```text
answer is correct
AND
all benchmark-required documents were retrieved/disclosed
```

This is the fairest shared end-to-end metric. RAG also reports a stricter final-answer citation metric, but that is not directly symmetric with progressive disclosure because progressive attribution is derived from its model-authored evidence plan.

| System | Answer accuracy | Complete discovery | Answer + discovery | Single-doc | Multi-doc | Mean docs | Mean input tokens | Corpus body loaded | Generation calls | Current status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **Progressive disclosure V18** | **97.2%** | 95.6% | 95.6% | 96.7% | **93.3%** | **1.68** | 9,773 | **2.9%** | 2.16 | **Finalist** |
| Dense RAG K6 | 86.1% | 91.1% | 86.1% | 94.2% | 70.0% | 4.12 | **3,043** | 5.3% | **1.00** | Baseline only |
| **Hybrid RAG K6** | 96.1% | **98.3%** | **96.1%** | 97.5% | **93.3%** | 4.40 | 3,102 | 5.5% | **1.00** | **Finalist** |
| Hybrid + global reranker | 92.8% | 97.8% | 91.7% | **99.2%** | 76.7% | 4.27 | 3,155 | 5.5% | **1.00** | Do not deepen |
| Qwen hierarchical hybrid K8 | 92.2% | **99.4%** | 92.2% | **99.2%** | 78.3% | 5.27 | 3,720 | 6.5% | **1.00** | Do not deepen as-is |

The result is not that a more sophisticated retriever automatically performs better. The opposite happens on the hard multi-document slice: both reranking experiments improve or nearly perfect **source discovery**, while making the final evidence context less useful for answering.

### Multi-document questions are the discriminator

Single-document retrieval is close to solved by several systems. Multi-document questions expose whether a retriever assembles a **complementary evidence set** rather than merely highly relevant passages.

| System | Northstar multi answer | Tell Aster multi answer | Multi-doc discovery | Multi-doc answer + discovery |
| --- | ---: | ---: | ---: | ---: |
| **Progressive disclosure V18** | **100%** | **95%** | 93.3% | **93.3%** |
| Dense RAG K6 | 95% | 57.5% | 80.0% | 70.0% |
| **Hybrid RAG K6** | **100%** | 90% | 96.7% | **93.3%** |
| Hybrid + global reranker | 90% | 75% | 93.3% | 76.7% |
| Qwen hierarchical hybrid K8 | 90% | 72.5% | **98.3%** | 78.3% |

The Qwen run is particularly instructive: it finds essentially every required source, yet Tell Aster multi-document answer accuracy falls to **72.5%**. Retrieval-only answer-evidence coverage on that slice is **80%**. High document recall therefore does not guarantee an answerable context.

### Efficiency

Progressive disclosure is the most selective system: it reads only 1.68 document bodies and about 2.9% of corpus content on average. Its cost is the planning/recovery loop, which increases cumulative input tokens and model calls.

The original hybrid K6 baseline is currently the strongest production-shaped RAG candidate: retrieval is local, warm retrieval latency is around tens of milliseconds on the measured machine, the answer stage uses one generation call, and it remains tied with progressive disclosure on the aggregate multi-document Answer + discovery metric.

The Qwen hierarchy is much heavier as currently implemented: measured local retrieval was on the order of seconds per query rather than tens of milliseconds, while answer accuracy was lower. It is useful as an ablation source, but not currently a better production pipeline.

## What the experiments taught us

### 1. Dense retrieval alone is not enough

Dense K6 performs well on simple Northstar lookup but degrades strongly on Tell Aster multi-document questions. Exact identifiers and complementary lexical evidence matter.

### 2. BM25 is the largest RAG improvement so far

Adding local BM25 and reciprocal-rank fusion changes the result dramatically:

```text
Dense K6:   91.1% discovery / 86.1% answers
Hybrid K6:  98.3% discovery / 96.1% answers
```

This is the strongest RAG improvement measured in the repository.

### 3. Global relevance reranking can destroy evidence diversity

The cross-encoder reranker improves single-document performance but hurts multi-document composition. Several individually relevant chunks can crowd out a different document needed for another part of the question.

### 4. Stronger retrieval does not automatically improve answering

The Qwen hierarchical pipeline reaches **99.4% complete document discovery** and 100% discovery across both single-document slices. Nevertheless, its multi-document answer accuracy falls below the simpler hybrid K6 baseline.

The core remaining problem is therefore not just:

> Which documents are relevant?

It is:

> Which small set of passages collectively establishes every independent fact needed by the question?

### 5. Progressive disclosure and hybrid RAG fail differently

A paired comparison of the 180 cases is especially promising:

```text
solved by both:                 165
solved only by Hybrid RAG K6:     8
solved only by Progressive V18:   7
solved by neither:                0
```

This is **not** a claim that an implemented ensemble already achieves 100%; both systems have been developed on these corpora. It does show that their failure modes are strongly complementary and motivates a conditional fallback architecture.

## What to deepen next

The project now has enough branches. Further work should concentrate on a small number of candidates.

### 1. Hybrid RAG K6 — primary production candidate

Keep the simple hybrid architecture as the main RAG line.

The next RAG work should be controlled ablations rather than another wholesale pipeline rewrite:

- test `Qwen3-Embedding-0.6B` as a **drop-in embedding replacement** inside the existing K6 hybrid architecture;
- keep BM25, RRF, the existing chunker, K6 context, and answer stage fixed so the embedding model is the only changed variable;
- run a small retrieval-only grid for K/chunk-size/max-chunks-per-document before paying for full E2E runs;
- optimize for **answer-bearing evidence coverage**, not document recall alone.

Do not carry forward the full Qwen hierarchy or global reranker unless a clean ablation demonstrates a benefit.

### 2. Progressive disclosure V18 — reliability / evidence-planning finalist

Keep V18 frozen as the explicit-planning alternative.

Its strengths remain:

- highest overall answer accuracy;
- strongest Tell Aster multi-document result;
- very selective context loading;
- explicit evidence obligations and bounded recovery.

Future work should focus more on production hardening, abstention/fallback behavior, latency/cost reduction, and evaluation on an untouched corpus than on continued prompt tuning against known cases.

### 3. Adaptive Hybrid -> Progressive fallback — most promising combined follow-up

The paired-case result suggests a practical production architecture:

```text
question
   |
   v
local Hybrid RAG K6
   |
   +--> evidence looks sufficient --> answer
   |
   +--> incomplete / ambiguous / compound evidence
             |
             v
      progressive evidence planning
             |
             v
           answer
```

The goal would be to preserve the cheap one-call hybrid path for ordinary questions while using explicit evidence planning only on the difficult cases where RAG evidence is incomplete or internally conflicting.

This should be treated as a **new experiment**, not inferred to achieve the union score automatically. The important research question is whether a runtime signal can identify the fallback cases without evaluator gold.

### Stop optimizing these branches

- **Dense-only RAG:** useful baseline, but clearly dominated by hybrid retrieval.
- **Global cross-encoder reranking:** improves single lookup but damages multi-document evidence coverage.
- **Full Qwen hierarchical K8 pipeline:** excellent source recall, but slower and substantially worse on multi-document answering.

The Qwen models remain useful components for controlled ablations; the measured full architecture does not justify further tuning as a primary pipeline.

See [`docs/approach-selection.md`](docs/approach-selection.md) for the detailed decision record.

## Evaluation caveat

Northstar and Tell Aster have both participated in development. They are now best treated as development/validation corpora, not untouched evidence of universal production reliability.

After the two finalists and any adaptive fallback are frozen, the next decisive benchmark should use a **third untouched corpus** with the same evaluation methodology. That experiment will be more informative than pushing these familiar 180 cases toward 100% through further case-specific tuning.

## Why progressive disclosure?

LLM context is finite. More context is not automatically better context.

The progressive-disclosure architecture separates the knowledge base into two layers:

1. **Always-visible metadata** — document identity, description, activation hints, and compact routing information.
2. **On-demand bodies** — detailed content disclosed only after the model identifies an evidence need.

If disclosed evidence reveals a useful cross-reference but a fact is still missing, the runtime can use that discovery as a compact hint for bounded recovery.

The normal path remains intentionally small:

```text
metadata
-> complete evidence plan
-> selected bodies
-> answer
```

## Grounded in current agent and retrieval guidance

The progressive-disclosure design follows the context-engineering direction described by Anthropic and OpenAI, while the RAG experiments test the complementary retrieval path.

**Anthropic — Agent Skills**

Anthropic describes metadata such as a skill name and description as the first level of progressive disclosure, followed by the selected body and deeper linked resources.

https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

**Anthropic — Effective context engineering**

Anthropic argues for keeping context focused on high-signal information and retrieving additional context just in time.

https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**Anthropic — Contextual Retrieval**

Anthropic's retrieval work motivates combining semantic retrieval with lexical BM25 and evaluates reranking as a further retrieval stage. This repository reproduces the large dense -> hybrid gain, but also demonstrates that pointwise reranking can reduce evidence-set quality on multi-document questions.

https://www.anthropic.com/engineering/contextual-retrieval

**OpenAI — Harness engineering**

OpenAI recommends giving agents a **map rather than a giant instruction manual**, keeping the entry point small, and organizing deeper knowledge for discovery.

https://openai.com/index/harness-engineering/

## Corpora

### Northstar

A compact synthetic enterprise and policy knowledge base with topics such as products, billing, governance, regional rules, infrastructure, incidents, approvals, overrides, and exceptions.

### Tell Aster

A larger synthetic archaeological archive covering excavation, stratigraphy, ceramics, artifacts, burials, environmental evidence, laboratory dating, inscriptions, conservation, museum provenance, remote sensing, and archaeological synthesis.

Tell Aster contains **80 knowledge documents**. Its datasets and evaluator gold live separately under `datasets/`, not inside `corpus/tell-aster/`.

## Repository layout

```text
corpus/        knowledge documents only
datasets/      evaluation questions and evaluator-only gold
prompts/       runtime prompts
src/           progressive-disclosure and local-RAG runtimes
experiments/   benchmark configurations
scripts/       validation, indexing, retrieval, and evaluation entry points
docs/          methodology and engineering guidance
models/        ignored local model snapshots for reproducible Qwen experiments
```

Evaluator ground truth—including required document IDs and expected answers—is never supplied to a runtime retriever or answer agent.

## Run it

Run deterministic repository checks:

```bash
python -m pytest
python scripts/check_all.py
```

### Progressive disclosure V18

```bash
python scripts/run_eval_suite.py \
  --suite experiments/suites/eval-all-v18.yaml \
  --runs 1
```

### Frozen local hybrid RAG K6

```bash
pip install -r requirements-rag.txt

python scripts/build_rag_index.py \
  --all \
  --device mps

python scripts/run_rag_suite.py \
  --suite experiments/suites/rag-hybrid-all.yaml \
  --device mps
```

### Global-reranker experiment

```bash
python scripts/run_rag_v2_pipeline.py \
  --device mps \
  --with-paid-evals
```

This experiment is retained for reproducibility, not recommended as the current production candidate.

### Qwen hierarchical-hybrid experiment

Install and explicitly download the pinned local models:

```bash
pip install -r requirements-qwen-rag.txt
python scripts/download_qwen_rag_models.py
```

Then run the complete pipeline:

```bash
python scripts/run_qwen_rag_pipeline.py \
  --device mps \
  --with-paid-evals
```

The Qwen run is also retained as a measured architecture experiment rather than the recommended production path.

## Evaluation philosophy

The benchmark separates questions that are easy to conflate:

- Did retrieval find every required source?
- Did it retrieve the actual answer-bearing evidence, not merely the right document?
- Did it load unnecessary material?
- Could the answer model use the supplied evidence correctly?
- Was attribution complete?
- How many model calls and how much model input were required?

A correct-looking answer is not enough for evidence-grounded retrieval, while a retrieval miss should not automatically be diagnosed as an answering failure.

## More detail

- [`docs/approach-selection.md`](docs/approach-selection.md) — measured architecture comparison and follow-up recommendation
- [`docs/methodology.md`](docs/methodology.md) — evaluation design and metric semantics
- [`docs/how-to-corpus-metadata.md`](docs/how-to-corpus-metadata.md) — discoverable corpus metadata
- [`docs/how-to-progressive-disclosure-runtime.md`](docs/how-to-progressive-disclosure-runtime.md) — progressive-disclosure runtime design
- [`docs/rag-baselines.md`](docs/rag-baselines.md) — local dense/hybrid RAG architecture and commands
- [`docs/rag-comparison.md`](docs/rag-comparison.md) — dense/hybrid/progressive-disclosure comparison
- [`docs/rag-reranking.md`](docs/rag-reranking.md) — global cross-encoder reranking experiment
- [`docs/qwen-rag-pipeline.md`](docs/qwen-rag-pipeline.md) — Qwen hierarchical-hybrid architecture and measured result
