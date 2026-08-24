# V10 multi-document validation learning — 2026-08-23

## Status of the partial run

The uploaded V10 multi-document run contains 25 completed trials: EVAL-041 through EVAL-045 twice and EVAL-046 through EVAL-060 once.

Observed from the raw trials:

- expected answer values present: 23/25 = 92%;
- complete required-document discovery: 18/25 = 72%;
- all required sources cited: 13/25 = 52%;
- end-to-end success: 18/25 = 72% when using the trial `overall_success` field;
- the dominant failures are evidence-set completeness and attribution, not inability to synthesize the final values.

This is materially different from the old V7 multi-document behavior. V10 often knows the answer after seeing a subset of the intended proof chain, but the selector/evidence stage does not reliably construct and preserve that chain.

## Failure classes

### 1. Missing dependency in the initial evidence set

Examples include effective product/region questions where the model opened a regional authority plus an infrastructure resolver but omitted the product assignment, or vice versa.

The general pattern is:

`base assignment -> resolver -> modifier/override -> effective result`

For a question that explicitly asks what *remains assigned*, what *actually applies*, or what *follows from* an effective class/tier, the proof may require more than the document containing the final numeric value.

### 2. Precedence/fallback answered from only the winning rule

For an in-limit D-8 US refund, the exception document contains the winning team/code, so Nano can answer correctly without opening the US authority that establishes that the regional override is bypassed. For an over-limit D-8 case, the reverse dependency is needed to establish fallback.

When a question names multiple potentially governing scopes and asks which rule governs, the evidence plan should include the authorities needed to prove the precedence/fallback relationship, not merely the document that happens to contain the final value.

### 3. Compound questions were not decomposed

EVAL-057 asks both the standard maintenance window and the approval for a 50-minute change. One V10 trial selected only the window policy. The issue is not ambiguous metadata; it is failure to turn a compound question into two independent evidence obligations.

### 4. Correct proof set, incomplete citation

Several trials opened all required documents and produced the right answer but cited only the document containing the final value. A source that materially establishes a base assignment, regional scope, dependency, or precedence premise is part of the proof and should be cited even if another body repeats the final value.

### 5. Recovery can fail when the answer looks superficially complete

The current evidence stage requests more documents only when it notices a missing fact. If the disclosed subset already contains the final answer value, it can answer immediately and never discover the missing proof premise. This is why selection and evidence resolution need a shared explicit evidence plan.

## V11 design

V11 keeps the same progressive-disclosure architecture and ideal two-call path:

1. question + activation metadata -> structured evidence plan and document selection;
2. selected bodies + evidence plan -> answer or one bounded recovery selection.

The first call now emits an `evidence_plan`: atomic obligations mapped to document IDs. The evidence call receives that plan as non-factual routing state. It must verify every obligation against disclosed bodies before answering.

This does not expose evaluator gold or a single/multi label. The plan is derived only from the natural-language question and catalog metadata.

## Evidence-planning rules

- Decompose every requested output into an evidence obligation.
- Add dependency obligations when a requested result depends on a base assignment plus a resolver/override.
- Add competing-authority obligations when precedence/fallback must be proved.
- Do not re-derive prerequisites already supplied as case facts.
- Cite every document that materially contributes a fact, scope decision, dependency, fallback, or precedence conclusion.
- Do not cite extra documents that were opened accidentally and contributed nothing.

## Benchmark integrity

This patch does **not** relax `required_documents` in eval-v1. Some existing required sets may ultimately prove stricter than the minimum possible proof path, but changing them now would confound agent improvement with evaluator relaxation. First test whether explicit evidence planning can satisfy the current strict benchmark. If systematic correct answers still use smaller defensible proof sets, then revise the multi-document evaluator separately and document accepted proof alternatives.

Because eval-v1 has now informed V9-V11, it is validation data. Freeze a new eval-v2 before making final reliability claims.
