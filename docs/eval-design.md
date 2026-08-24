# Eval design

## Goal

Measure discovery, answer application, attribution, stopping, and context efficiency separately for a metadata-first progressive-disclosure knowledge system.

Gold document IDs and expected answer values exist only in the evaluator.

## Dataset status

`datasets/eval-v1.yaml` contains:

- 40 single-document cases, one for every corpus document;
- 20 multi-document composition/precedence cases;
- complete 40/40 corpus-document coverage.

Because V9 was designed after inspecting V7 failures on this dataset, `eval-v1` is now a **validation set**. It is appropriate for measuring whether the redesign fixes known failure classes, but it cannot support the final untouched held-out claim. Freeze a new held-out dataset after V14 is stable.

## Diagnostic baselines

### Oracle answer

Gold bodies are disclosed directly and the model only performs evidence resolution.

```bash
python scripts/run_diagnostics.py --mode oracle --tag single_doc --runs 1 --dry-run
```

This measures the answer/application ceiling. If it is not approximately 100%, fix answer extraction or grading before blaming retrieval.

### Metadata selection only

The model receives the complete activation catalog and must emit a primary document plus only genuinely required additional documents. No body is disclosed and no answer is generated.

```bash
python scripts/run_diagnostics.py --mode selection --tag single_doc --runs 1 --dry-run
```

For single-document cases the primary target is top-1 accuracy >=99% over repeated runs.

For V14, selection-only reports top-1 separately from complete initial-plan recall. A multi-document selection diagnostic counts as successful only when the primary document is relevant and the complete evaluator-required proof set is present in the one-call evidence plan.

## End-to-end V14

```text
activation metadata
    -> build complete atomic evidence plan
    -> disclose distinct planned bodies
    -> submit_answer OR request_more_evidence
    -> if one concrete obligation is unsupported: one bounded recovery selection
    -> answer
```

Single- and predictable multi-document tasks share the ideal two-call trajectory. Recovery is exceptional rather than the normal way to assemble a dependency chain.

## Per-trial dimensions

### Discovery

- primary/first selected document;
- complete selected/read sequence;
- required-document recall;
- document precision;
- wrong documents before first gold;
- reads required for complete discovery.

### Stopping / efficiency

- documents selected after complete discovery;
- extra model calls after complete discovery;
- recovery-selection count;
- fraction of corpus bodies disclosed.

### Answer application

All declared `expected_contains` values must appear in the submitted answer after normalization. These are synthetic values selected to be difficult to guess from priors.

### Attribution

The final sources must include all required documents.

A trial is end-to-end successful only when answer, discovery, and attribution all succeed. Discovery inefficiency is reported separately.

## Repeated runs and reliability targets

Do not use a single run as evidence of reliability.

For 40 single-document cases × 5 repeats = 200 trials:

- 200/200 = 100%;
- 199/200 = 99.5%;
- 198/200 = 99.0%.

The current milestone is >=99% single-document top-1 and end-to-end validation, followed by a new held-out dataset.

The secondary multi-document target is >=95% end-to-end, measured separately so multi-document planning does not obscure the single-document mechanism.

## Raw results

Every end-to-end trial records question, gold documents, expected values, model/prompt fingerprints, selected/read sequence, discovery metrics, answer, citations, token usage, context size, and termination. `trials.jsonl` is the source of truth.

Diagnostic runs write their own `trials.jsonl`, `manifest.json`, and `summary.json` so pure selection and oracle-answer behavior are inspectable without conflating them with the full agent.


## V14 multi-document evaluation

The V12 adaptive experiment regressed to 25% E2E on `multi-dev-v2` because model-authored evidence state was not monotonic and the nested evidence schema produced protocol failures. See `docs/v12-validation-learning-2026-08-24.md`.

V14 retains V13's complete pre-disclosure evidence planning and `datasets/multi-dev-v2.yaml` as development data. V13 reached 30/30 complete initial plans in selection diagnostics and 20/20 discovery in the 20-trial end-to-end multi development gate; the five remaining failures were all empty-answer protocol actions after complete discovery. V14 changes only the evidence-stage action interface, not the selection strategy. See `docs/v13-validation-learning-2026-08-24.md`.

`multi-dev-v2` remains development data. Every required document should contribute a distinct requested fact or transformation. The dataset version is incremented after fixing quoted numeric expectations and strengthening `MDEV-001` so the product document contributes a unique requested service-class fact.

For multi-document selection diagnostics, inspect both `top1_rate` and `complete_initial_plan_rate`. A high top-1 rate with low complete-plan recall is not a successful multi-document retrieval result.

## Model comparison

After V14 evidence-action reliability is established, compare current models by **cost per successful task**, not token price alone. A stronger model that selects the correct evidence in one two-call trajectory can be cheaper than a tiny model that requires recovery or fails.

The repository includes `experiments/model-comparison-v9.yaml` for a later repeated comparison; always inspect the dry-run call count first.


## V10 routing diagnostics

V10 records `active_qualifiers` and `excluded_qualifiers` on every selection. These values come only from the natural-language question; they are not evaluator labels or gold documents. They let a failed retrieval be decomposed further:

1. query-scope parsing failure (an active qualifier was lost or wrongly excluded);
2. document-choice failure despite a correct qualifier split.

An explicit negative qualifier is local to the named branch. It must not erase unrelated active scope. See `docs/v9-validation-learning-2026-08-23.md`.
