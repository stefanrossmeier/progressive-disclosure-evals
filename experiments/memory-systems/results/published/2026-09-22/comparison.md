# Memory-system comparison

The primary cross-system metric is **Answer + discovery**: the shared answer grader passes and every evaluator-required document is present in the provider-ranked unique-document set. Attribution is reported separately.

| Backend | Answer | Discovery | Answer + discovery | Attribution | Single-doc A+D | Multi-doc A+D | Mean docs | Retrieval ms | Unresolved hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| basic-memory | 88.9% | 88.9% | 87.8% | 85.0% | 95.0% | 73.3% | 5.98 | 2047.3 | 0.00 |
| hindsight | 95.0% | 96.7% | 93.9% | 93.3% | 99.2% | 83.3% | 5.93 | 974.3 | 2.26 |
| openviking | 88.3% | 87.8% | 86.7% | 82.2% | 94.2% | 71.7% | 6.00 | 206.8 | 0.37 |

## Interpretation guardrails

- Every backend is scored on the same Northstar + Tell Aster cases and the repository's deterministic answer matcher.
- The final answer stage is the repository's existing `RagAnswerer` with `prompts/rag/system-v1.md` and `OPENAI_MODEL`.
- Provider retrieval is mapped to unique source documents; the full Markdown body of each mapped document is supplied to the common answerer.
- Provider ingestion cost and provider-internal model calls are not normalized because the three products expose different telemetry. Ingest wall time and raw provider metadata are preserved in manifests/markers.
- Northstar and Tell Aster are development corpora, so this experiment compares behavior on the existing benchmark rather than establishing untouched generalization.
