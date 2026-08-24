---
id: platform.infrastructure.storage.classes
title: Storage Classes
description: Storage-class definition and capacity policy for named classes such as Opal, Slate, and Amber. Use when a question asks a storage class's logical object/capacity ceiling per tenant shard; use storage retention for retention durations.
version: 2
---

# Storage Classes

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers storage classes, capacity, infrastructure, class mapping. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Amber storage has a logical object ceiling of 4,921 GiB per tenant shard.
2. Slate storage has a logical object ceiling of 2,147 GiB per tenant shard.
3. Opal storage has a logical object ceiling of 863 GiB per tenant shard.
4. Capacity ceilings do not determine retention duration; retention is defined separately.
5. Product documents assign default classes, while regional data-handling documents may override the assigned class for a governed tenant.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.storage.retention`
- `platform.products.atlas.limits`
- `platform.products.zephyr.limits`
- `platform.products.nova.limits`
