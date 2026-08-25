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

## Treat explicit entity anchors as first-class routing keys

Cross-domain evaluation exposed a failure mode that is easy to miss in policy-style corpora: a question may identify the relevant evidence with a concrete archaeological/object/archive anchor while the metadata only describes a broad document category. Examples of anchor shapes include object IDs (`SF-241`), contexts (`C-511`), walls/features (`W-91`, `F-41`), samples (`OSL-6`), burials (`B-23`), photographs (`PR-2014-337`), and record IDs (`O-31`).

If an anchor is already present in the user question and its purpose is to identify which document body should be opened, it should normally appear in the activation metadata of the document that owns the relevant fact. This is routing vocabulary, not answer leakage.

A useful rule is:

> When the user can name a stable entity before retrieval, make that entity discoverable in metadata wherever it is an important activation boundary.

Do not add the hidden value the user is asking for. For example, metadata may say that the Trench T11 register should be used for `SF-241` recovery-context questions, but it must not reveal the requested context ID. Metadata may say that a doorway-graffiti catalogue covers `D-44`, but it must not disclose the numeral written there.

Check this against the **whole evaluation set**, not only the current question. An identifier can be safe routing context in one case but be a hidden answer in another. If globally visible metadata would reveal a graded answer anywhere in the benchmark, do not publish that value as an activation anchor. Use another question-known boundary instead—for example a review year, document purpose, feature type, or relation endpoint that is already stated in the triggering question. Corpus validation should continue to reject answer values that leak into the always-visible catalog.

This principle is especially important when several neighboring documents have equally plausible human-readable titles. A generic description such as “worked bone catalogue” is not enough to route a question about the excavation context of `SF-241`; the excavation register must expose `SF-241` as an activation anchor too.

## Do not encode an assumed document taxonomy into routing

The selector must route from metadata, not from stereotypes about where a kind of fact “ought” to live. A fact about an object may live in an excavation notebook, a date may be constrained by stratigraphy plus a laboratory report, and a mapped location may require both a field elevation and a topographic survey.

Metadata should therefore state the *fact ownership boundary*, not just the subject category. Prefer descriptions such as:

```text
Trench T2 deep-sounding notebook. Use when SF-088 is named and the question asks for its field elevation, registration, or excavated setting.
```

over:

```text
Early excavation notebook with small finds.
```

Likewise, specialist metadata should distinguish treatment history from identification, field provenance from catalogue classification, and sample age from geomorphic correlation. This reduces the tendency to choose a document merely because its broad category matches the noun in the question.

## Describe the direction of lookup

A relationship can be discoverable in one direction and still be hard to route in the other. Small models often treat these as different activation problems.

For example, this metadata:

```text
Legacy provenance review. Use when deciding which object belongs to an older excavation season.
```

helps with `season -> object`, but it is weak for a question that gives the object and asks for its season. If the body supports both directions and both are legitimate query shapes, describe both without exposing either hidden endpoint:

```text
Legacy provenance review used to confirm the excavation season or trench attribution of a named older object. Use when given an object and asked which historical season it came from, or for the inverse provenance lookup.
```

The same principle applies to `floor -> context`, `context -> ceramic horizon`, `sample -> terrace`, `photograph -> context`, and other bridge relationships. Metadata should describe the **operation the user is asking the system to perform**, not merely list the two concepts involved.

A useful review question is:

> Given the entity or condition already stated by the user, does this description make the requested lookup direction obvious?

## Expose multi-document bridge endpoints without exposing the answer

Some questions require one document to identify an entity and a second document to supply the requested property. Metadata should make that bridge predictable before bodies are opened.

Examples of safe bridge language include:

- `Use when SF-203 must be mapped to its burial before another specialist property is retrieved.`
- `Combine with geomorphology when the question asks which named terrace an OSL sample belongs to.`
- `Use when a photograph identifier must be mapped to its photographed context before a ceramic lookup.`

This tells the selector that two bodies may be indispensable without revealing the burial ID, terrace name, vessel type, date, or other answer fact.

Do not select extra documents merely for corroboration or background. Every selected body should be expected to contribute either a requested fact or an indispensable bridge/transformation needed to obtain one.


## Separate primary-record ownership from later interpretation

When several documents discuss the same entity across time, metadata should state which stage of the evidentiary chain each document owns. A primary field report and a later synthesis can both mention the same installation, but they should not be interchangeable routing targets.

Prefer boundaries such as:

```text
Primary field record. Use to establish the original excavation interpretation before later specialist reassessment.
```

and:

```text
Later specialist synthesis. Use for the reassessment rationale or later functional interpretation, not for the original field label.
```

Likewise, a context-specific ceramic revision can own `context -> revised horizon`, while a chronology synthesis owns `horizon -> broad absolute range`. If a question requests both, each description should make the two-step bridge predictable without leaking the horizon or date.

This is a fact-ownership boundary, not merely a topical distinction. Repeated selection of a later synthesis for an original-record fact is usually evidence that this boundary is too weak.

## Keep answer grading separate from proof-set validation

A multi-document benchmark needs two different kinds of gold:

1. **Answer expectations** — facts the final user-facing answer must contain.
2. **Required-evidence anchors** — evidence strings used by dataset validation to prove that every required document contributes something unique.

Do not overload `expected_contains` with long intermediate bridge statements solely to make required-document indispensability mechanically checkable. That makes semantically correct concise answers fail because they omit a derivation sentence the question never asked for.

For strict multi-document corpora, use a separate per-document `required_evidence` mapping when available. The evaluator should grade the answer against answer expectations, while dataset validation should use `required_evidence` to verify that each gold document has a unique contribution.

This separation preserves strict proof-set design without forcing the runtime model to restate every intermediate relation in its final answer.

### Grade the minimum semantic answer actually requested

`expected_contains` should encode the smallest stable answer value that makes the user's requested fact correct. Do not require the model to repeat nouns already supplied by the question.

For example, if the question is `How many large plastered bins ...?`, an answer of `Three.` is semantically complete. Grading only `three large plastered bins` would create a false negative even though the model supplied the requested count. The stronger descriptive phrase can remain in `required_evidence` when it is useful for proving that the gold document contains the relevant evidence.

Prefer answer expectations such as a count, identifier, date range, name, code, or other requested value over a sentence-shaped restatement of the question.

For every `How many ...?` case, audit the entire dataset consistently. The evaluator should accept the requested count alone (`Five.`, `17.`, `31.`) without requiring the model to repeat nouns from the question. Keep a richer contextual phrase such as `17 socketed arrowheads` in `expected_contains` when a bare value like `17` would collide with unrelated always-visible metadata (for example another sample or record identifier) and therefore trigger the global leakage validator. In that situation the matcher, not the runtime prompt, should interpret the leading count semantically. Keep the full descriptive phrase in `required_evidence` when it is useful for proving document contribution. Do not fix only the individual count case that happened to fail.

### Every gold document must answer an explicit request or an indispensable bridge

Do not make a document gold merely because it provides useful historical context. For each required document, ask whether removing it makes at least one requested fact or necessary derivation impossible to establish.

If a multi-document case expects the final answer to include a fact such as an *initial interpretation*, the user question must actually ask for that fact or make it necessary to the requested comparison. Otherwise the benchmark silently grades an obligation the user never requested, and the selector has no principled reason to retrieve that document.

When this defect is found, prefer correcting the question/benchmark semantics over adding metadata that artificially forces the hidden gold document into the plan.

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
7. Check the direction of lookup: verify that the description supports the realistic `known entity -> requested property` direction, not only the inverse relation.
8. Check every routing anchor against the whole eval set so a safe query-known value in one case does not leak a hidden answer in another.
9. For documents that discuss the same entity at different interpretive stages, state which document owns the original record, reassessment, or synthesized property.
10. Run `python scripts/validate_corpus.py`.
11. Run the selection-only diagnostic before the end-to-end benchmark.
12. Inspect every repeated selection error as a metadata-design problem first, not as a reason to add orchestration.

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
- [ ] It describes the lookup direction users actually ask for (`known entity -> requested property`) when direction matters.
- [ ] If sibling documents describe different interpretive stages, it states which stage/fact this document owns.
- [ ] Every exposed anchor has been checked against the whole eval set for answer leakage.
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

## Release rule: keep corpus content and evaluator gold physically separate

A distributable corpus must not contain its evaluation questions, required-document labels, expected answers, or other benchmark gold anywhere beneath the corpus directory. Even when the runtime loader happens to ignore those files, colocating them makes leakage audits harder and makes the public artifact look unsafe.

Use a repository layout like:

```text
corpus/
  tell-aster/
    ...document bodies only...

datasets/
  tell-aster-eval-v1.yaml   # historical benchmark
  tell-aster-eval-v2.yaml   # current release benchmark
```

The corpus registry may point from a corpus name to its default external dataset, but the dataset must not be part of the corpus tree.

## Make multi-document gold indispensable to the user question

A unique phrase in each required document is not sufficient to prove that the document is semantically indispensable. V17 exposed several cases where a downstream specialist document repeated enough of the bridge to answer correctly without opening the nominal bridge document.

For release benchmarks, prefer this stronger rule:

> Every required document should contribute an explicitly requested output, or a relationship that cannot already be established from the question or another selected document.

When a bridge document is repeatedly unnecessary, do **not** tune metadata to force retrieval of it. Rewrite the evaluation question so that the bridge contributes a real requested fact, reclassify the case, or remove the redundant document from the gold set.

Examples of stronger question design:

- weak: "What crop was stored in the bin that survives to 1.34 m?" when the botanical report already names the bin;
- stronger: "What maximum height is recorded for Bin Bn-6, and which crop dominated its fill?" — architecture owns the height and botany owns the crop;
- weak: "Which source matches the limestone of IW-5?" when the geology report already states the entire mapping;
- stronger: "Which architectural reference sample does IW-5 match, and which geological source matches that sample?" — each document contributes a requested result.

Keep historical benchmark versions immutable for reproducibility. Put corrected release semantics in a new dataset version rather than silently rewriting the old benchmark.

## Use metadata as the first disclosure layer

Anthropic's Agent Skills guidance describes name/description metadata as the first level of progressive disclosure: enough information to decide *when* to load the deeper body. OpenAI's harness guidance similarly recommends a compact map rather than a large always-visible manual.

For corpus metadata this means:

- describe **fact ownership**, not merely topic;
- include safe entity anchors when the entity is already known in the question;
- state important source-role boundaries such as original record vs later reassessment;
- state predictable combination rules when another source type owns a requested property;
- never place hidden answer values in activation metadata merely to improve routing.

Official references:

- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://openai.com/index/harness-engineering/
