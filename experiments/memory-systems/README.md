# Memory-system retrieval experiment

This experiment compares **Basic Memory**, **OpenViking**, and **Hindsight** on the repository's existing Northstar + Tell Aster evaluation questions.

The experiment is intentionally additive. It does not modify the frozen V18 or RAG baselines.

## What is held constant

All three systems are evaluated against the same contract:

1. The same current Markdown corpora are copied into a backend-specific memory root.
2. The backend ingests only that Markdown. Evaluator gold (`required_documents`, `expected_contains`) is never supplied to the memory system.
3. The backend receives the exact benchmark question and returns ranked retrieval hits.
4. Retrieval hits are mapped back to unique source-document IDs.
5. The full Markdown body of the top mapped documents is passed to the repository's existing `RagAnswerer` with `prompts/rag/system-v1.md`.
6. The answer is scored with the repository's existing deterministic `answer_matches_expected` grader.

The main comparison metric is **Answer + discovery**: the answer passes the deterministic grader **and** all evaluator-required source documents were retrieved. Attribution is reported separately.

For a clean-room setup and reproduction procedure, see [`SETUP.md`](SETUP.md). The first full three-backend result and comparison with Progressive Disclosure V18 are documented in [`docs/memory-system-evaluation-2026-09-22.md`](../../docs/memory-system-evaluation-2026-09-22.md).

This isolates the memory system's ingestion/retrieval behavior from differences in vendor-specific final answer generation.

## Directory model

Each backend gets an independently editable memory tree:

```text
experiments/memory-systems/
├── basic-memory/
│   ├── memory/            # canonical Markdown snapshot for this experiment
│   │   ├── northstar/
│   │   └── tell-aster/
│   └── runtime/           # disposable index/database state (gitignored)
├── openviking/
│   ├── memory/
│   └── runtime/
├── hindsight/
│   ├── memory/
│   └── runtime/
├── .venvs/                # isolated product dependencies (gitignored)
└── results/               # timestamped benchmark output (gitignored)
```

The `memory/` folders are deliberately separate from runtime state. They can later become independent private Git repositories. The experiment SHA-256 hashes the Markdown tree at ingest time and refuses to evaluate after an edit until the backend is re-ingested.

For Basic Memory, this matches its native Markdown-source-of-truth model. For OpenViking and Hindsight, the experiment imposes the Markdown snapshot as the external authoritative source and treats their internal state as rebuildable runtime state.

## Versions pinned by the bootstrap script

The bootstrap defaults are intentionally explicit so the run is reproducible:

- Basic Memory `0.23.2`
- OpenViking `0.4.21`
- OpenViking SDK `0.1.12`
- Hindsight `0.10.1`

Override any pin with the matching environment variable if a platform-specific fix is required. The installed provider version is stored with the ingest marker and in every result manifest.

Basic Memory currently requires Python 3.12+, so the backend environments all use Python 3.12 for consistency. On Intel macOS the bootstrap defaults Hindsight to `hindsight-all-slim`; override `HINDSIGHT_PACKAGE` if necessary.

## Prerequisites

Use the repository's normal environment for the harness itself. It must be able to run the existing RAG evaluation and therefore needs the repo's OpenAI optional dependency and environment settings.

Expected environment variables:

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5-nano   # or the exact model used for the baseline you want to compare against
```

The harness calls the repository's `load_project_env()`, so an existing project `.env` continues to work.

The OpenViking and Hindsight ingestion paths use `OPENAI_API_KEY`. By default they use `MEMORY_EVAL_INGEST_MODEL`, falling back to `OPENAI_MODEL`, for provider-internal semantic extraction. OpenViking additionally uses `text-embedding-3-small` by default.

## Install the isolated backends

From repository root:

```bash
bash experiments/memory-systems/scripts/bootstrap.sh
python experiments/memory-systems/run_memory_eval.py doctor --backend all
```

Nothing from the three products is installed into the repository's main virtual environment.

## Recommended first run

Prepare and ingest the full corpora once, then run a small answer-stage smoke test:

```bash
python experiments/memory-systems/run_memory_eval.py prepare --backend all --reset-memory
python experiments/memory-systems/run_memory_eval.py ingest --backend all --reset-runtime
python experiments/memory-systems/run_memory_eval.py eval --backend all --limit 2
```

If that succeeds, reuse the same ingested state and run all existing questions:

```bash
python experiments/memory-systems/run_memory_eval.py eval --backend all
```

This avoids paying for a second full ingestion after the smoke test. `--limit` is per corpus. Without it the harness evaluates the complete Northstar + Tell Aster datasets currently present in the repository (180 cases at the time this experiment was added).

## Split workflow

The one-command run is equivalent to:

```bash
python experiments/memory-systems/run_memory_eval.py prepare --backend all --reset-memory
python experiments/memory-systems/run_memory_eval.py ingest --backend all --reset-runtime
python experiments/memory-systems/run_memory_eval.py eval --backend all
```

That split is useful when inspecting or editing the Markdown between phases.

### Human edit test

For example, edit a file directly under:

```text
experiments/memory-systems/basic-memory/memory/northstar/
```

An immediate eval will fail because the snapshot hash no longer matches its ingest marker. Rebuild that backend from the edited Markdown:

```bash
python experiments/memory-systems/run_memory_eval.py ingest \
  --backend basic-memory \
  --reset-runtime

python experiments/memory-systems/run_memory_eval.py eval \
  --backend basic-memory
```

This is intentional: machine state must never silently outrank the Markdown ground truth.

## Retrieval budget

The default common evidence budget is six unique source documents:

```text
--top-k-documents 6
```

Each provider may return up to 24 raw hits so fact/chunk-level systems have enough opportunities to map back to six unique documents:

```text
--provider-hit-limit 24
```

Both values are recorded in the manifest and may be changed explicitly for ablations. Do not compare runs with different budgets as if they were the same experiment.

## Backend-specific behavior

### Basic Memory

The worker creates one isolated local project per corpus, indexes the Markdown tree with a full `reindex`, and queries `search-notes` in JSON mode. Its local database/index is under `basic-memory/runtime/`; the Markdown remains under `basic-memory/memory/`.

### OpenViking

The worker starts a private local OpenViking server, imports each corpus into a scoped `viking://resources/memory-eval/<corpus>/` tree, and queries `find()` rather than LLM-backed `search()`. The default ingest processing mode is `semantic_and_vectors`, so OpenViking is allowed to build its normal semantic L0/L1 artifacts while final answers are still generated by the shared evaluator.

For a retrieval-only ablation that disables semantic understanding during ingest:

```bash
export MEMORY_EVAL_OPENVIKING_PROCESSING_MODE=vectors_only
```

The manifest/ingest marker records the processing mode.

### Hindsight

The worker runs Hindsight Embedded in an isolated HOME and creates one bank per corpus. Each Markdown file is retained with a stable `document_id` equal to the corpus document ID and `update_mode=replace`. Recall uses Hindsight's normal `mid` budget plus raw chunks/source facts so retrieved memories can be traced back to canonical source documents.

Useful overrides:

```bash
export MEMORY_EVAL_HINDSIGHT_RECALL_BUDGET=mid
export MEMORY_EVAL_HINDSIGHT_RECALL_MAX_TOKENS=8192
```

## Results

Each eval run creates a new timestamped directory:

```text
experiments/memory-systems/results/<timestamp>/
├── basic-memory/
│   ├── manifest.json
│   ├── trials.jsonl
│   └── ... existing aggregate outputs ...
├── openviking/
├── hindsight/
├── comparison.json
└── comparison.md
```

Each trial retains:

- the exact question and existing evaluator metadata;
- deterministic answer/discovery/attribution outcomes;
- the ordered mapped source documents;
- full raw provider retrieval hits;
- hit-to-document mapping reasons;
- unresolved hit count;
- provider version and metadata;
- retrieval wall time;
- answer-model token usage;
- SHA-256 of the exact Markdown snapshot.

Keep the complete result directory when sharing results for analysis. In particular, do not send only `comparison.md`; the raw trial records are what make failure analysis possible.

Raw result directories stay gitignored. After analysis, create a compact commit-safe snapshot with `scripts/publish_results.py`; published snapshots live under `results/published/` and retain normalized per-case records plus SHA-256 references to the omitted raw provider traces.

## Cost and interpretation notes

This is not a zero-cost benchmark. OpenViking's default semantic ingest and Hindsight retention can make model/embedding calls before the 180 shared answer calls. Provider-internal token/cost telemetry is not normalized because the products expose different information; wall time and available raw metadata are retained instead.

The current corpora are development corpora, so this experiment answers **how these memory systems behave on the benchmark already used by this repository**. It does not replace the repository's stated need for a future untouched corpus.

The products also implement different memory philosophies. The experiment intentionally allows their normal ingestion behavior instead of reducing every system to a vector database. The controlled boundary is the source Markdown, questions, top-document evidence budget, final answerer, and grader.
