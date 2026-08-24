# How to design corpus metadata for progressive disclosure

## Purpose

Corpus metadata is not a miniature summary of a document. It is the **discovery and activation layer** that lets a model decide which document body to disclose.

For a metadata-first knowledge system, a description has one primary job:

> Given only the user question plus the metadata for many documents, make the correct document distinguishable from its neighbors without revealing the factual answer.

This follows the same progressive-disclosure principle used by Anthropic Agent Skills: the always-visible metadata should say both **what the resource contains** and **when it should be used**. The full body remains hidden until selected.

Authoritative references:

- Anthropic, Agent Skills overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Anthropic, Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropic, Equipping agents for the real world with Agent Skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- OpenAI, Harness engineering: https://openai.com/index/harness-engineering/

## Required shape

Every document front matter contains:

```yaml
---
id: commercial.billing.refunds.exceptions
title: Refund Exceptions
description: Named refund-exception policy. Use when a refund mentions D-8, verified duplicate billing, exception eligibility, age or amount limits, partner-sold restrictions, or fallback after an exception; prefer this over the standard refund policy when a matching exception trigger is present.
version: 2
---
```

The description should normally have two semantic parts:

1. **WHAT** — the kind of knowledge or decision contained in the body.
2. **WHEN** — the query conditions, vocabulary, qualifiers, or triggers that should activate this document rather than a neighboring document.

A useful template is:

> `<WHAT this document governs>. Use when <specific query triggers/conditions>. <Optional distinction or precedence against the nearest confusing neighbor>.`

Do not force every description into identical prose. The semantic information matters more than the exact sentence structure.

## Routing vocabulary is not answer leakage

A progressive-disclosure catalog must expose enough vocabulary to route a question. Hiding every distinctive term makes correct activation unnecessarily difficult.

It is appropriate to put a term in metadata when it is **known in the question before retrieval and functions as a routing key**. Examples in this corpus include:

- `MIG-2` for the migration-credit policy;
- `D-8` for the duplicate-billing refund exception;
- `PINE-6` for a named partner exception;
- `P-17` for a severity override;
- `EX-TEMP` for staged export retention.

Those values identify *which policy to open*. They do not answer the downstream question.

Do **not** put hidden answer facts in metadata merely to improve an eval. For example, the following belong only in the body when they are the facts being retrieved:

- approval team names;
- approval or workflow codes requested by the question;
- thresholds and monetary values that are the answer;
- durations that are the answer;
- queue names or classes that are the answer.

The practical test is:

> If the user already supplied this term, does repeating it in metadata help select the correct authority without revealing the requested result?

If yes, it is usually legitimate routing vocabulary.

## Make neighboring documents mutually discriminative

Metadata quality is relational. A description can be accurate in isolation and still be poor if a sibling document sounds almost identical.

For every document, identify its closest competitors and state the deciding boundary where useful.

Examples:

### Base policy vs exception

Weak:

```text
Refund Exceptions — Exception cases that alter standard refund bands.
```

Better:

```text
Named refund-exception policy. Use when a refund mentions D-8, verified duplicate billing,
exception eligibility, age or amount limits, partner-sold restrictions, or fallback after an
exception; prefer this over the standard refund policy when a matching exception trigger is present.
```

The second version makes `refunds.exceptions` distinguishable from `refunds.standard` without exposing the approval result.

### Definition vs quantitative limit

Weak:

```text
Storage Classes — Definitions and capacity characteristics for named storage classes.
```

Better:

```text
Storage-class definition and capacity policy for named classes such as Opal, Slate, and Amber.
Use when a question asks a storage class's logical object/capacity ceiling per tenant shard;
use storage retention for retention durations.
```

The negative distinction prevents a model from confusing storage capacity with storage retention.

### Base rule vs regional override

For a region-qualified question, the regional metadata must make the qualifier salient. A description such as "billing adjustments for US customers" is often too weak when a global refund policy is also available.

Prefer metadata that states that a US-governed billing question should route to the US override, while also explaining that a narrower named exception can still take precedence.

## Treat negative qualifiers as local exclusions

A query can contain several routing qualifiers at once. Keep positive scope and explicit exclusions separate.

For example, `US-governed standard refund; no D-8 exception applies` contains active US/regional and refund qualifiers plus one excluded D-8 branch. The phrase `no D-8` must not be generalized into `no specialized rule`.

Write base-policy metadata so it wins only when no still-active more-specific qualifier applies. Write specialized metadata so an unrelated exclusion does not accidentally deactivate its region, product, partner, or process scope.

This matters especially for small models because negative wording can create a strong lexical pull toward descriptions containing phrases such as “when no exception applies.” Prefer semantic boundaries such as “when no still-active region/partner/exception authority applies.”

This principle was established empirically by the repeated V9 EVAL-015 failure; see `docs/v9-validation-learning-2026-08-23.md`.

## Describe precedence when precedence affects discovery

The body remains authoritative for the actual rule, but metadata may state **which kind of authority should be consulted first**.

Good routing metadata can say:

- prefer this exception when its marker is present;
- use the regional override for region-qualified standard billing questions;
- use the base policy only when no named exception or regional override applies;
- use compute quotas for concurrent capacity, not compute-tier definitions.

This is discovery information, not the hidden answer.

Do not put the concrete winning team/code/threshold in metadata.

## Include terminology users will actually ask with

A human-maintained title is not enough. Descriptions should include stable synonyms and domain language likely to appear in queries when those terms distinguish the document.

Examples:

- `outage`, `service credit`, `Lattice`;
- `card-network chargeback` vs `invoice-line dispute`;
- `break-glass` vs `credential rotation`;
- `customer notice` vs `executive briefing`;
- `paging/acknowledgement` vs `escalation team/queue`;
- `concurrent compute units` vs `scheduler marker`;
- `object/capacity ceiling` vs `retention duration`.

Do not stuff descriptions with every noun in the document. Add terms that materially improve routing against plausible alternatives.

## Metadata anti-patterns

Avoid these patterns:

### Human summary only

```text
Rules for refunds, approvals, and exceptions.
```

It describes content but does not say when this document should win against neighboring refund documents.

### Generic field matching

```text
Contains team, code, duration, and approval information.
```

Many documents contain those fields. This creates false routing signals.

### Answer leakage

```text
D-8 refunds use Team PEBBLE and GLASS-12.
```

This bypasses progressive disclosure because the catalog now contains the answer.

### Hidden trigger vocabulary

If `D-8` is the decisive routing marker and users ask with `D-8`, omitting it from every metadata entry forces the model to guess which generic refund document contains it.

### Indistinguishable siblings

```text
Compute Tiers — Compute tier rules.
Compute Quotas — Compute tier rules and limits.
```

State the decision boundary: scheduler/tier identity versus concurrent capacity.

### Metadata that tries to become the document

The description is a router, not a compact policy manual. Detailed implementation or factual rules belong in the body.

## Authoring workflow

For every new document:

1. Write the body and identify the authority it represents.
2. List 3–8 realistic user phrases or conditions that should cause this document to be opened.
3. Identify the two or three documents most likely to be confused with it.
4. Write a description containing WHAT + WHEN and, where useful, one discriminating boundary.
5. Check that routing identifiers supplied by users are present when they are necessary for activation.
6. Remove answer facts that would let a user answer the benchmark without opening the body.
7. Run `python scripts/validate_corpus.py`.
8. Run the selection-only diagnostic before the end-to-end benchmark.
9. Inspect every repeated selection error as a metadata-design problem first, not as a reason to add orchestration.

## Evaluation standard

Metadata should be evaluated independently from answering.

For single-document cases:

```text
question + complete metadata catalog
        -> exactly one primary document selection
```

Report at minimum:

- top-1 document accuracy;
- top-k/set recall where multi-document selection is allowed;
- per-document accuracy;
- repeated-run variance;
- confusion pairs (`gold -> selected`);
- catalog size and input-token cost.

Only after metadata selection is highly reliable should an end-to-end result be used to judge progressive disclosure.

A correct final answer after first reading the wrong document is not a top-1 retrieval success.

## Scaling to a much larger corpus

For the current 40-document experiment, loading all activation metadata is deliberately simple and directly mirrors Agent Skills discovery.

A corpus 100x larger may make an all-document catalog too large. Do **not** weaken individual descriptions to solve that problem. Preserve activation-quality metadata and introduce an additional catalog-discovery layer only when measurements show the full metadata map no longer fits the desired context/cost envelope.

Possible future layers include a coarse domain map, search over metadata, or another index, but they should return the same high-quality activation records. The invariant remains:

```text
small routing representation
    -> select relevant resource(s)
    -> disclose detailed body
    -> disclose deeper resources only if required
```

The scale mechanism is a separate experiment from metadata quality.

## Review checklist

Before accepting a metadata description, verify:

- [ ] It says what the document contains.
- [ ] It says when the document should be selected.
- [ ] A question containing a decisive marker/qualifier can route here from metadata alone.
- [ ] It is clearly distinguishable from its closest sibling documents.
- [ ] It uses stable user/domain vocabulary rather than generic answer-field words.
- [ ] It states an important base/exception/override boundary when that boundary affects discovery.
- [ ] It contains no hidden team/code/threshold/duration/queue answer fact.
- [ ] It stays short enough to be useful as always-visible routing context.

## Encode multi-document dependency boundaries

Activation metadata should not only distinguish siblings; it should also tell the selector when a document is one premise in a larger proof.

Useful dependency language includes:

- `use this product document to establish the base tier/class, then combine with quota/retention and the regional authority for the effective result`;
- `when a region and product are both named, include both the product baseline and regional override`;
- `when the question asks which authority governs, combine this exception with the competing/fallback authority needed to establish precedence`;
- `when the same question asks both the window and approval, select the separate window and approval policies`.

This is still routing metadata. It names *which kinds of evidence must be combined* without exposing the hidden team, code, threshold, duration, or final answer.

### Do not confuse repeated values with complete proof

A regional document may repeat a tier name while also setting a lower ceiling. That does not necessarily make the product-assignment and quota policies irrelevant when the question asks for the complete effective-decision chain. Metadata should make the dependency explicit when those premises materially justify the result.

Conversely, do not force a derivation document when the user already supplies the derived fact. If the question says `already classified Lattice-3`, metadata should route directly to consumers of Lattice-3 rather than reopening severity classification merely because it can derive the same level.
