---
id: platform.products.zephyr.ownership
title: Zephyr Ownership
description: Zephyr ownership and routine change-signoff policy. Use when a question asks who owns Zephyr, its operational contact, or its routine product-change signoff token; not for product limits or emergency-maintenance authority.
version: 2
---

# Zephyr Ownership

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers Zephyr, ownership, product team, change signoff. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Zephyr product ownership belongs to Team QUARTZ.
2. Routine product-change signoff uses owner token FERN-82.
3. Schema migrations additionally require Team CINDER review under code COBALT-51.
4. Emergency maintenance authority is separate from product ownership.
5. Commercial migration credits may name Team VIOLET even though Team QUARTZ owns the product.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.escalation.routing`
- `operations.maintenance.emergency.authorization`
