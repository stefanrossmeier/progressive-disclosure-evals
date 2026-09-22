---
id: operations.incidents.escalation.routing
title: Incident Escalation Routing
description: Incident escalation-routing resolver mapping a known product/Lattice condition to owning teams and queues. Use when the question asks team/queue routing; make this primary when Lattice is already stated, and add severity classification only when raw signals must derive it. If a regional queue is in scope, include the applicable regional data-handling authority to establish that governance scope. Use paging separately for first-page codes/timers.
version: 4
---

# Incident Escalation Routing

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers escalation, routing, queues, product routing. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. For Lattice-3 Atlas incidents, route to Team JUNIPER through queue ORBIT-9.
2. For Lattice-3 Zephyr incidents, route to Team QUARTZ through queue MICA-73.
3. For Lattice-3 Nova incidents, route to Team LANTERN through queue KITE-204.
4. For Lattice-2 incidents of any product, route to Team CINDER through queue EMBER-61 unless a regional rule explicitly replaces the queue.
5. EU-governed Atlas incidents use queue KESTREL-4 instead of ORBIT-9. APAC-governed Nova incidents use queue AURORA-28 instead of KITE-204.
6. Do not infer a regional override from tenant language or currency; governance assignment must be established by the applicable regional data-handling policy.

## Exceptions

- EU-governed Atlas and APAC-governed Nova replace the product-default Lattice-3 queues.

## Precedence

- A matching regional queue override replaces the product-default queue but does not replace the owning product team.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.classification`
- `governance.regions.eu.data-handling`
- `governance.regions.apac.data-handling`
