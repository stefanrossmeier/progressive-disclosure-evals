You are generating a synthetic internal enterprise knowledge base for an evaluation of progressive knowledge disclosure in AI agents.

The knowledge base belongs to a completely fictional company named **Northstar Systems**. None of its products, organizational units, codes, processes, thresholds, identifiers, rules, or policies correspond to real companies.

The objective is NOT to produce realistic general business advice. The objective is to produce a controlled knowledge corpus containing specific facts that a language model cannot reasonably infer without reading the appropriate documents.

## Purpose

The corpus will be used to evaluate whether an AI agent:

1. discovers the documents required to answer a question;
2. avoids reading unnecessary documents;
3. combines information from multiple documents when necessary;
4. respects exception and precedence rules;
5. changes its answer when arbitrary corpus facts are changed;
6. refuses to invent an answer when required knowledge is absent.

Therefore, favor arbitrary but internally consistent facts over obvious or conventional rules.

For example, prefer:

* approval team: `CEDAR`
* authorization code: `RAVEN-42`
* threshold: `€7,350`
* escalation queue: `ORBIT-9`
* retention period: `43 days`
* product owner: `Team JUNIPER`

instead of predictable answers such as:

* contact management
* contact security
* use the normal escalation process
* retain data for 30 days

## Required hierarchy

Generate content for the following hierarchy:

corpus/northstar/

operations/
incidents/
severity/
classification.md
overrides.md
escalation/
routing.md
paging.md
communication/
customer-notification.md
executive-notification.md
maintenance/
scheduled/
windows.md
approvals.md
emergency/
authorization.md
rollback.md

commercial/
billing/
refunds/
standard.md
exceptions.md
credits/
migration.md
outage.md
disputes/
chargebacks.md
invoice-disputes.md
contracts/
enterprise/
approvals.md
renewals.md
partner/
approvals.md
exceptions.md

platform/
products/
atlas/
limits.md
ownership.md
zephyr/
limits.md
ownership.md
nova/
limits.md
ownership.md
infrastructure/
storage/
classes.md
retention.md
compute/
tiers.md
quotas.md

governance/
regions/
eu/
data-handling.md
billing-overrides.md
us/
data-handling.md
billing-overrides.md
apac/
data-handling.md
billing-overrides.md
security/
credentials/
rotation.md
emergency-access.md
exports/
approval.md
retention.md

## Document format

Every document must begin with YAML front matter:

---

id: <stable dot-separated identifier>
title: <human-readable title>
description: <short description useful for deciding whether this document should be opened>
version: 1
----------

The `description` is activation/routing metadata, not merely a human summary. It MUST communicate both:

* **WHAT** kind of knowledge or decision the document contains; and
* **WHEN** the document should be selected, including discriminating triggers, qualifiers, or boundaries against confusing neighboring documents.

Routing vocabulary that the user can supply before retrieval MAY appear in metadata when it is needed to choose the correct authority (for example a named exception marker such as `D-8`). This is not answer leakage if the marker only identifies which policy to open.

The description MUST NOT reveal concrete facts that answer the downstream question, such as hidden approval teams/codes, answer thresholds, answer durations, result queues/classes, or other values that should require opening the body.

Good description:

"Named refund-exception policy. Use when a refund mentions D-8, verified duplicate billing, exception eligibility, age or amount limits, partner-sold restrictions, or fallback after an exception; prefer this over the standard refund policy when a matching exception trigger is present."

Good sibling distinction:

"Base policy for ordinary subscription refunds, including amount bands, approvals, and settlement timing. Use for standard refunds only when no named exception, partner rule, or regional billing override governs the case."

Bad description:

"Refunds above €7,350 require CEDAR approval with code RAVEN-42."

Each document should contain approximately 250–500 words.

## Knowledge design requirements

Create a globally consistent internal rule set.

Include at least:

* 15 arbitrary alphanumeric codes;
* 10 arbitrary team names;
* 12 non-round numerical thresholds;
* 8 unusual durations such as 17, 43 or 73 days;
* 10 explicit exception rules;
* 8 precedence or override relationships;
* 10 cross-document references;
* 6 rules requiring both product-specific and region-specific knowledge;
* 6 rules requiring both a general policy and an exception document.

Use distinctive fictional identifiers such as:

RAVEN-42
ORBIT-9
MICA-73
VX-17
KITE-204
EMBER-61

Generate additional identifiers rather than repeatedly using these examples.

## Important constraints

The factual answers must not be derivable from common sense.

For example, do NOT write:

"Critical security incidents require immediate escalation."

Instead write something such as:

"For Atlas incidents classified as Lattice-3, route escalation to Team JUNIPER through queue ORBIT-9. If the affected tenant is governed by the EU data-handling policy, the regional override changes the queue to KESTREL-4."

The semantics may resemble ordinary enterprise processes, but the concrete decision must depend on arbitrary corpus-specific facts.

## Cross-document reasoning

Design documents so later evaluation questions can require:

### Single-document lookup

One document contains everything necessary.

### Two-document composition

The answer requires combining facts from two documents.

Example structure:

* product document determines service class;
* quota document determines the limit for that class.

### Three-document composition

The answer requires combining three independent facts.

Example structure:

* product determines service tier;
* region defines an override;
* approval policy determines the resulting approval code.

### Exception handling

A general document establishes a rule and another document overrides it for a particular condition.

### Precedence

Explicitly state which rule takes precedence.

For example:

"Regional billing overrides take precedence over standard refund rules, except where the migration-credit policy explicitly declares itself authoritative."

Create several different precedence structures. Do not make all exceptions work identically.

## Distractors

Create semantically similar documents deliberately.

For example:

* standard refunds
* refund exceptions
* migration credits
* outage credits
* chargebacks
* invoice disputes

They should share terminology while containing different rules.

This allows evaluation of whether the agent selects the correct document rather than opening everything with similar keywords.

## Cross references

Documents may explicitly reference other documents using their stable ID.

Example:

"For regional overrides, see `governance.regions.eu.billing-overrides`."

Not every required relationship should have an explicit link. Some evaluation cases should require the agent to infer from the situation that another policy category is relevant.

## Consistency

Before producing the result, internally verify:

* every identifier has one intended meaning;
* no two documents accidentally assign incompatible meanings to the same code;
* exception rules identify the rule they override;
* precedence rules are unambiguous;
* cross references point to documents that exist;
* every metadata description states both WHAT and WHEN/activation conditions;
* close sibling documents are mutually discriminative from metadata alone;
* routing markers needed for activation are present when appropriate;
* no metadata description leaks concrete answer values;
* arbitrary facts are distributed across the hierarchy.

## Output format

Return each file separately using exactly this format:

FILE: corpus/northstar/<path>

```markdown
<complete file contents>
```

Do not omit any requested file.

Do **not** generate a global manifest, fact registry, search index, or `_index.yaml` file.
The runtime derives the progressive-disclosure catalog directly from each document's YAML front matter (`id`, `title`, `description`, `version`). The document body remains hidden until explicitly selected.

Cross-document references belong in the relevant document body using stable document IDs. They become visible only after that document is read.

Do not generate evaluation questions yet.
