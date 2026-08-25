---
id: platform.infrastructure.compute.tiers
title: Compute Tiers
description: Compute-tier definition policy for named tiers, including scheduler characteristics and tier markers. Use when a question asks what a tier means or which scheduler marker identifies it; use compute quotas for concurrent compute-unit ceilings.
version: 2
---

# Compute Tiers

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers compute tiers, infrastructure, scheduling, tier mapping. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Reed is the light compute tier and uses scheduler marker REED-17.
2. Flint is the middle compute tier and uses scheduler marker FLINT-43.
3. Crown is the high compute tier and uses scheduler marker CROWN-73.
4. Tier names do not themselves encode quota values; quota numbers are maintained in the compute quota policy.
5. Product documents identify the default tier used by each product, and regional data handling may place a lower temporary ceiling without renaming the tier.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.compute.quotas`
- `platform.products.atlas.limits`
- `platform.products.zephyr.limits`
- `platform.products.nova.limits`
