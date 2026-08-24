# V10 single-document validation learning — 2026-08-23

## Result

V10 was evaluated on all 40 single-document cases for five repeats (200 trials) with `gpt-5-nano`.

Observed aggregate metrics:

- complete required-document discovery: 199/200 = 99.5%;
- first-read/top-1 hit: 197/200 = 98.5%;
- end-to-end success: 197/200 = 98.5%;
- mean document reads: 1.41;
- median document reads: 1;
- p95 document reads: 3;
- mean corpus content disclosed: about 3.6%.

The aggregate end-to-end number hides three different failures. They must not be treated as one retrieval problem.

## Failure decomposition

### EVAL-004 and EVAL-012: protocol/runtime failures after correct retrieval

In both trials the correct and only required document was selected first and disclosed. The second forced `resolve_evidence` model call terminated as `invalid_model_action`, so no answer was recorded.

These are not knowledge-discovery failures and there was no observed wrong Northstar answer. They expose a production reliability issue in strict structured-action handling.

A bounded retry of the exact same stateless structured request is appropriate for malformed required-tool output. This is different from the historical conversational protocol-repair loops: it does not add reasoning/navigation state, does not reveal evaluator gold, and is attempted only after an invalid response envelope/argument shape.

The runtime should record the invalid response reason and retry count so retries remain visible in cost/reliability metrics.

### EVAL-020: semantic negation was routed as positive scope

The question said `non-EU` plus `EX-TEMP`. The selector recorded `non-EU` as an active qualifier and selected EU data handling instead of export retention.

General rule: lexical forms such as `non-X`, `not X`, `outside X`, or `X does not apply` must be represented as an exclusion of X, not as an active X routing signal. Negative scope remains local: excluding EU does not remove the active export/EX-TEMP scope.

### EVAL-024 and EVAL-026: unnecessary prerequisite derivation hurt top-1

These trials eventually succeeded but missed top-1.

- EVAL-024 already supplied `Lattice-3`; severity classification was selected before escalation routing.
- EVAL-026 already supplied the ordinary `Lattice-1` classification; base classification was selected before the P-17 override.

General rule: do not load a document whose only purpose is to derive a prerequisite that the question already provides. Progressive disclosure should consume stated facts directly and disclose the next authority that uses them.

This matters for both accuracy and efficiency: redundant prerequisite reads create extra opportunities for distraction and make first-read metrics look worse even when eventual discovery succeeds.

## Interpretation

V10 demonstrates that activation-oriented metadata plus explicit selection is close to the desired single-document reliability. The remaining single-document work is narrower than another retrieval redesign:

1. normalize semantic negation as excluded routing scope;
2. avoid re-deriving prerequisites supplied by the question;
3. make required structured calls resilient to rare malformed model actions with one visible stateless retry;
4. keep stopping/over-selection as a separate efficiency metric rather than trading away answer reliability to optimize it.

Because eval-v1 has now directly influenced several changes, it is a validation set. Final reliability claims require a new frozen eval-v2 after the mechanism is frozen.

## Multi-document warning discovered while inspecting the same run family

Do not interpret the current multi-document end-to-end score before auditing the gold evidence design. Several existing multi cases require every document in a derivation chain to be opened/cited even when a smaller disclosed set already directly establishes the answer. That conflicts with the project's goal of minimum sufficient disclosure and with the runtime instruction to cite only direct supporting sources.

The multi-document benchmark should distinguish a genuinely necessary evidence set from a historical/intended derivation path. If multiple minimal proof paths exist, the evaluator must accept them rather than requiring one exact document set. This should be addressed before tuning the runtime against multi-document aggregate pass/fail.
