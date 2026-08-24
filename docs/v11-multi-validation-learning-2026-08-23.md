# V11 multi-document validation learning — 2026-08-23

## Result

V11 was evaluated on all 20 `multi_doc` cases in `datasets/eval-v1.yaml` for five repeats with `gpt-5-nano` (100 completed trials).

Observed aggregate metrics:

- strict end-to-end success: **84/100 = 84%**;
- complete declared-document discovery: **95/100 = 95%**;
- literal answer accuracy: **95/100 = 95%**;
- strict declared-source attribution: **86/100 = 86%**;
- first-read hit: **95/100 = 95%**;
- mean document reads: **2.85**;
- median document reads: **3**;
- p95 document reads: **4**;
- mean corpus content disclosed: about **7.3%**.

This is a large improvement over the early V7 multi-document result, but the strict E2E score is still below the desired reliability target.

## What V11 proved

V11's up-front structured evidence plan materially improved multi-document discovery. The remaining failures are no longer dominated by inability to locate any relevant document. Instead they split across:

1. incomplete proof-set discovery in a small number of cases;
2. correct evidence with incomplete final attribution;
3. unnecessary `need_more` recovery despite already sufficient disclosed facts;
4. scope mistakes when a distractor authority from another region is disclosed;
5. answer-grader brittleness for equivalent formatting such as compact UTC ranges;
6. eval-v1 cases whose declared `required_documents` encode one derivation chain even though a smaller body set can sometimes state the requested effective value directly.

The last point must not be solved by weakening multi-document evaluation. It means future multi-document cases should be designed so every declared required document contributes a distinct requested fact or transformation.

## Why multi-document is a first-class target

Multi-document questions are not an edge case for progressive disclosure. They are where progressive disclosure is most valuable: a large knowledge base often distributes a decision across product defaults, infrastructure resolvers, regional authorities, exceptions, approval rules, and operational procedures.

A useful system therefore needs both:

- a very reliable fast path for one-body answers; and
- an adaptive path that can discover additional evidence when one body establishes only part of the answer.

Optimizing only single-document retrieval would leave the most valuable knowledge-base workflow untested.

## V11 architectural limitation

V11 tries to predict the complete evidence set from metadata before reading any body. This has two costs:

- **under-selection:** a dependency only becomes obvious after seeing a body fact, but the first metadata call omitted the needed resolver/authority;
- **over-selection:** the planner preloads several plausible dependency documents even when the first body would have made some of them unnecessary.

The V11 single-document verification also showed this conservatism: answer reliability stayed high, but mean reads increased and stopping efficiency fell.

## V12 direction: adaptive evidence disclosure

V12 keeps the architecture explainable and metadata-first, but makes multi-document discovery iterative:

1. question + metadata -> select the **next smallest high-confidence evidence batch**;
2. disclose those bodies;
3. audit each requested obligation and record a compact **evidence ledger** of supported findings and sources;
4. if a concrete obligation remains missing, feed the supported ledger + missing fact back into metadata selection;
5. disclose only the next body/batch needed for that gap;
6. answer when every material obligation is supported.

A single-document question can still finish in two calls. A real three-document dependency may require four calls, which is acceptable because the extra calls are buying targeted disclosure rather than speculative context loading.

## Evidence-ledger rules

Each evidence audit records:

- the obligation;
- `supported`, `missing`, or `conflict`;
- the concrete finding when supported;
- the disclosed source documents that establish it.

The runtime carries supported findings into the next selection round. This lets a later routing decision use facts learned from bodies, for example:

`Atlas default storage = Slate` -> now find the EU replacement -> `Opal` -> now resolve Opal retention.

A `need_more` response is incoherent when every evidence item is already supported and is retried as a protocol error rather than triggering another speculative read.

## Attribution

Final citations are the union of the model's final source list and the sources attached to supported evidence items. This does not use evaluator gold. It makes attribution follow the model's own structured proof instead of depending on a second, lossy source-list decision at the end.

## Evaluation changes

`eval-v1` remains unchanged as historical validation data.

V12 adds `datasets/multi-dev-v2.yaml`. It is explicitly a **development** set, not a held-out benchmark. Every required document must contribute a distinct requested value or transformation. Examples include:

- product service/tier assignment + base quota + regional ceiling;
- product default storage + regional replacement class + class retention;
- approval band + product ceiling + regional ceiling;
- severity classification + routing fact + regional incident-notice fact.

This lets strict required-document discovery and attribution remain meaningful without forcing redundant reads.

After V12 stabilizes, create a new frozen held-out multi-document eval before making final reliability claims.

## Follow-up after the V12 experiment

The adaptive V12 direction described above was tested on 2026-08-24 and regressed materially with `gpt-5-nano` because model-authored evidence-ledger state was not monotonic and the nested evidence schema caused protocol failures. It is retained here as historical reasoning, not as the current recommendation. V13 returns to complete up-front evidence planning with one bounded recovery. See `docs/v12-validation-learning-2026-08-24.md`.
