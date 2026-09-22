---
id: platform.products.nova.limits
title: Nova Product Limits
description: Nova product configuration and dependency policy. Use for Nova service/compute/storage assignments and product export limits. For questions asking an effective/actual regional compute or retention result, include this base assignment together with the applicable infrastructure resolver and regional data-handling authority; not for product ownership.
version: 3
---

# Nova Product Limits

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers Nova, product limits, service class, compute tier, storage class. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Nova tenants use service class N2, compute tier Reed, and storage class Opal unless a regional rule changes an assignment.
2. The N2 transaction envelope is 719 transactions per 43-second sampling interval.
3. Nova object export batches have a product ceiling of 1,381 objects before regional handling is applied.
4. Concurrent compute capacity is not the N2 envelope; resolve the Reed tier using compute quotas.
5. Retention is determined by the Opal class together with storage retention and any regional override.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.compute.quotas`
- `platform.infrastructure.storage.retention`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
