# V12 validation learning — 2026-08-24

## Result

V12 tested an adaptive multi-document design in which the model selected one or two bodies, emitted a structured evidence ledger, and then used that ledger to drive later metadata selection.

Observed verification results with `gpt-5-nano`:

- difficult single-document set: 20/24 end-to-end = 83.3%; discovery 24/24 = 100%; first-read 22/24 = 91.7%; mean 2.92 model calls;
- genuine multi-document development set: 5/20 end-to-end = 25%; discovery 13/20 = 65%; answer accuracy 6/20 = 30%; mean 4.15 model calls.

This is a clear regression from V11 and should not be interpreted as evidence that progressive disclosure or multi-document composition is inherently unreliable. The failure is specific to the V12 adaptive state-management mechanism.

## Primary failure: non-monotonic model-authored evidence state

V12 asked the model to regenerate an obligation-level evidence ledger after every disclosure. The runtime then replaced the previous ledger with the newly generated one.

In raw traces, facts marked supported in one round were frequently marked missing again in a later round even though the supporting body remained disclosed. This caused the agent to restart already solved parts of the problem, select unrelated documents, and exhaust document or selection-round limits.

Examples:

- `MDEV-001`: EU data handling established Slate -> Opal in round 1. After storage retention was added, the next audit changed the previously supported Atlas default-storage obligation back to missing and triggered an unrelated EU billing selection.
- `MDEV-003`: product assignment and EU ceiling were established, but later audits reset several obligations to missing and the run exhausted the selection-round budget.
- `MDEV-006`: D-8 exception evidence was supported in the first audit, then the next audit forgot it and reopened the entire proof.
- single-document `EVAL-026`: the question explicitly states that the incident is not APAC-governed. The adaptive audit nevertheless created new obligations to prove that APAC did not apply, leading to four document reads and a selection-round-limit failure.

General lesson: if adaptive multi-step retrieval is revisited, accumulated evidence state must be monotonic and runtime-owned. A later model call may add or challenge a finding with explicit conflicting evidence, but it must not silently erase a previously grounded fact merely by omitting or rewriting the ledger entry.

## Secondary failure: structured-output burden

V12 expanded `resolve_evidence` from four simple fields to a nested array of evidence items with per-item status, finding, and sources plus global answer/source/missing fields. `gpt-5-nano` produced repeated `invalid_model_action` terminations even after the correct document had been selected.

Examples include `EVAL-004`, `EVAL-020`, `MDEV-004`, `MDEV-005`, `MDEV-007`, and `MDEV-010`.

The strict schema made protocol correctness a larger source of failure than knowledge retrieval. For this benchmark, simpler forced tool schemas are more reliable.

## Negative scope must not become an evidence obligation

V10/V11 correctly learned that `non-EU` or `not APAC` excludes that routing branch. V12 sometimes turned the exclusion itself into a fact that needed documentary proof.

That is wrong. The user's question supplies its own scope. The runtime should use a negative qualifier to prevent routing into an excluded branch; it should not retrieve regional documents to prove that the excluded branch is absent.

## Multi-document diagnostics were too weak

The selection-only diagnostic previously reported `success=true` when the primary/top-1 document was a gold document. That is useful for single-document routing but insufficient for multi-document planning.

For a multi-document case, a correct first document can coexist with an incomplete proof set. V13 therefore defines selection-diagnostic success as:

1. primary/top-1 is one of the required documents; and
2. the complete required document set is present in the initial evidence plan.

Top-1 remains a separately reported metric.

## Development-set corrections

`multi-dev-v2` is retained because genuine multi-document questions are strategically important, but two evaluator issues were corrected:

- comma-containing numeric expectations are quoted as strings rather than being parsed by YAML as separate integer list entries;
- `MDEV-001` now requests Atlas's service class as well, ensuring the product document contributes a fact not duplicated by the EU regional document.

## V13 decision

V13 returns to the more reliable V11 shape:

1. one forced metadata-selection call builds a complete atomic evidence plan (`need -> document_id`);
2. all currently predictable necessary bodies are disclosed together;
3. one simple forced evidence-resolution call answers;
4. one bounded recovery selection is available only for a concrete missing obligation.

The runtime still receives no evaluator label, required-document count, gold IDs, or expected values.

For multi-document questions, the optimization target is not "read one document first". It is "plan the smallest complete proof set from activation metadata, then disclose those bodies once." This preserves the two-model-call ideal path for both single- and multi-document questions while avoiding the non-monotonic state machine that failed in V12.
