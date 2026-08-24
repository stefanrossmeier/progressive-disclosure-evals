# V9 validation learning — qualifier preservation

## What happened

The first larger V9 single-document validation was stopped after 56 completed trials (40 cases in repeat 1 plus EVAL-001 through EVAL-016 in repeat 2).

- 54 / 56 completed trials passed.
- The only failures were EVAL-015, and it failed in both repeats.
- In both failures the primary selection was `commercial.billing.refunds.standard`.
- The required `governance.regions.us.billing-overrides` document was never disclosed.
- The model then correctly applied the wrong disclosed base policy, returning its high-band team/code.

This is a **systematic discovery failure**, not answer extraction, citation, stopping, or random tool-protocol failure.

EVAL-015 asks about a **US-governed standard refund** while also stating that **no D-8 exception applies**. The V9 selector appears to have treated the negative exception statement as evidence that no specialized policy applies and collapsed the request to the global standard-refund policy.

## General lesson: exclusions are local

Routing must preserve the semantics of every explicit qualifier.

A statement such as:

```text
no D-8 exception applies
```

means only:

```text
D-8 is not an active routing branch
```

It does **not** mean:

```text
no exception, override, region, partner rule, product rule, or other specialized authority applies
```

If the same question says `US-governed`, US scope remains active. The selector must compare candidate documents against the set of **still-active qualifiers**, not use one negative condition as a shortcut to the generic base policy.

This is a reusable corpus/retrieval design principle and should apply equally to statements such as `not emergency`, `no partner exception`, `not a migration`, or `no export exception`: each exclusion removes only the branch it names.

## Why metadata alone was not enough

V9 already made the US metadata substantially more activation-oriented and told the model to prefer specific regions/overrides. That improved most historically weak cases, but it was still possible for a small model to lose an active qualifier when a separate qualifier was explicitly negated.

V10 therefore makes qualifier preservation explicit in three places that are naturally part of the retrieval decision:

1. the lean system routing rule;
2. the `select_documents` schema/description;
3. the structured selection result itself, which now records `active_qualifiers` and `excluded_qualifiers`.

The structured fields are not evaluator gold and do not reveal whether the case needs one or multiple documents. They are derived only from the user question. They also make future failures diagnosable: we can distinguish *mis-parsed query scope* from *wrong document choice despite correct scope parsing*.

## Metadata implication

Base-policy metadata should not be triggered merely by negative language about one exception. A base document is appropriate only when no **still-active** more-specific scope qualifier points elsewhere. Regional/partner/product metadata should explicitly remain active when an unrelated exception is excluded.

This is routing information, not answer leakage. The metadata still must not contain the hidden team, code, threshold, duration, queue, or other answer fact.

## Verification implication

A one-pass smoke test is insufficient for a case that was historically unstable: EVAL-015 passed the original 6-case V9 smoke once and then failed twice in the larger run.

The small single-document verification config therefore uses three repeats per case in V10 (6 cases × 3 = 18 trials). Before another 200-trial validation, run a focused selection-only diagnostic for EVAL-015 repeatedly:

```bash
python scripts/run_diagnostics.py \
  --mode selection \
  --case EVAL-015 \
  --runs 10 \
  --prompt prompts/agent/system-v10.md
```

That costs 10 model calls and isolates routing from answering. The target is 10/10 top-1 before spending on the full end-to-end validation.

Because V9/V10 changes are now informed by EVAL-015, `eval-v1` is validation data. A new frozen `eval-v2` is required before making a final held-out reliability claim.
