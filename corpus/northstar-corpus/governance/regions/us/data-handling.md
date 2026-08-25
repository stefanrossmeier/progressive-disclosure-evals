---
id: governance.regions.us.data-handling
title: US Data Handling
description: US regional data-handling authority for Atlas, Nova, and Zephyr. Use for US-governed storage/retention, compute ceilings, export object ceilings, or other product-data constraints. For effective/actual/remains/follows-from questions, combine this regional authority with the product/base assignment and the relevant quota/retention/security resolver rather than treating the regional value alone as the complete proof.
version: 3
---

# US Data Handling

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers US, data handling, regional overrides, product-specific governance. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. US-governed Atlas tenants keep Slate storage but have an explicit retention duration of 61 days instead of the Slate base duration.
2. US-governed Zephyr tenants use an export-batch ceiling of 2,219 objects instead of the Zephyr product ceiling.
3. US-governed Nova tenants have a concurrent compute ceiling of 113 units while remaining on the Reed tier.
4. US incident customer notices use regional statement identifier US-PS-43 only when a notice contains tenant-level capacity data.
5. The numeric compute ceiling is applied as a ceiling, not as a tier replacement.

## Precedence

- The explicit US Atlas retention duration overrides Slate base retention.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.products.atlas.limits`
- `platform.products.zephyr.limits`
- `platform.products.nova.limits`
- `platform.infrastructure.storage.retention`
- `platform.infrastructure.compute.quotas`
