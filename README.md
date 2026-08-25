# Progressive Disclosure Evals

An eval-first implementation of **progressive disclosure for LLM knowledge retrieval**.

Instead of placing an entire knowledge base into the model context—or retrieving chunks with embeddings—the runtime first exposes a compact metadata map of the available documents. The model plans the evidence it needs, only those document bodies are disclosed, and the answer is grounded in the disclosed evidence.

```text
question + compact document metadata
                ↓
      atomic evidence plan
                ↓
   selected document bodies
                ↓
            answer
                ↓
 bounded recovery when evidence is still missing
```

The project asks a deliberately simple question:

> **How far can a small, well-engineered progressive-disclosure system go without embeddings, a vector database, rerankers, or graph retrieval?**

## Current result

The latest complete benchmark is **V18 on `gpt-5-nano`**, with **180 single- and multi-document trials across two unrelated synthetic knowledge bases**.

| Benchmark | Trials | Strict E2E | Answer accuracy | Complete discovery | Mean bodies read |
| --- | ---: | ---: | ---: | ---: | ---: |
| Northstar — single document | 40 | **100%** | 100% | 100% | 1.40 |
| Northstar — multi document | 20 | **90%** | 100% | 90% | 2.60 |
| Tell Aster — single document | 80 | **95%** | 96.3% | 95% | 1.28 |
| Tell Aster — multi document | 40 | **95%** | 95% | 95% | 2.30 |
| **Overall** | **180** | **95.6%** | **97.2%** | **95.6%** | **1.68** |

Across the complete run:

- **100% completion** — 180/180 trials completed without runtime errors.
- **95.6% strict end-to-end success**.
- **97.2% answer accuracy**.
- **95.6% complete evidence discovery and attribution**.
- **92.2% first-read hit rate**.
- **86.9% mean document precision**.
- **1.68 document bodies read on average**, with **p95 = 3**.
- **2.16 model calls per trial on average**.
- Only **2.9% of corpus body content** was loaded on average.

Strict E2E is intentionally stronger than answer accuracy: a trial passes only when the answer is correct **and** every benchmark-required evidence document is discovered and attributed.

The result is especially useful because the two corpora have very different information structures. Northstar is an enterprise/policy knowledge base; Tell Aster is an archaeological research archive. Tell Aster's evaluation data is kept outside the corpus so evaluator gold is never part of the runtime knowledge base.

## Why progressive disclosure?

LLM context is finite. More context is not automatically better context.

The architecture therefore separates the knowledge base into two layers:

1. **Always-visible metadata** — document identity, description, activation hints, and other compact routing information.
2. **On-demand bodies** — detailed content disclosed only after the model identifies an evidence need.

If disclosed evidence reveals a useful cross-reference but a fact is still missing, the runtime can use that discovery as a compact hint for bounded recovery. It does not automatically traverse every link or load the surrounding corpus.

The successful path remains intentionally small:

```text
metadata
→ complete evidence plan
→ selected bodies
→ answer
```

## Grounded in current agent guidance

This design follows the same context-engineering direction described by Anthropic and OpenAI.

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
src/           progressive-disclosure runtime and evaluator
experiments/   benchmark configurations
scripts/       validation and evaluation entry points
docs/          methodology and engineering guidance
```

Evaluator ground truth—including required document IDs and expected answers—is never supplied to the runtime agent.

## Run it

Install the project dependencies, configure the model credentials expected by the repository, then run the deterministic checks:

```bash
python -m pytest
python scripts/check_all.py
```

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

## Evaluation philosophy

The benchmark separates several questions that are easy to conflate:

- Did the model find the right evidence?
- Did it find the evidence early?
- Did it load unnecessary documents?
- Could it answer correctly from the evidence it had?
- Did it attribute every required source?
- Did it stop once the evidence was sufficient?

This matters because a correct-looking answer is not enough for evidence-grounded retrieval, while a retrieval miss should not automatically be misdiagnosed as an answering failure.

The repository therefore reports both **strict end-to-end success** and **answer accuracy**, together with discovery, attribution, first-read hit rate, document precision, model calls, and knowledge fraction loaded.

## More detail

- [`docs/methodology.md`](docs/methodology.md) — evaluation design and metrics
- [`docs/how-to-corpus-metadata.md`](docs/how-to-corpus-metadata.md) — how to design discoverable corpus metadata
- [`docs/how-to-progressive-disclosure-runtime.md`](docs/how-to-progressive-disclosure-runtime.md) — runtime design and evidence-planning rules
- [`docs/rag-baselines.md`](docs/rag-baselines.md) — local dense/hybrid RAG architecture, indexing, evaluation, and comparison workflow
