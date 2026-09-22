# Memory-system benchmark setup and reproduction

This document describes how to reproduce the Basic Memory, OpenViking, and Hindsight experiment against the repository's existing Northstar and Tell Aster corpora.

The benchmark is designed so that the three memory products differ only in their ingest/retrieval implementation. The final answer stage and deterministic scoring are shared with the existing repository benchmark.

## What the experiment measures

The experiment answers a narrow first question:

> If the same Markdown knowledge base is ingested into three memory systems, how well does each system retrieve the source documents needed to answer the repository's existing 180 questions?

It does **not** yet measure the complete memory lifecycle. In particular, it does not evaluate autonomous memory creation from agent trajectories, consolidation across repeated experiences, forgetting, contradiction resolution, temporal updates, or human correction. Those require a separate memory-lifecycle benchmark.

The controlled evaluation path is:

```text
same Markdown corpus
        |
        v
memory-system-specific ingest
        |
        v
exact same benchmark question
        |
        v
provider retrieval
        |
        v
map provider hits -> source document IDs
        |
        v
top 6 full Markdown documents
        |
        v
shared RagAnswerer / prompts/rag/system-v1.md
        |
        v
shared deterministic answer + discovery scoring
```

Evaluator gold is never supplied to a memory system.

## Directory model

```text
experiments/memory-systems/
├── basic-memory/
│   ├── memory/              # copied Markdown ground truth
│   └── runtime/             # disposable provider state; gitignored
├── openviking/
│   ├── memory/
│   └── runtime/
├── hindsight/
│   ├── memory/
│   └── runtime/
├── .venvs/                  # isolated provider environments; gitignored
├── results/
│   ├── <raw-run>/           # complete local output; gitignored
│   └── published/           # compact commit-safe snapshots
├── scripts/
│   ├── bootstrap.sh
│   └── publish_results.py
└── run_memory_eval.py
```

The backend-specific `memory/` trees are intentionally separate from provider state. Editing the Markdown changes the snapshot hash; evaluation then refuses to use an index built from an older snapshot.

## Pinned provider versions

The default bootstrap pins are:

| Backend | Version |
| --- | --- |
| Basic Memory | `0.23.2` |
| OpenViking | `0.4.21` |
| OpenViking SDK | `0.1.12` |
| Hindsight | `0.10.1` |

The installed versions are recorded in each result manifest.

## 1. Prepare the repository environment

The main evaluation harness requires Python 3.11 or newer. The isolated memory backends use Python 3.12 because Basic Memory requires it.

From repository root, create/activate the normal project environment and install the model dependency if it is not already present:

```bash
python -m pip install -e ".[model,dev]"
```

Verify that Python 3.12 is also available for the backend environments:

```bash
python3.12 --version
```

If it is installed under another name/path:

```bash
export PYTHON_BIN=/path/to/python3.12
```

## 2. Configure model credentials

The final answer model must match the benchmark being compared. The reference run used `gpt-5-nano`.

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5-nano"
```

The harness also loads the repository `.env`, so these values may be stored there instead.

OpenViking and Hindsight use the same API key during ingest. Their provider-internal ingest model defaults to `OPENAI_MODEL`. To make that choice explicit:

```bash
export MEMORY_EVAL_INGEST_MODEL="gpt-5-nano"
```

OpenViking defaults to `text-embedding-3-small` for its embedding stage.

## 3. Install the memory systems

The three products are installed in isolated virtual environments so their dependency trees cannot change the repository's normal environment:

```bash
bash experiments/memory-systems/scripts/bootstrap.sh
```

Check the installation before doing paid ingestion:

```bash
python experiments/memory-systems/run_memory_eval.py doctor \
  --backend all
```

`doctor` checks the corpora and datasets, backend Python/worker executables, installed provider versions, prepared memory trees, ingest markers, and required OpenAI settings.

## 4. Prepare independent Markdown memory trees

Copy the current repository corpora into one memory root per backend:

```bash
python experiments/memory-systems/run_memory_eval.py prepare \
  --backend all \
  --reset-memory
```

For the current benchmark this creates:

- 40 Northstar Markdown files per backend;
- 80 Tell Aster Markdown files per backend.

At this point the memory directories can be inspected or edited like independent repositories.

## 5. Ingest each backend

Run each backend separately. This makes failures and cost easier to attribute and avoids losing progress if a later backend fails.

### Basic Memory

```bash
python experiments/memory-systems/run_memory_eval.py ingest \
  --backend basic-memory \
  --reset-runtime
```

Basic Memory performs a full local reindex and local FastEmbed embedding build over the Markdown snapshot.

### OpenViking

```bash
python experiments/memory-systems/run_memory_eval.py ingest \
  --backend openviking \
  --reset-runtime
```

The reference configuration uses OpenViking's `semantic_and_vectors` processing mode with `no_split` parsing. To run a vectors-only ablation instead:

```bash
export MEMORY_EVAL_OPENVIKING_PROCESSING_MODE=vectors_only
```

Do not compare an ablation with the reference run without labeling the configuration difference.

### Hindsight

```bash
python experiments/memory-systems/run_memory_eval.py ingest \
  --backend hindsight \
  --reset-runtime
```

Hindsight performs fact extraction/consolidation rather than only building a retrieval index, so its ingest is substantially slower. The worker uses `retain_batch()` and defaults to batches of 10 documents:

```bash
export MEMORY_EVAL_HINDSIGHT_BATCH_SIZE=10
```

Progress is written to:

```bash
tail -f experiments/memory-systems/hindsight/runtime/worker.stderr.log
```

Do not delete/reset Hindsight runtime state after a successful ingest unless a clean rebuild is intentionally required.

## 6. Smoke-test retrieval and answering

Before paying for all 180 shared answer calls, evaluate two cases per corpus for each backend:

```bash
python experiments/memory-systems/run_memory_eval.py eval \
  --backend basic-memory \
  --limit 2

python experiments/memory-systems/run_memory_eval.py eval \
  --backend openviking \
  --limit 2

python experiments/memory-systems/run_memory_eval.py eval \
  --backend hindsight \
  --limit 2
```

A smoke eval does not change the ingested memory state.

## 7. Run the complete benchmark

After all three smoke tests pass:

```bash
python experiments/memory-systems/run_memory_eval.py eval \
  --backend all
```

The default common retrieval budget is:

```text
top unique source documents: 6
provider raw-hit limit:      24
```

The run creates a new timestamped raw result directory under:

```text
experiments/memory-systems/results/<timestamp>/
```

Never overwrite an existing run. The harness refuses to do so.

## 8. Publish a commit-safe result snapshot

Raw `trials.jsonl` files retain full provider hits and can become large because source content is repeated in retrieval traces. Runtime logs also contain machine-specific provider state. Raw runs therefore remain gitignored.

Create a compact, auditable snapshot for Git:

```bash
python experiments/memory-systems/scripts/publish_results.py \
  experiments/memory-systems/results/<timestamp> \
  --name YYYY-MM-DD
```

The published snapshot contains:

```text
results/published/YYYY-MM-DD/
├── README.md
├── SHA256SUMS
├── raw-artifacts.json
├── comparison.json
├── comparison.md
├── basic-memory/
│   ├── manifest.json
│   ├── summary.json
│   ├── report.md
│   └── cases.jsonl
├── openviking/
└── hindsight/
```

`cases.jsonl` preserves normalized per-question outcomes, ranked source-document IDs, answer text, citations, discovery status, provider version, latency, token use, and snapshot fingerprints while omitting bulky provider-internal raw hits.

`raw-artifacts.json` records the byte size and SHA-256 of each original raw `trials.jsonl`, so a retained local/archive copy can be verified against the committed snapshot.

## Human-edit / rebuild invariant

The experiment deliberately treats the backend-specific Markdown tree as authoritative input. If a Markdown file is edited after ingest, the stored snapshot hash no longer matches and evaluation fails rather than silently querying stale derived state.

After a human edit, rebuild only the affected backend:

```bash
python experiments/memory-systems/run_memory_eval.py ingest \
  --backend basic-memory \
  --reset-runtime
```

The same invariant applies to OpenViking and Hindsight.

## Useful focused evaluations

Run one case:

```bash
python experiments/memory-systems/run_memory_eval.py eval \
  --backend hindsight \
  --case TA-M-002
```

Run a tagged subset:

```bash
python experiments/memory-systems/run_memory_eval.py eval \
  --backend all \
  --tag multi_doc
```

Change the common source-document budget for an explicitly labeled ablation:

```bash
python experiments/memory-systems/run_memory_eval.py eval \
  --backend all \
  --top-k-documents 8 \
  --provider-hit-limit 32
```

Do not merge results from different budgets into one headline comparison.

## Reproducibility checklist

Before interpreting a run, verify all of the following:

- the same Northstar and Tell Aster dataset fingerprints are used;
- the same Markdown snapshot hashes are used across the comparable backends;
- `OPENAI_MODEL` is unchanged;
- `prompts/rag/system-v1.md` has the expected fingerprint;
- `--top-k-documents` and `--provider-hit-limit` are unchanged;
- backend provider versions match the intended run;
- ingest modes/recall budgets are unchanged;
- no evaluator gold was used during provider ingest or retrieval;
- the full raw run is retained somewhere if provider-level forensic analysis may be needed later.

## Known interpretation limits

This benchmark reuses Northstar and Tell Aster, which have already participated in development of the repository's retrieval approaches. Treat them as development/validation corpora, not untouched evidence of generalization.

More importantly, static corpus ingest + retrieval is only the first layer of a memory-system evaluation. A complete agent-memory benchmark still needs to measure:

- automatic selection of what should be remembered;
- repeated experience and consolidation;
- updates that supersede older facts;
- contradiction handling;
- temporal validity;
- deletion/forgetting;
- human edits and authoritative corrections;
- rebuild from the Git/Markdown ground truth;
- whether memory improves later agent tasks rather than only question answering.

The current benchmark should therefore be described as the **memory-system retrieval benchmark**, not as proof that one product is the best complete agent memory.
