# Markdown-native memory-system retrieval experiment

This experiment compares three permissively licensed, Markdown-native memory systems on the repository's existing frozen Northstar + Tell Aster retrieval benchmark:

- `akitaonrails/ai-memory` (MIT), pinned release `2.4.0` by default.
- `EverMind-AI/EverOS` (Apache-2.0), pinned PyPI release `1.3.1` by default.
- `tigerless-labs/agent-memory` (MIT), installed from a Git checkout and recorded at an exact commit SHA by bootstrap.

It reuses the same evaluation boundary as `experiments/memory-systems`: backend retrieval chooses documents, the repository's existing `RagAnswerer` generates the answer, and the existing deterministic grader scores it. Evaluator gold is never supplied to a backend.

## Why these retrieval modes

The goal is to compare memory retrieval rather than provider configuration:

- **ai-memory:** native FTS5 search through its read-only JSON API; documents are written as pinned wiki pages through the public `/admin/write-page` API. Ingestion verifies the expected corpus page count before writing an ingest marker.
- **EverOS:** native `method="keyword"` BM25 retrieval. Each corpus document is represented as its own valid EverOS episode Markdown file and projected with deterministic per-file `cascade sync`, avoiding bulk-rebuild failure modes while keeping Markdown canonical. Ingestion checks cascade state before writing an ingest marker. No embedding/reranker is used. EverOS 1.3.x still requires an `[llm]` provider to be configured for server startup; the worker automatically maps the repository's existing `OPENAI_API_KEY` / `OPENAI_MODEL` into EverOS when explicit `EVEROS_LLM__*` settings are absent. Keyword retrieval itself makes no retrieval LLM call.
- **agent-memory:** native local BM25 `recall`; each corpus document is recorded as one durable Markdown memory and the index is rebuilt before evaluation.

All three therefore have a provider-free retrieval path for this first bakeoff. A later ablation can enable each system's vector/hybrid path explicitly.

## Layout

```text
experiments/markdown-memory-systems/
├── ai-memory/{memory,runtime}/
├── everos/{memory,runtime}/
├── agent-memory/{memory,runtime}/
├── .tools/                 # pinned binaries/checkouts, gitignored
├── .venvs/                 # isolated Python workers, gitignored
├── workers/
├── scripts/
└── results/
```

The `memory/` trees are clean copies of the repository corpora and are the experiment input contract. Backend-native stores and derived indexes live only under `runtime/`.

## Run

From repository root:

```bash
bash experiments/markdown-memory-systems/scripts/bootstrap.sh
python experiments/markdown-memory-systems/run_memory_eval.py doctor --backend all
python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend all --reset-memory
python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend all --reset-runtime
python experiments/markdown-memory-systems/run_memory_eval.py probe --backend all --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend all --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend all
```

The shared answer stage still needs the repository's normal OpenAI configuration (`OPENAI_API_KEY`, `OPENAI_MODEL`). Retrieval itself remains local in the default configuration. ai-memory and agent-memory need no provider; EverOS 1.3.x requires an LLM provider configuration to boot its server, but `method="keyword"` retrieval does not call that provider. The worker reuses the repository OpenAI settings automatically unless explicit `EVEROS_LLM__*` values are supplied.

## Reproducibility

`bootstrap.sh` records the exact `agent-memory` checkout SHA at `.tools/agent-memory.sha`; each backend's `hello`/ingest metadata is copied into the result manifests. Override pins only deliberately:

```bash
AI_MEMORY_VERSION=2.4.0 \
EVEROS_VERSION=1.3.1 \
AGENT_MEMORY_REF=<commit-or-tag> \
  bash experiments/markdown-memory-systems/scripts/bootstrap.sh
```

For a publication run, set `AGENT_MEMORY_REF` to a reviewed full commit SHA rather than leaving it at `main`. The bootstrap always records the exact resolved SHA, so even exploratory runs remain auditable.

## Licensing scope

This experiment installs only each project's permissively licensed core path. It does not vendor upstream benchmarks, fixtures, models, or optional extras. In particular, keep EverOS non-core/test assets out of any eventual Safeplane distribution unless they have been audited separately. Repeat the transitive-dependency/license audit before bundling any backend into Safeplane; this experiment is an evaluation harness, not a redistribution approval.

## Interpretation caveat

Northstar and Tell Aster were used during development of earlier retrieval approaches. They are validation/development corpora, not untouched evidence of generalization. The purpose of this experiment is a controlled comparison on the existing benchmark and preparation for a later memory-formation experiment.

## Final status — 2026-09-23

The retrieval phase is complete enough to narrow the active comparison to two finalists:

| Backend | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **agent-memory** | 98.3% | 97.8% | **96.7%** | **100.0%** | **90.0%** | **Finalist** |
| **ai-memory** | **98.9%** | 97.2% | 96.1% | **100.0%** | 88.3% | **Finalist** |
| EverOS | — | — | — | — | — | Parked; Tell Aster keyword retrieval not validated |

The commit-safe final aggregates are stored at:

```text
experiments/markdown-memory-systems/results/published/2026-09-23/
```

The full interpretation, comparison with the earlier Basic Memory / OpenViking / Hindsight experiment, licensing notes, failure analysis, and recommended next phase are in:

```text
docs/markdown-memory-systems-evaluation-2026-09-23.md
```

### Recommended reproduction path

For the two finalists, prefer explicit backend commands rather than `--backend all`:

```bash
python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend ai-memory --reset-memory
python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend agent-memory --reset-memory

python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend ai-memory --reset-runtime
python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend agent-memory --reset-runtime

python experiments/markdown-memory-systems/run_memory_eval.py probe --backend ai-memory --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py probe --backend agent-memory --limit 2

python experiments/markdown-memory-systems/run_memory_eval.py eval --backend ai-memory
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend agent-memory
```

EverOS remains in the harness for diagnostic/reproduction work, but it is not part of the final scored comparison. Do not interpret a partial EverOS run as comparable to the two 180-case finalist runs.
