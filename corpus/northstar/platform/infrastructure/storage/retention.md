---
id: platform.infrastructure.storage.retention
title: Storage Retention
description: Base storage-retention resolver by named storage class with regional override interaction. Use for a class retention duration or an effective retention result. When a product and region determine the class, combine the product limits baseline, regional data handling, and this retention policy; use storage classes for object/capacity ceilings.
version: 3
---

# Storage Retention

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers storage retention, storage classes, data lifecycle, regional overrides. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Amber class base retention is 43 days.
2. Slate class base retention is 73 days.
3. Opal class base retention is 29 days.
4. A regional data-handling policy may replace either the class assignment or the resulting duration. When a region replaces the class, calculate retention from the replacement class unless the regional policy also states an explicit duration.
5. Explicit regional duration overrides take precedence over class-derived retention.

## Precedence

- An explicit regional retention duration overrides both the product default class and the class-derived base retention.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.storage.classes`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
