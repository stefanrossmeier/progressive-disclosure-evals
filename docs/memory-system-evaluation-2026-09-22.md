# Memory-system retrieval evaluation — 2026-09-22

## Executive summary

This experiment compares **Basic Memory 0.23.2**, **OpenViking 0.4.21**, and **Hindsight 0.10.1** against the same 180 Northstar + Tell Aster questions already used by this repository.

The result is clear at the retrieval layer:

- **Hindsight is the strongest of the three memory systems.** It reaches **95.0% answer accuracy**, **96.7% complete source discovery**, and **93.9% Answer + discovery**.
- Hindsight is competitive with the repository's stronger retrieval experiments, but it does **not** beat the two existing finalists. Progressive Disclosure V18 remains at **95.6% Answer + discovery** and Hybrid RAG K6 at **96.1%**.
- Hindsight's strength is **single-document recall**: **99.2% Answer + discovery**, higher than Progressive V18's 96.7% and Hybrid K6's 97.5%.
- Its weakness is the same difficult dimension that has separated the earlier retrieval approaches: **multi-document composition**. Hindsight falls to **83.3% Answer + discovery** on multi-document cases versus **93.3%** for both Progressive V18 and Hybrid K6.
- **Basic Memory** reaches **87.8% Answer + discovery** and **OpenViking** **86.7%**. In this configuration they are not competitive with V18, Hybrid K6, or Hindsight as the sole retrieval mechanism.
- Hindsight's write path is expensive. Ingesting the 120 Markdown documents took about **25 minutes** on the measured machine, versus about **34 seconds** for Basic Memory and **104 seconds** for OpenViking.
- The most interesting paired result is that **Hindsight passes all eight cases that Progressive Disclosure V18 misses, while V18 passes all eleven cases Hindsight misses**. Their diagnostic union is 180/180 on these development corpora. This is evidence of complementary failure modes, not an implemented 100% system or a generalization claim.

For the intended agent-memory architecture, the result argues against replacing the repository's retrieval mechanisms with a memory product wholesale. A stronger direction is to separate the concerns:

```text
agent experience
      |
      v
memory extraction / consolidation
      |        candidate: Hindsight-like machinery
      v
Git + Markdown canonical memory
      |
      +---- human browse/edit/review
      |
      v
derived retrieval/indexes
      |        V18 / Hybrid / other rebuildable readers
      v
agent recall
```

The current benchmark measures the **read/retrieval side** of memory. It does not yet answer the more important long-term question: which system learns, updates, consolidates, corrects, and forgets memory best over repeated agent work.

## Artifacts and reproducibility

The commit-safe result snapshot for this run is stored at:

```text
experiments/memory-systems/results/published/2026-09-22/
```

It contains the generated comparison, backend manifests, backend aggregate reports, and normalized per-case `cases.jsonl` files. The much larger provider-level raw `trials.jsonl` files are omitted from Git; their byte sizes and SHA-256 hashes are retained in `raw-artifacts.json` so an archived raw run can be verified.

The exact setup and reproduction procedure is documented in:

```text
experiments/memory-systems/SETUP.md
```

The existing V18/Hybrid comparison used below is documented in `README.md` and `docs/approach-selection.md`.

## Benchmark contract

The experiment deliberately holds the final answer stage constant. Each backend receives the same Markdown corpus and the exact same benchmark question. Provider retrieval hits are mapped back to source document IDs. The full Markdown bodies of the top six mapped documents are then passed to the repository's existing `RagAnswerer` using `prompts/rag/system-v1.md` and `gpt-5-nano`.

The main metric is the same cross-architecture metric already used by this repository:

```text
Answer + discovery =
    deterministic answer matcher passes
    AND
    every evaluator-required source document was retrieved
```

This matters because it prevents vendor-specific answer generation from becoming an uncontrolled variable. The memory system is primarily being tested as an ingest/retrieval layer.

### Reference configuration

| Setting | Value |
| --- | --- |
| Corpora | Northstar (40 docs), Tell Aster (80 docs) |
| Questions | 180 total: 120 single-doc, 60 multi-doc |
| Final answer model | `gpt-5-nano` |
| Final answer prompt | `prompts/rag/system-v1.md` |
| Unique source-document budget | 6 |
| Provider raw-hit budget | 24 |
| Basic Memory | 0.23.2 |
| OpenViking | 0.4.21, SDK 0.1.12 |
| Hindsight | 0.10.1 |
| Hindsight recall budget | `mid` |
| OpenViking ingest mode | `semantic_and_vectors`, `no_split` |

## Primary comparison with existing repository results

The following table puts the new memory-system results into the repository's existing architecture comparison. Existing V18/RAG values come from the frozen results documented in `README.md` and `docs/approach-selection.md`.

| System | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Mean docs | Mean answer input tokens | Body loaded | Answer calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hybrid RAG K6** | 96.1% | **98.3%** | **96.1%** | 97.5% | **93.3%** | 4.40 | **3,102** | 5.5% | 1.00 |
| **Progressive Disclosure V18** | **97.2%** | 95.6% | 95.6% | 96.7% | **93.3%** | **1.68** | 9,773 | **2.9%** | 2.16 |
| **Hindsight** | 95.0% | 96.7% | **93.9%** | **99.2%** | 83.3% | 5.93 | 6,853 | 10.0% | 1.00 |
| Qwen hierarchical hybrid K8 | 92.2% | **99.4%** | 92.2% | **99.2%** | 78.3% | 5.27 | 3,720 | 6.5% | 1.00 |
| Hybrid + global reranker | 92.8% | 97.8% | 91.7% | **99.2%** | 76.7% | 4.27 | 3,155 | 5.5% | 1.00 |
| **Basic Memory** | 88.9% | 88.9% | 87.8% | 95.0% | 73.3% | 5.98 | 6,885 | 10.2% | 1.00 |
| **OpenViking** | 88.3% | 87.8% | 86.7% | 94.2% | 71.7% | 6.00 | 6,796 | 10.0% | 1.00 |
| Dense RAG K6 | 86.1% | 91.1% | 86.1% | 94.2% | 70.0% | 4.12 | 3,043 | 5.3% | 1.00 |

Two conclusions matter more than the ordering itself.

First, **Hindsight is a credible retrieval system on this benchmark**. Its 93.9% Answer + discovery is materially better than the dense baseline, global-reranker experiment, Qwen full hierarchy, Basic Memory, and OpenViking. It is only 1.7 percentage points behind V18 and 2.2 points behind Hybrid K6 on the shared end-to-end metric.

Second, the aggregate number hides a sharp single-versus-multi-document split. Hindsight is almost perfect when one document is sufficient and loses most of its ground when the answer requires complementary evidence from several documents.

## Memory systems only

| Backend | Answer | Discovery | Answer + discovery | Attribution | Single-doc A+D | Multi-doc A+D | Mean docs | Mean retrieval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hindsight** | **95.0%** | **96.7%** | **93.9%** | **93.3%** | **99.2%** | **83.3%** | 5.93 | 974 ms |
| Basic Memory | 88.9% | 88.9% | 87.8% | 85.0% | 95.0% | 73.3% | 5.98 | 2,047 ms |
| OpenViking | 88.3% | 87.8% | 86.7% | 82.2% | 94.2% | 71.7% | 6.00 | **207 ms** |

All 540 backend/case trials completed without runtime errors in the final run.

### By corpus and question type

| Backend | Northstar A+D | Northstar single | Northstar multi | Tell Aster A+D | Tell Aster single | Tell Aster multi |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hindsight** | **90.0%** | **97.5%** | **75.0%** | **95.8%** | **100.0%** | **87.5%** |
| Basic Memory | 86.7% | 92.5% | 75.0% | 88.3% | 96.3% | 72.5% |
| OpenViking | 86.7% | 92.5% | 75.0% | 86.7% | 95.0% | 70.0% |

Hindsight's Tell Aster single-document slice is perfect: 80/80 Answer + discovery. The difficult part is not ordinary fact lookup. It is evidence composition.

## Hindsight versus Progressive Disclosure V18

This is the most useful comparison for the intended memory architecture.

### Aggregate differences

Relative to V18, Hindsight is:

- **2.2 percentage points lower** on answer accuracy: 95.0% vs 97.2%;
- **1.1 points higher** on complete document discovery: 96.7% vs 95.6%;
- **1.7 points lower** on Answer + discovery: 93.9% vs 95.6%;
- **2.5 points higher** on single-document Answer + discovery: 99.2% vs 96.7%;
- **10.0 points lower** on multi-document Answer + discovery: 83.3% vs 93.3%.

This repeats an important lesson from the earlier Qwen experiment: **finding the required documents more often does not automatically produce better final answers**. Hindsight discovers required sources slightly more often than V18 overall, but the six-full-document context is less reliable on compound cases than V18's explicit evidence planning and selective disclosure.

### V18's eight failed cases

The existing paired V18/Hybrid analysis identifies eight V18 Answer + discovery failures. Hindsight passes all eight:

| Case | Basic Memory | OpenViking | Hindsight |
| --- | ---: | ---: | ---: |
| `EVAL-041` | fail | pass | **pass** |
| `EVAL-045` | fail | pass | **pass** |
| `TA-M-007` | pass | pass | **pass** |
| `TA-M-023` | pass | fail | **pass** |
| `TA-S-024` | pass | pass | **pass** |
| `TA-S-027` | pass | pass | **pass** |
| `TA-S-065` | pass | pass | **pass** |
| `TA-S-080` | pass | fail | **pass** |

Basic Memory and OpenViking each recover six of the eight V18 failures. Hindsight recovers all eight.

### Hindsight's eleven failed cases

V18 passes all eleven cases that Hindsight fails:

| Case | Corpus | Type | Answer correct | Complete discovery | Required documents |
| --- | --- | --- | ---: | ---: | --- |
| `EVAL-021` | Northstar | single | no | no | `operations.incidents.communication.customer-notification` |
| `EVAL-042` | Northstar | multi | yes | no | `nova.limits`, `compute.quotas`, `us.data-handling` |
| `EVAL-043` | Northstar | multi | yes | no | `zephyr.limits`, `compute.quotas`, `eu.data-handling` |
| `EVAL-048` | Northstar | multi | no | yes | `refunds.exceptions`, `us.billing-overrides` |
| `EVAL-057` | Northstar | multi | no | no | `scheduled.windows`, `scheduled.approvals` |
| `EVAL-058` | Northstar | multi | no | yes | `exports.approval`, `zephyr.limits`, `us.data-handling` |
| `TA-M-002` | Tell Aster | multi | no | no | `TA-EXC-03`, `TA-CER-02`, `TA-DAT-03` |
| `TA-M-003` | Tell Aster | multi | no | yes | `TA-BUR-01`, `TA-ART-02` |
| `TA-M-015` | Tell Aster | multi | no | yes | `TA-ENV-06`, `TA-ARC-07` |
| `TA-M-019` | Tell Aster | multi | no | no | `TA-SUR-02`, `TA-DAT-02` |
| `TA-M-025` | Tell Aster | multi | no | yes | `TA-ART-01`, `TA-ENV-07` |

Only one of those eleven is a single-document question. Ten are multi-document questions.

Five of the failures have **complete required-document discovery but an incorrect answer** (`EVAL-048`, `EVAL-058`, `TA-M-003`, `TA-M-015`, `TA-M-025`). Two have a correct answer despite incomplete benchmark discovery (`EVAL-042`, `EVAL-043`). Four miss both retrieval and answer (`EVAL-021`, `EVAL-057`, `TA-M-002`, `TA-M-019`).

That pattern strongly suggests that Hindsight's remaining gap is not just source recall. Evidence-set composition and final answerability remain important.

### Diagnostic union

Because Hindsight passes all eight V18 failures and V18 passes all eleven Hindsight failures:

```text
Progressive Disclosure V18 OR Hindsight
= 180 / 180 Answer + discovery cases on the current corpora
```

This is a diagnostic overlap result only. It must **not** be described as an implemented 100% architecture. The current corpora have participated in development, and a real fallback/router would have to decide at runtime when to invoke the second mechanism without evaluator gold.

Still, the complementarity is notable. Hindsight is not simply failing on a superset of V18's difficult cases.

## Common memory-system failures

Across all three memory systems:

```text
all three pass: 135 / 180
at least one passes: 177 / 180
all three fail: 3 / 180
```

The three common failures are all Tell Aster multi-document questions:

1. `TA-M-002` — combine trench context, ceramic horizon, and absolute dating across three documents;
2. `TA-M-015` — combine environmental and architectural evidence to distinguish animal penning from storage;
3. `TA-M-025` — combine artifact material and environmental taxonomy to identify shell species.

Progressive Disclosure V18 passes all three. These are precisely the kind of relational, cross-document evidence-composition questions for which explicit evidence obligations appear to help.

## Required-document ranking quality

Looking at each individual required-document occurrence, not just complete-case discovery:

| Backend | Required doc at rank 1 | Required doc within top 3 | Missing required-document occurrences |
| --- | ---: | ---: | ---: |
| **Hindsight** | **72.1%** | **96.7%** | **6** |
| OpenViking | 70.6% | 93.9% | 22 |
| Basic Memory | 61.9% | 91.0% | 27 |

Hindsight's advantage is therefore visible before the answer stage: its required documents are both more complete and more highly ranked.

## Ingestion cost

The memory systems differ dramatically in write-path cost.

| Backend | Northstar ingest | Tell Aster ingest | Total | Relative to Basic |
| --- | ---: | ---: | ---: | ---: |
| **Basic Memory** | 15.6 s | 17.9 s | **33.5 s** | 1.0x |
| **OpenViking** | 48.0 s | 55.9 s | **103.9 s** | 3.1x |
| **Hindsight** | 264.4 s | 1,246.0 s | **1,510.4 s (25m 10s)** | **45.1x** |

Hindsight is about **14.5x slower to ingest than OpenViking** in this run.

This is not an apples-to-apples implementation detail: the products perform different work. Basic Memory's reference ingest built full-text search and local `bge-small-en-v1.5` FastEmbed vectors. OpenViking ran semantic summarization plus embeddings. Hindsight retained the Markdown through its normal fact-extraction/consolidation path rather than being reduced to a vector store.

OpenViking exposed ingest token telemetry:

| Corpus | LLM tokens | Embedding tokens | Total provider tokens |
| --- | ---: | ---: | ---: |
| Northstar | 124,851 | 44,455 | 169,306 |
| Tell Aster | 234,216 | 121,541 | 355,757 |
| **Total** | **359,067** | **165,996** | **525,063** |

The Hindsight manifest does not expose comparable ingest-token telemetry, so no normalized provider-cost comparison should be claimed from this run.

For an actual long-running agent, this write cost may be acceptable if memory is consolidated asynchronously and read many times. It is nevertheless a material architectural characteristic and should remain part of future memory benchmarks.

## Retrieval latency

Measured provider retrieval latency in the experiment:

| Backend | Mean | Median | p95 | Notes |
| --- | ---: | ---: | ---: | --- |
| **OpenViking** | **207 ms** | **172 ms** | **400 ms** | fastest memory backend in this harness |
| Hindsight | 974 ms | 916 ms | 1,080 ms | one ~11 s outlier; otherwise near 1 s |
| Basic Memory | 2,047 ms | 2,046 ms | 2,078 ms | worker invokes the Basic Memory CLI, so process/CLI overhead is included |

These are harness-level retrieval measurements, not pure engine microbenchmarks. Basic Memory in particular should not be described as intrinsically a two-second search engine from this run alone.

For context, the repository's existing Hybrid K6 implementation has measured warm local retrieval around tens of milliseconds (roughly 52 ms in the documented run). Progressive V18 uses model-based evidence planning, so a local-search latency comparison is not symmetric.

## Context efficiency

All three memory backends were evaluated with the same maximum of six **full source documents** passed to the common answerer. They consequently read almost six documents per question and load about 10% of the corpus body on average.

| System | Mean docs | Mean body loaded | Mean answer input tokens |
| --- | ---: | ---: | ---: |
| Progressive Disclosure V18 | **1.68** | **2.9%** | 9,773 |
| Hybrid RAG K6 | 4.40 | 5.5% | **3,102** |
| Hindsight | 5.93 | 10.0% | 6,853 |
| Basic Memory | 5.98 | 10.2% | 6,885 |
| OpenViking | 6.00 | 10.0% | 6,796 |

This result should be interpreted carefully. The six-document budget is a benchmark control, not necessarily the ideal production configuration of each memory product. Nevertheless, it shows why Hindsight can have better document discovery than V18 while still producing worse answers on some compound cases: the answer model receives a larger, less explicitly structured evidence set.

A future retrieval ablation could test smaller and larger document budgets, but it should be kept separate from this reference run.

## What this says about the Git/Markdown memory goal

The original architectural requirement is stronger than generic "agent memory":

> The ground truth must live in a private Git repository, be easy for a human to browse as rendered Markdown, and be directly editable when the agent learned something incorrectly.

The current result suggests that **storage/learning and retrieval should not be forced into one product**.

### Basic Memory

Basic Memory is still the closest architectural fit to the Git/Markdown source-of-truth requirement. Its own derived index can be rebuilt from Markdown, and the reference run ingested the corpus very cheaply.

However, **87.8% Answer + discovery is not strong enough to justify using Basic Memory's retrieval as the only read path** when the repository already contains much stronger retrieval mechanisms.

A reasonable interpretation is:

> Basic Memory remains interesting as a model for Markdown-native state and synchronization, but this run does not validate its retrieval layer as a replacement for V18/Hybrid.

### OpenViking

OpenViking provides the fastest memory-backend retrieval in this experiment and an attractive hierarchical/context-oriented model. Its semantic ingest finished in under two minutes for the full corpus.

But **86.7% Answer + discovery** and **71.7% multi-document A+D** put the measured configuration near the dense baseline rather than the repository's finalists. On this benchmark there is no evidence to replace existing retrieval with OpenViking recall.

### Hindsight

Hindsight is the only one of the three whose retrieval quality justifies deeper investigation. Its advantages are:

- 99.2% single-document Answer + discovery;
- 96.7% complete required-document discovery;
- 93.9% overall Answer + discovery;
- recovery of every current V18 failure;
- strong provenance metadata on retained facts/chunks.

Its costs are equally clear:

- approximately 25 minutes to ingest 120 documents in the reference run;
- roughly one-second retrieval rather than local-millisecond retrieval;
- a 10-point multi-document A+D gap versus V18/Hybrid;
- Hindsight's database/memory bank, not Git Markdown, is its native internal memory representation.

For the intended architecture, Hindsight therefore looks more promising as a **learning/consolidation engine around a Markdown ground truth** than as the sole canonical store and sole retrieval mechanism.

## Recommended architecture after this experiment

The benchmark supports decoupling the write path from the read path.

```text
                       private Git repository
                      CANONICAL MARKDOWN MEMORY
                               /       \
                              /         \
                    human review        derived indexes
                    edit / revert        / graph / vectors
                         ^                    |
                         |                    v
                memory reconciler        retrieval layer
                         ^             V18 / Hybrid / ablation
                         |
              learned memory proposals
                         ^
                         |
                  agent trajectories
                         |
            Hindsight-like extraction /
                 consolidation engine
```

The important invariant would be:

> Any machine-only state may be deleted and rebuilt without losing the authoritative memory.

A learning engine may propose or consolidate memories, but durable accepted state is materialized into Markdown and committed to Git. Human edits to those files outrank stale derived state and trigger re-indexing/reconciliation.

This architecture allows using the strongest tool for each job instead of accepting a memory product's complete stack as indivisible.

## What the current experiment does **not** establish

The results should not be presented as "Hindsight is the best agent memory" or "Basic Memory failed as a memory system." The benchmark is intentionally narrower.

It does not evaluate:

- deciding which events deserve memory;
- learning from conversations or tool trajectories;
- extracting durable lessons from repeated tasks;
- merging duplicate memories;
- updating a fact when reality changes;
- retaining historical truth while changing current truth;
- contradiction detection;
- human corrections and authority;
- deletion/forgetting;
- Git round-trip/rebuild behavior;
- whether learned memory improves subsequent agent task performance;
- memory growth over weeks/months;
- cost per useful learned memory.

Those capabilities are central to the actual product decision.

## Next experiment: memory lifecycle and human oversight

The next benchmark should stop asking only "can this system retrieve an already-written document?" and instead simulate an agent working over time.

A useful lifecycle corpus would contain a sequence of 100–300 events across a fictional software project. Events should deliberately include:

1. facts worth remembering and irrelevant noise;
2. repeated facts that should consolidate rather than duplicate;
3. decisions and the reasons behind them;
4. facts that later become obsolete;
5. explicit corrections;
6. contradictory evidence;
7. procedures learned through successful/failed tasks;
8. user preferences and project conventions;
9. historical facts that must remain queryable after being superseded;
10. human edits made directly in the Markdown repository.

The benchmark should then measure at least:

- **write precision** — did the system remember useful things rather than everything?
- **write recall** — did it retain important lessons?
- **consolidation quality** — did repeated evidence become one coherent memory?
- **update correctness** — is the current fact correct after changes?
- **temporal recall** — can it distinguish "current" from "previously true"?
- **contradiction handling** — does conflicting evidence trigger reconciliation instead of silent overwrite?
- **human-override compliance** — does an explicit Markdown correction become authoritative?
- **rebuild fidelity** — after deleting all indexes/databases, can useful memory be reconstructed from the Git repository?
- **task improvement** — does memory actually improve later agent behavior?
- **cost/latency** — how expensive is one useful durable memory over its lifecycle?

That second experiment is the one that should determine the eventual memory engine.

## Decision from this phase

The static retrieval experiment is sufficient to narrow the next work:

1. **Keep Progressive Disclosure V18 and Hybrid K6 as the retrieval reference points.** Neither should be replaced by a memory product based on this result.
2. **Deepen Hindsight as the learning/consolidation candidate.** It is the only tested memory backend close enough in retrieval quality to justify the added complexity, and its failures complement V18.
3. **Keep Basic Memory in scope for Markdown-native ground-truth mechanics**, not because its current retrieval result wins.
4. **Do not prioritize OpenViking as the primary memory path from this result alone.** Its measured retrieval quality does not justify another large integration effort before the lifecycle benchmark.
5. **Build the lifecycle/human-correction benchmark before selecting the final memory architecture.** Static recall is only one part of the actual requirement.

## Evaluation caveats

Northstar and Tell Aster have both been used during development of this repository. The numbers are appropriate for comparative development decisions but are not untouched estimates of production generalization.

The memory systems also receive different internal ingest treatment because they are different products. The experiment intentionally permits their normal memory behavior rather than reducing all three to the same vector database. Consequently, ingest wall time and provider-internal cost reflect real product differences but are not controlled algorithmic microbenchmarks.

Finally, this is a single full run. The deterministic evaluator makes the headline scoring stable given an answer, but the LLM-based final answer stage and provider semantic ingest can still vary. A final architecture claim should be confirmed with repeated runs and an untouched third corpus.
