# Setup and reproduction

## Prerequisites

- Python 3.12+
- `uv` (required by `agent-memory`)
- `git`, `curl`, `tar`, `shasum`
- the repository's normal environment for the shared answer/evaluation harness

Bootstrap installs nothing globally. `ai-memory` is downloaded as a pinned native release into `.tools/`; EverOS gets an isolated venv; `agent-memory` is checked out under `.tools/agent-memory` and installed with its upstream `uv sync --all-packages` workflow.

## Recommended clean run

```bash
bash experiments/markdown-memory-systems/scripts/bootstrap.sh
python experiments/markdown-memory-systems/run_memory_eval.py doctor --backend all
python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend all --reset-memory
python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend all --reset-runtime
python experiments/markdown-memory-systems/run_memory_eval.py probe --backend all --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend all --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend all
```

`prepare` copies the canonical corpora independently for each backend. `ingest` receives no evaluator information and builds only backend-native runtime state. `probe` checks native retrieval plus document mapping without calling the answer model. `eval` checks the Markdown snapshot hash before running.

## What requires external access

Bootstrap needs network access to download the ai-memory release, install EverOS from PyPI, and fetch the pinned agent-memory Git revision. The full answer benchmark additionally requires the configured OpenAI answer model. ai-memory and agent-memory retrieval do not require an LLM API key. EverOS 1.3.x requires `[llm]` configuration even for Tier-1 keyword search; the worker automatically reuses `OPENAI_API_KEY` / `OPENAI_MODEL` for server startup when explicit `EVEROS_LLM__*` settings are absent. The benchmark still sends `method="keyword"`, so EverOS retrieval itself does not make an LLM call.

Ingestion is fail-closed: ai-memory verifies the expected scoped page count after `/admin/write-page` imports, and EverOS syncs each generated episode file independently before checking cascade state. An ingest marker is therefore not written for a backend/corpus pair whose derived retrieval index is incomplete.

## Finalist run after the 2026-09-23 bakeoff

The final scored comparison excludes EverOS because its Tell Aster keyword retrieval path was not validated. For a clean reproduction of the decision-driving runs, use only the two finalists:

```bash
python -m pip install -e ".[model,dev]"
bash experiments/markdown-memory-systems/scripts/bootstrap.sh

python experiments/markdown-memory-systems/run_memory_eval.py doctor --backend ai-memory
python experiments/markdown-memory-systems/run_memory_eval.py doctor --backend agent-memory

python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend ai-memory --reset-memory
python experiments/markdown-memory-systems/run_memory_eval.py prepare --backend agent-memory --reset-memory

python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend ai-memory --reset-runtime
python experiments/markdown-memory-systems/run_memory_eval.py ingest --backend agent-memory --reset-runtime

python experiments/markdown-memory-systems/run_memory_eval.py probe --backend ai-memory --limit 2
python experiments/markdown-memory-systems/run_memory_eval.py probe --backend agent-memory --limit 2

python experiments/markdown-memory-systems/run_memory_eval.py eval --backend ai-memory
python experiments/markdown-memory-systems/run_memory_eval.py eval --backend agent-memory
```

The frozen evaluated agent-memory revision is `70d85e5c22081d9dac88c5e908c88ea0bf13af88`. For exact reproduction, pass that SHA as `AGENT_MEMORY_REF` when bootstrapping.

See `docs/markdown-memory-systems-evaluation-2026-09-23.md` before changing retrieval settings. The next recommended experiment is memory lifecycle/formation, not additional tuning against the current 180 development cases.
