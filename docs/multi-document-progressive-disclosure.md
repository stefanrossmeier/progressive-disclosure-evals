# Multi-document progressive disclosure

## Design goal

Progressive disclosure should reliably answer questions whose result depends on several independent or chained authorities while loading only the bodies that materially contribute to the answer.

The runtime is task-type agnostic: it is never told whether a case is single-document or multi-document. It must infer the necessary proof set from the question plus activation metadata.

Common patterns include:

```text
product assignment -> infrastructure resolver -> regional ceiling
```

```text
base policy + named exception + regional fallback
```

```text
classification + routing + regional notification requirement
```

## V13 mechanism

```text
question + compact activation metadata
              ↓
atomic evidence plan
  need A -> document X
  need B -> document Y
  need C -> document Z
              ↓
disclose the distinct planned bodies
              ↓
resolve all requested facts and transformations
              ↓
answer + material sources
```

The normal path is two model calls regardless of whether one, two, three, or four bodies are required. A second metadata-selection round is reserved for a concrete obligation that the initial plan predicted incorrectly or could not establish from the disclosed bodies.

## Why complete planning instead of V12-style adaptive ledgers

The V12 experiment used small batches followed by model-authored evidence ledgers. With `gpt-5-nano`, that state was not monotonic: facts established in one audit disappeared in later audits, exclusions became new evidence requirements, and nested structured outputs caused protocol failures. The genuine multi-document verification fell to 25% end-to-end despite 95% top-1 routing.

Activation metadata already describes WHAT each body contains and WHEN it applies. For this corpus, the more reliable use of that metadata is to plan the complete currently predictable proof set before body disclosure, then use body content for evidence and synthesis.

## Planning rules

- Decompose every requested output into an atomic obligation.
- Map each obligation to the body expected to establish it.
- Multiple obligations may map to the same body; disclose each distinct body only once.
- Treat scope, product, marker, level, and other facts explicitly supplied by the question as inputs, not as evidence gaps.
- A negative qualifier such as `non-EU` excludes EU routing; it does not require an EU document to prove the exclusion.
- Preserve contrasts. If the question asks for both the normal quota and a lower regional ceiling, both values must be returned. If it asks for a default queue without a regional replacement as well as a regional notice fact, do not substitute the effective regional queue for the requested default.
- For precedence/fallback, include both authorities only when both materially support the requested explanation.
- Do not select a generic derivation document merely to recompute a fact the question already supplies.

## Evaluation

Multi-document selection diagnostics must not use top-1 alone. Report separately:

- top-1 hit;
- complete initial-plan recall;
- document precision;
- final required-document recall;
- answer accuracy;
- attribution;
- recovery frequency;
- document reads and model calls;
- knowledge fraction disclosed.

A selection diagnostic counts as successful only when top-1 is relevant **and the complete required proof set is planned**. This prevents a correct first document from hiding incomplete multi-document discovery.

Every development/held-out multi-document case should make each required document contribute a distinct requested fact or transformation. Otherwise the benchmark rewards reproducing an evaluator-authored derivation rather than solving the information need.
