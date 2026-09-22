---
id: governance.regions.apac.data-handling
title: APAC Data Handling
description: APAC regional data-handling authority for Atlas, Nova, and Zephyr. Use for APAC-governed storage changes, compute ceilings, export limits, incident queues, or APAC Nova severity interactions. For effective/actual/final questions, combine this authority with the base product/classification and the relevant quota/retention/routing/override policy when those premises determine the result.
version: 3
---

# APAC Data Handling

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers APAC, data handling, regional overrides, product-specific governance. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. APAC-governed Atlas tenants have a concurrent compute ceiling of 283 units while remaining on the Flint tier.
2. APAC-governed Zephyr tenants replace Amber storage with Slate.
3. APAC-governed Nova tenants use export-batch ceiling 1,019 objects and incident queue AURORA-28 for Lattice-3 escalation.
4. The P-17 severity floor does not apply to APAC-governed Nova incidents.
5. APAC customer notifications that include export metrics must carry statement identifier AP-PS-61.

## Exceptions

- APAC Nova ignores the P-17 severity floor.

## Precedence

- APAC Nova routing overrides the Nova default Lattice-3 queue.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.products.atlas.limits`
- `platform.products.zephyr.limits`
- `platform.products.nova.limits`
- `operations.incidents.severity.overrides`
- `operations.incidents.escalation.routing`
