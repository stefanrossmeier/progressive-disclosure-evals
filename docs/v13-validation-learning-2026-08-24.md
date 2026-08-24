# V13 validation learning — 2026-08-24

## Result

V13 restored the reliable complete-plan architecture after the V12 adaptive-state regression.

Focused selection diagnostics on `multi-dev-v2` ran 30 trials (10 cases × 3 repeats):

- valid/successful selection: 30/30;
- top-1 hit: 30/30;
- complete initial evidence plan: 30/30.

The difficult single-document verification ran 24 trials (8 cases × 3 repeats):

- task success: 24/24 (100%);
- discovery: 24/24 (100%);
- first-read hit: 24/24 (100%);
- mean documents read: 1.54.

The genuine multi-document development verification ran 20 trials (10 cases × 2 repeats):

- task success: 15/20 (75%);
- discovery: 20/20 (100%);
- first-read hit: 20/20 (100%);
- mean documents read: 3.20.

## What the five multi-document failures actually were

All five failed trials (`MDEV-004` repeat 1, `MDEV-005` repeat 1, `MDEV-006` repeat 1,
`MDEV-008` repeat 2, and `MDEV-010` repeat 2) had already disclosed every evaluator-required
document before failure. None was a retrieval miss.

Every failure had the same protocol shape:

1. selection produced a complete evidence plan;
2. all required bodies were disclosed;
3. the model called `resolve_evidence` with `status="answer"`;
4. the model left `answer` empty;
5. the stateless protocol retry repeated the same malformed behavior;
6. the run terminated as `invalid_model_action`.

This makes the V13 multi-document result primarily a resolver-interface reliability problem, not a
multi-document discovery problem.

## V14 decision

Do not change the V13 selection strategy. It achieved the desired 100% complete-plan discovery on
this focused development gate and preserved 100% single-document task success.

Instead, simplify the evidence-stage action interface:

- `submit_answer(answer)` for a complete, non-empty user-facing answer;
- `request_more_evidence(missing_information)` for one precise unresolved obligation.

The model no longer has to populate a conditional four-field object containing a status, answer,
source list, and missing-information field simultaneously. Final attribution comes deterministically
from the model-authored evidence plan once `submit_answer` succeeds.

A protocol retry must also be corrective rather than identical: the retry state explicitly states why
the previous action was invalid (for example, an empty `answer`) and asks for one valid evidence-stage
action.

## General lesson

When retrieval is already correct, avoid adding more retrieval machinery to compensate for a
structured-output failure. Diagnose stage boundaries separately. A small control/action schema can
be more reliable than one function containing mutually exclusive modes and fields, especially for a
small model.
