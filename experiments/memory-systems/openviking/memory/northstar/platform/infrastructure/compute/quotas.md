---
id: platform.infrastructure.compute.quotas
title: Compute Quotas
description: Concurrent compute-capacity resolver for named compute tiers and regional ceilings. Use for actual/effective concurrent capacity. When a product and region are both named, combine the product limits document that establishes the tier with this quota policy and the regional data-handling document that supplies any ceiling; use compute tiers only for scheduler/tier markers.
version: 3
---

# Compute Quotas

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers compute quotas, concurrency, tiers, regional ceilings. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Reed permits 137 concurrent compute units per tenant.
2. Flint permits 311 concurrent compute units per tenant.
3. Crown permits 719 concurrent compute units per tenant.
4. If a regional policy states a numeric ceiling for a product, use the lower of the tier quota and the regional ceiling unless that regional policy explicitly declares replacement rather than a ceiling.
5. Product request or transaction envelopes are separate metrics and must not be substituted for concurrent compute quota.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.compute.tiers`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
