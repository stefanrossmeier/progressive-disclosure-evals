# Progressive Disclosure Evals

An eval-first comparison of **progressive disclosure** and conventional **local RAG** for LLM knowledge retrieval.

The primary runtime uses a compact metadata map instead of embedding search: the model plans the evidence it needs, only the selected document bodies are disclosed, and the answer is grounded in that evidence. The repository also includes dense and hybrid RAG baselines over the exact same corpora and eval datasets.

```text
Progressive disclosure
question + document metadata
        -> atomic evidence plan
        -> selected document bodies
        -> answer

Local RAG
question
        -> dense or hybrid retrieval
        -> top-K document chunks
        -> answer
```

The project asks two practical questions:

> **How far can a small progressive-disclosure system go without a vector database or retrieval framework?**

> **When does conventional RAG provide a better production trade-off?**

## Current results

All results below use `gpt-5-nano` for answer generation and the same Northstar + Tell Aster evaluation sets.

### Progressive disclosure V18

The latest full progressive-disclosure benchmark contains **180 single- and multi-document trials across two unrelated synthetic knowledge bases**.

| Benchmark | Trials | Strict E2E | Answer accuracy | Complete discovery | Mean bodies read |
| --- | ---: | ---: | ---: | ---: | ---: |
| Northstar — single document | 40 | **100%** | 100% | 100% | 1.40 |
| Northstar — multi document | 20 | **90%** | 100% | 90% | 2.60 |
| Tell Aster — single document | 80 | **95%** | 96.3% | 95% | 1.28 |
| Tell Aster — multi document | 40 | **95%** | 95% | 95% | 2.30 |
| **Overall** | **180** | **95.6%** | **97.2%** | **95.6%** | **1.68** |

Across the full run, progressive disclosure loaded only **2.9% of corpus body content on average** and used **2.16 model calls per trial**.

### Local RAG comparison

The repository contains two deliberately small local retrieval baselines using `BAAI/bge-small-en-v1.5`, top-6 retrieval, and the same answer model:

- **Dense RAG** — local embeddings + cosine similarity.
- **Hybrid RAG** — dense retrieval + local BM25 + reciprocal-rank fusion.

| System | Answer accuracy | Complete discovery | Answer + discovery | Mean docs represented | Corpus body loaded | Generation calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Progressive disclosure V18** | **97.2%** | 95.6% | 95.6% | **1.68** | **2.9%** | 2.16 |
| Dense RAG K6 | 86.1% | 91.1% | 86.1% | 4.12 | 5.3% | **1.00** |
| Hybrid RAG K6 | 96.1% | **98.3%** | **96.1%** | 4.40 | 5.5% | **1.00** |

The result is not a simple winner/loser story:

- Dense-only RAG is clearly weaker on these corpora, especially for genuine multi-document questions.
- Adding BM25 changes the picture substantially: hybrid RAG reaches **98.3% complete document discovery** and **96.1% answer accuracy**.
- Progressive disclosure remains much more selective, reading about **2.6× fewer documents** and roughly **half as much corpus body content**.
- Hybrid RAG needs only **one generation call** per normal query because retrieval is local and deterministic.
- On Tell Aster multi-document questions, progressive disclosure still has an answer-accuracy advantage: **95% vs 90%** for hybrid K6. This is where explicit evidence planning appears most useful.

### A note on strict RAG E2E

The current RAG reports also show a citation-strict E2E score of **81.1% for dense K6** and **91.1% for hybrid K6**. Those numbers are useful, but they are not directly symmetric with progressive disclosure.

RAG currently requires the final answer call to explicitly cite every benchmark-required document. Progressive disclosure derives attribution from the model-authored evidence plan and does not ask the final answer call to reconstruct the source set again. For architecture comparison, this README therefore highlights **answer correctness + complete required-document discovery** alongside the raw citation-strict score.

See [`docs/rag-comparison.md`](docs/rag-comparison.md) for the detailed breakdown and interpretation.

## Why progressive disclosure?

LLM context is finite. More context is not automatically better context.

The progressive-disclosure architecture separates the knowledge base into two layers:

1. **Always-visible metadata** — document identity, description, activation hints, and compact routing information.
2. **On-demand bodies** — detailed content disclosed only after the model identifies an evidence need.

If disclosed evidence reveals a useful cross-reference but a fact is still missing, the runtime can use that discovery as a compact hint for bounded recovery. It does not automatically traverse every link or load the surrounding corpus.

The normal path remains intentionally small:

```text
metadata
-> complete evidence plan
-> selected bodies
-> answer
```

The RAG baselines provide a useful counterpoint: they avoid the planning call, but retrieve a wider top-K chunk set up front.

## Grounded in current agent guidance

The progressive-disclosure design follows the same context-engineering direction described by Anthropic and OpenAI.

**Anthropic — Agent Skills**

Anthropic describes skill metadata such as a name and description as the first level of progressive disclosure, followed by the selected skill body and then deeper linked resources. This project applies the same principle to Markdown knowledge bases.

https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills

**Anthropic — Effective context engineering**

Anthropic argues for keeping context focused on high-signal information and retrieving additional context just in time. It also describes agentic search as a process in which information discovered during navigation can guide the next retrieval decision.

https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**OpenAI — Harness engineering**

OpenAI recommends giving agents a **map rather than a giant instruction manual**, keeping the entry point small, organizing deeper knowledge for discovery, and enforcing repository structure mechanically.

https://openai.com/index/harness-engineering/

**OpenAI — A practical guide to building agents**

OpenAI emphasizes clear, standardized tool definitions and descriptions so agents can reliably discover and invoke the capabilities they need.

https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

The common principle is:

> **Keep always-visible context small, make the map informative, and disclose detailed information only when it becomes relevant.**

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
```

Evaluator ground truth—including required document IDs and expected answers—is never supplied to either runtime.

## Run it

Install the core project and run deterministic checks:

```bash
python -m pytest
python scripts/check_all.py
```

### Progressive disclosure

Run the small verification suite:

```bash
python scripts/run_eval_suite.py \
  --suite experiments/suites/verify-all-v18.yaml
```

Run the full benchmark:

```bash
python scripts/run_eval_suite.py \
  --suite experiments/suites/eval-all-v18.yaml \
  --runs 1
```

### Local RAG

Install the optional local retrieval stack:

```bash
pip install -r requirements-rag.txt
```

Build both indexes:

```bash
python scripts/build_rag_index.py \
  --all \
  --device mps
```

Run the retrieval-only checks before spending generation calls:

```bash
python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-northstar.yaml \
  --device mps

python scripts/run_rag_retrieval_eval.py \
  --config experiments/rag/hybrid-tell-aster.yaml \
  --device mps
```

Run the full hybrid benchmark:

```bash
python scripts/run_rag_suite.py \
  --suite experiments/suites/rag-hybrid-all.yaml \
  --device mps
```

See [`docs/rag-baselines.md`](docs/rag-baselines.md) for dense/hybrid configuration, offline operation, index details, and evaluation commands.

## Evaluation philosophy

The benchmark separates questions that are easy to conflate:

- Did retrieval find every required source?
- Did it retrieve the actual answer-bearing evidence, not merely the right document?
- Did it load unnecessary material?
- Could the answer model use the supplied evidence correctly?
- Was attribution complete?
- How many model calls and how much corpus content were required?

A correct-looking answer is not enough for evidence-grounded retrieval, while a retrieval miss should not automatically be diagnosed as an answering failure.

The repository therefore reports answer accuracy, complete discovery, attribution, document precision, model calls, and knowledge fraction loaded in addition to end-to-end success.

## More detail

- [`docs/methodology.md`](docs/methodology.md) — evaluation design and metric semantics
- [`docs/how-to-corpus-metadata.md`](docs/how-to-corpus-metadata.md) — how to design discoverable corpus metadata
- [`docs/how-to-progressive-disclosure-runtime.md`](docs/how-to-progressive-disclosure-runtime.md) — runtime design and evidence-planning rules
- [`docs/rag-baselines.md`](docs/rag-baselines.md) — local dense/hybrid RAG architecture, indexing, and commands
- [`docs/rag-comparison.md`](docs/rag-comparison.md) — measured dense/hybrid/progressive-disclosure comparison
