# Markdown memory systems — retrieval evaluation and direction — 2026-09-23

## Executive decision

The retrieval phase is now strong enough to narrow the memory work to **two Markdown-native finalists**:

1. **tigerless-labs/agent-memory** — primary architectural candidate;
2. **akitaonrails/ai-memory** — primary alternative / maturity-and-performance comparator.

Both clear the threshold for the next phase. On the same frozen 180-question Northstar + Tell Aster benchmark used elsewhere in this repository:

- **agent-memory** reaches **98.3% answer accuracy**, **97.8% complete discovery**, and **96.7% Answer + discovery**;
- **ai-memory** reaches **98.9% answer accuracy**, **97.2% complete discovery**, and **96.1% Answer + discovery**;
- both are **100% on single-document Answer + discovery**;
- both remain weaker on the difficult multi-document slice: **90.0%** for agent-memory and **88.3%** for ai-memory, versus **93.3%** for Progressive Disclosure V18 and Hybrid RAG K6.

These are strong enough retrieval results that more tuning on the current corpora is no longer the highest-value work. The next decisive experiment should evaluate **memory formation and lifecycle behavior**: what gets remembered, how duplicates and contradictions are handled, how old facts are superseded, whether human Markdown edits remain authoritative, whether provenance survives, and whether all machine state can be rebuilt from the Markdown/Git ground truth.

The current direction is therefore:

```text
agent activity
    |
    v
memory formation / consolidation
    |             compare agent-memory vs ai-memory
    v
private Git repository
CANONICAL MARKDOWN MEMORY
    |
    +--> human browse / edit / diff / revert
    |
    +--> disposable indexes
              |
              v
       cheap native retrieval
              |
              +--> easy lookup: answer
              |
              +--> compound / incomplete evidence
                         |
                         v
                 V18-like evidence planning
                         |
                         v
                       answer
```

Do **not** choose a final production memory engine solely from these retrieval numbers. Do freeze these retrieval adapters and move the comparison to lifecycle behavior.

## Scope and benchmark contract

This document synthesizes both memory-system retrieval experiments performed in this repository:

### Phase 1 — general memory systems

- Basic Memory 0.23.2
- OpenViking 0.4.21
- Hindsight 0.10.1

The detailed original report is `docs/memory-system-evaluation-2026-09-22.md`.

### Phase 2 — Markdown-native memory systems

- ai-memory 2.4.0
- EverOS 1.3.1
- agent-memory commit `70d85e5c22081d9dac88c5e908c88ea0bf13af88`

The final valid Phase-2 aggregate snapshot is:

```text
experiments/markdown-memory-systems/results/published/2026-09-23/
```

Both phases deliberately use the same evaluation boundary:

```text
memory backend
    |
    | retrieves / ranks memory
    v
resolved full Markdown documents
    |
    v
shared RagAnswerer
    |
    v
prompts/rag/system-v1.md
    |
    v
shared deterministic scorer
```

The memory provider does not get evaluator gold and does not supply a proprietary final-answer stack. This makes **Answer + discovery** the primary cross-system metric:

```text
correct deterministic answer
AND
all benchmark-required source documents were retrieved
```

Reference configuration for the Phase-2 final runs:

| Setting | Value |
| --- | --- |
| Corpora | Northstar (40 docs), Tell Aster (80 docs) |
| Questions | 180 total: 120 single-doc, 60 multi-doc |
| Answer model | `gpt-5-nano` |
| Answer prompt | `prompts/rag/system-v1.md` |
| Unique source-document budget | 6 |
| Provider raw-hit budget | 24 |
| ai-memory retrieval | native FTS5, no embedding provider |
| agent-memory retrieval | native local BM25 |
| EverOS intended retrieval | native `method="keyword"` BM25 |

## Phase 1 result: Basic Memory, OpenViking, Hindsight

The first memory-system experiment established three useful facts.

First, Hindsight was the only backend close to the repository's strongest retrieval approaches:

| Backend | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Mean retrieval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Hindsight** | **95.0%** | **96.7%** | **93.9%** | **99.2%** | **83.3%** | 974 ms |
| Basic Memory | 88.9% | 88.9% | 87.8% | 95.0% | 73.3% | 2,047 ms |
| OpenViking | 88.3% | 87.8% | 86.7% | 94.2% | 71.7% | **207 ms** |

Second, Hindsight and Progressive Disclosure V18 had strongly complementary failures: Hindsight passed all eight V18 A+D failures, while V18 passed all eleven Hindsight A+D failures. The diagnostic union was 180/180 on these development corpora. That result was useful evidence for explicit fallback/evidence-planning, but not an implemented 100% system.

Third, product architecture mattered as much as retrieval quality. Basic Memory was Markdown-friendly but its then-current AGPL license made it unattractive as a bundled Safeplane dependency. OpenViking had the same broad licensing concern. Hindsight was permissively licensed and strong at retrieval, but its canonical state is database-first rather than Git/Markdown-first.

That phase therefore produced an interim direction: separate memory formation from retrieval and look for systems where Markdown is the actual durable truth rather than a projection.

## Phase 2 candidate selection

The follow-up research identified three systems that matched the desired source-of-truth model much more closely.

### ai-memory

Target architecture:

```text
Git-backed Markdown wiki = durable truth
SQLite / FTS / optional embeddings = derived state
```

The evaluated release is **2.4.0**. The project is MIT licensed.

The final benchmark uses its local FTS5 path without embeddings. Pages are imported through the public write-page API, the server is explicitly scoped to the benchmark corpus, and ingestion fails closed unless the expected 40/80 pages are visible through the scoped read API.

### agent-memory

Target invariant:

> files are truth; indexes are rebuildable caches.

The evaluated revision is:

```text
70d85e5c22081d9dac88c5e908c88ea0bf13af88
```

The project is MIT licensed. It has no stable PyPI release in the evaluated setup, so the exact Git SHA is part of the benchmark identity.

The benchmark uses its native Markdown record path and local BM25 index. Its architecture is especially close to the desired Safeplane model: plain files, rebuildable SQLite indexes, provenance/history, supersession, and an explicit manage/sleep layer.

### EverOS

EverOS core is Apache-2.0, but its repository NOTICE contains a **CC BY-NC 4.0 LoCoMo-derived test fixture carve-out**, and an optional multimodal dependency can add LGPL-3.0 obligations. This does not make the core itself non-permissive, but it makes "vendor the repository" an unacceptable packaging strategy; only audited permissive core components should ever be considered for distribution.

Operationally, EverOS 1.3.1 also requires an LLM provider configuration to start its server even when retrieval is explicitly `method="keyword"`.

The integration reached:

- successful corpus preparation;
- successful per-file cascade synchronization;
- successful Northstar keyword retrieval in smoke probes;
- **zero native provider hits for Tell Aster smoke queries** despite successful ingestion/cascade completion.

Because the Tell Aster retrieval path was not validated, **no full 180-case EverOS score is claimed**. EverOS is excluded from the finalist comparison rather than assigning an invalid or partial result.

## Important harness/integration findings

Several early smoke results were invalid because the adapters did not yet match the providers' exact contracts. These failures are documented here so they are not mistaken for backend quality results.

### ai-memory adapter corrections

The ai-memory integration needed all of the following before its result became valid:

- start the provider-owned HTTP server automatically;
- enable the read-only web/API surface;
- use explicit workspace/project scope;
- send the required scope fields to `/admin/write-page`;
- parse the **v2.4.0 bare-array response shape** for projects, pages, and search hits rather than assuming older wrapped objects;
- normalize provider hits back to the canonical Markdown frontmatter document IDs;
- fail ingestion if the expected 40/80 scoped pages are not visible.

The earlier zero-hit/zero-page runs are therefore adapter failures, not ai-memory benchmark failures.

### agent-memory adapter corrections

The agent-memory provider returns its recall payload under a `{"hits": [...]}` envelope. The initial adapter did not unwrap that shape correctly, which could retrieve the correct native memory but map it to the wrong benchmark document.

After correcting the envelope and canonical-ID mapping, agent-memory passed all four retrieval smoke cases and proceeded to the final full run.

### EverOS diagnostic status

EverOS initially failed to boot because `[llm]` configuration is mandatory in 1.3.1. Reusing the repository's existing OpenAI-compatible settings allowed the server to start while still forcing `method="keyword"` retrieval.

Bulk indexing was replaced with deterministic per-file `cascade sync`, which completed for both corpora. Northstar retrieval then worked, but Tell Aster still returned no provider hits. That unresolved provider-level behavior is why EverOS is parked rather than scored.

## Final Phase-2 full-run results

The two valid full runs contain 180 completed trials each and zero runtime errors.

| System | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Attribution | Mean docs | Mean retrieval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **agent-memory** | 98.3% | **97.8%** | **96.7%** | **100.0%** | **90.0%** | **95.0%** | 6.00 | 75.0 ms |
| **ai-memory** | **98.9%** | 97.2% | 96.1% | **100.0%** | 88.3% | 93.9% | 6.00 | **16.4 ms** |

### By corpus and question type

| System | Northstar A+D | Northstar single | Northstar multi | Tell Aster A+D | Tell Aster single | Tell Aster multi |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **agent-memory** | **93.3%** | **100.0%** | **80.0%** | 98.3% | **100.0%** | 95.0% |
| **ai-memory** | 91.7% | **100.0%** | 75.0% | 98.3% | **100.0%** | 95.0% |

The main result is not the 0.6-point gap between the two. It is the shape of the result:

- ordinary single-document lookup is perfect in this run for both systems;
- Tell Aster multi-document behavior is strong at 95% A+D for both;
- Northstar multi-document composition remains materially weaker at 75–80%;
- both systems read the fixed maximum of six full documents, so neither is context-selective in the way V18 is.

## Comparison with all measured memory systems and retrieval references

| System | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Mean docs | Mean retrieval | Role after this phase |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **agent-memory** | **98.3%** | 97.8% | **96.7%** | **100.0%** | 90.0% | 6.00 | 75 ms | **Markdown-memory finalist** |
| **Hybrid RAG K6** | 96.1% | **98.3%** | 96.1% | 97.5% | **93.3%** | 4.40 | ~52 ms warm | Retrieval reference |
| **ai-memory** | **98.9%** | 97.2% | 96.1% | **100.0%** | 88.3% | 6.00 | **16 ms** | **Markdown-memory finalist** |
| **Progressive Disclosure V18** | 97.2% | 95.6% | 95.6% | 96.7% | **93.3%** | **1.68** | model-planned | Evidence-planning reference |
| Hindsight | 95.0% | 96.7% | 93.9% | 99.2% | 83.3% | 5.93 | 974 ms | Formation reference, DB-first |
| Basic Memory | 88.9% | 88.9% | 87.8% | 95.0% | 73.3% | 5.98 | 2,047 ms | Retire from retrieval race |
| OpenViking | 88.3% | 87.8% | 86.7% | 94.2% | 71.7% | 6.00 | 207 ms | Retire from retrieval race |

The new systems therefore answer the narrow retrieval question positively:

> A Markdown-canonical memory system can retrieve well enough to be competitive with the repository's strongest purpose-built retrieval architectures on these development corpora.

That was not established by the Phase-1 systems.

## Ingestion cost

Measured provider ingestion time for the final valid Phase-2 runs:

| Backend | Northstar | Tell Aster | Total |
| --- | ---: | ---: | ---: |
| **ai-memory** | 0.70 s | 1.45 s | **2.14 s** |
| **agent-memory** | 2.61 s | 5.21 s | **7.82 s** |
| Basic Memory | — | — | ~33.5 s |
| OpenViking | 48.0 s | 55.9 s | ~103.9 s |
| Hindsight | 264.4 s | 1,246.0 s | ~1,510.4 s |

These numbers are operationally useful but **not algorithmically symmetric**. ai-memory and agent-memory are indexing already-written Markdown. Hindsight's expensive ingest performs much more semantic extraction/linking/consolidation work. The timing table therefore supports deployment planning, not a claim that one write algorithm is intrinsically 700x better than another.

## Context efficiency

The Phase-2 benchmark intentionally keeps the same six-document budget used in the first memory-system bakeoff.

| System | Mean docs | Mean answer input tokens | Mean corpus body loaded |
| --- | ---: | ---: | ---: |
| Progressive Disclosure V18 | **1.68** | 9,773 | **2.9%** |
| Hybrid RAG K6 | 4.40 | **3,102** | 5.5% |
| ai-memory | 6.00 | 6,819 | 10.0% |
| agent-memory | 6.00 | 6,816 | 10.1% |
| Hindsight | 5.93 | 6,853 | 10.0% |

The native memory retrieval results are therefore strong, but they are not evidence that six full documents is the desired production context strategy. The multi-document failures strengthen the opposite interpretation: ranking is now good enough that **evidence assembly and selective reading** are becoming the next read-side bottleneck.

## Failure analysis

### ai-memory failures

ai-memory has seven Answer + discovery failures:

```text
EVAL-041
EVAL-044
EVAL-045
EVAL-052
EVAL-058
TA-M-015
TA-M-025
```

Five are incomplete-document-discovery failures with the answer still correct. Two Tell Aster multi-document cases retrieve all required documents but the final answer is wrong.

### agent-memory failures

agent-memory has six Answer + discovery failures:

```text
EVAL-042
EVAL-043
EVAL-044
EVAL-045
TA-M-015
TA-M-025
```

Four are Northstar multi-document discovery failures. Two Tell Aster multi-document cases retrieve all required documents but the final answer is wrong.

### Overlap

The two systems share four A+D failures:

```text
EVAL-044
EVAL-045
TA-M-015
TA-M-025
```

Their diagnostic union passes **176/180** cases. That is only a diagnostic; no router/ensemble has been implemented.

More importantly, both systems' remaining weaknesses are overwhelmingly **multi-document composition** rather than ordinary fact lookup.

### Relationship to V18 / Hybrid K6

The existing V18 failure set contains eight A+D failures. agent-memory overlaps with only `EVAL-045`, giving a diagnostic V18 + agent-memory union of **179/180**. ai-memory overlaps with `EVAL-041` and `EVAL-045`, giving **178/180**.

The existing Hybrid K6 failure set overlaps with both new systems only on `TA-M-015`, giving a diagnostic Hybrid + ai-memory union and Hybrid + agent-memory union of **179/180**.

Again, these are not production scores. They reinforce the earlier finding that a cheap lexical/hybrid first pass and an explicit evidence-planning fallback fail differently enough to justify a routed architecture experiment.

## Licensing and packaging status

Status checked for this decision record on 2026-09-23:

| System | Core license | Safeplane implication |
| --- | --- | --- |
| ai-memory | MIT | Compatible candidate; audit transitive/runtime packaging before bundling |
| agent-memory | MIT | Compatible candidate; pin exact Git SHA until stable releases exist |
| EverOS | Apache-2.0 core | Core is permissive, but repository NOTICE has a CC BY-NC 4.0 test-fixture carve-out; never vendor repo wholesale |
| Hindsight | MIT | Permissive, but canonical state is not Markdown/Git |
| Basic Memory | AGPL-3.0 in evaluated project state | Not attractive as default bundled dependency |
| OpenViking | AGPL-3.0 in evaluated project state | Not attractive as default bundled dependency |

For EverOS, the license conclusion should be precise: **the core is not non-commercial**. The concern is distribution hygiene around separately licensed repository content and optional dependencies, plus the unresolved Tell Aster retrieval behavior in this harness.

License references checked for this record:

- ai-memory: `https://github.com/akitaonrails/ai-memory/blob/v2.4.0/LICENSE`
- agent-memory: `https://github.com/tigerless-labs/agent-memory/blob/main/LICENSE`
- EverOS core: `https://github.com/EverMind-AI/EverOS/blob/main/LICENSE`
- EverOS carve-outs/optional dependency notice: `https://github.com/EverMind-AI/EverOS/blob/main/NOTICE`

## Is the result good enough?

### Good enough to continue with Markdown as canonical memory: yes

The Phase-2 results remove a major uncertainty. We no longer need to choose between human-readable Git/Markdown truth and competitive retrieval. Both finalists exceed 96% Answer + discovery on the current benchmark and are perfect on the 120 single-document cases.

### Good enough to pick the final memory engine: no

This benchmark starts from already-curated Markdown. It does not measure the difficult part of long-running memory:

- deciding what deserves memory;
- ignoring noise;
- deduplicating repeated evidence;
- consolidating several observations into one durable fact;
- handling contradictions;
- superseding obsolete facts without destroying history;
- respecting direct human corrections;
- preserving provenance;
- deciding when deletion/forgetting is safe;
- rebuilding every derived index from Markdown;
- improving future agent task behavior rather than only answering synthetic questions.

Those dimensions are now more important than another 0.5–1 point of retrieval tuning on Northstar/Tell Aster.

## Direction from here

### 1. Freeze the current retrieval experiment

Treat the current ai-memory 2.4.0 and agent-memory SHA adapters as frozen reference configurations.

Do not tune query construction against the seven/six known failures. Northstar and Tell Aster are already development corpora, and the integration itself was debugged using smoke cases from them.

### 2. Advance agent-memory as the leading architectural candidate

agent-memory is the current lead because it combines:

- the strongest Phase-2 Answer + discovery result (96.7%);
- stronger multi-document A+D than ai-memory (90.0% vs 88.3%);
- an explicit files-are-truth / rebuildable-index invariant;
- local retrieval without a provider key;
- provenance/history/supersession concepts aligned with the human-oversight requirement;
- an independent manage/sleep layer that maps naturally onto the next benchmark.

Its main risk is maturity/release stability: the evaluated system is pinned to a Git commit rather than a stable packaged release.

### 3. Keep ai-memory as a first-class finalist, not a discarded runner-up

ai-memory remains highly attractive because it combines:

- 96.1% A+D and 98.9% answer accuracy;
- very fast measured FTS retrieval (~16 ms);
- very cheap rebuild/index time for these corpora;
- a stable tagged release and native binary distribution;
- Git-backed Markdown wiki semantics close to the desired canonical model.

The lifecycle benchmark may easily reverse the narrow retrieval ordering. It should therefore remain a full comparator.

### 4. Park EverOS for this decision cycle

Do not spend more time making the current retrieval bakeoff work with EverOS before the lifecycle experiment.

Reasons:

- Tell Aster keyword retrieval is still not validated;
- its server requires LLM configuration even for keyword-mode operation;
- packaging needs extra care because the repo contains separately licensed assets;
- ai-memory and agent-memory already provide two strong permissive Markdown-native finalists.

EverOS can be revisited later if its retrieval/indexing path or packaging story changes materially.

### 5. Retire Basic Memory and OpenViking from the active retrieval race

Their Phase-1 retrieval results are materially weaker and their evaluated licensing is unattractive for the intended default Safeplane integration.

Keep the results as baselines/history; do not invest another integration cycle now.

### 6. Reposition Hindsight as a formation/consolidation reference

Hindsight remains valuable because its write path performs much richer extraction, entity resolution, temporal linking, and consolidation than the Phase-2 import paths.

But with ai-memory and agent-memory now matching/exceeding its retrieval quality while keeping Markdown canonical, Hindsight should no longer be the leading production architecture candidate. Use it as a **conceptual or optional benchmark for memory formation quality**, especially if a future lifecycle test can run it without compromising the Git/Markdown source-of-truth invariant.

### 7. Build the lifecycle benchmark next

The next experiment should feed event sequences rather than pre-written memory documents.

A minimum event suite should include:

```text
decision made
same decision repeated
minor irrelevant observation
incorrect hypothesis
bug discovered
temporary workaround
workaround removed
decision superseded
human correction
contradictory new evidence
new project convention
preference learned
historical query about the old state
```

Score at least:

- write precision;
- write recall;
- deduplication;
- consolidation quality;
- current-fact correctness;
- temporal/history correctness;
- contradiction handling;
- provenance retention;
- human-override compliance;
- Markdown readability/editability;
- destructive rebuild fidelity;
- write latency/cost;
- later retrieval/task improvement.

The benchmark should explicitly perform:

```bash
git clone <memory-repo>
rm -rf <all-derived-state>
<backend> rebuild
```

and verify that no accepted knowledge is lost.

### 8. After lifecycle selection, test progressive evidence planning on top

Do not force the eventual memory engine to solve the full read problem alone.

Both Phase-2 finalists have perfect single-document retrieval but weaker multi-document composition. The existing V18/Hybrid results show that explicit evidence planning can recover a different set of hard cases with much more selective reading.

After choosing the canonical memory layer, measure two read modes:

```text
A. native memory recall -> answer
B. native recall / metadata map -> progressive evidence planner -> selective read -> answer
```

The planner/fallback trigger must be evaluator-independent. Candidate signals include multi-clause questions, low score separation, missing evidence obligations, contradictions, and an answer-stage unsupported-fact signal.

### 9. Freeze before a third untouched corpus

The current numbers are development results. Do not keep tuning until the known 180 cases approach 100%.

Freeze:

- agent-memory lifecycle configuration;
- ai-memory lifecycle configuration;
- the chosen read/fallback architecture.

Then evaluate unchanged on a third corpus that has not participated in implementation decisions. That experiment should be the main generalization gate for Safeplane integration.

## Final judgement

The Markdown-first direction is validated strongly enough to continue.

The most defensible current decision is:

> **Use agent-memory and ai-memory as the two finalists for the memory-lifecycle benchmark, with agent-memory as the architectural lead. Keep Markdown in private Git as canonical truth. Treat native indexes as disposable. Stop optimizing static retrieval on the current corpora. After the lifecycle winner is selected, add an explicit progressive evidence-planning/fallback experiment for difficult multi-document recall, then freeze and test on an untouched corpus.**

This is a materially different conclusion from the first memory-system bakeoff. The project no longer needs a database-first memory engine to reach strong retrieval quality, and it no longer needs to compromise the human-readable Git/Markdown source-of-truth requirement to stay competitive with the repository's best retrieval baselines.
