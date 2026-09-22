---
id: platform.products.zephyr.limits
title: Zephyr Product Limits
description: Zephyr product configuration and dependency policy. Use for Zephyr service/compute/storage assignments and product export/object limits. For effective regional compute, retention, or export-constraint questions, include this product baseline together with the relevant infrastructure/security resolver and regional data-handling authority; not for product ownership.
version: 3
---

# Zephyr Product Limits

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers Zephyr, product limits, service class, compute tier, storage class. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Zephyr tenants use service class Z5, compute tier Crown, and storage class Amber unless regional data handling states otherwise.
2. The Z5 message-ingest envelope is 2,147 messages per 73-second sampling interval.
3. Zephyr object export batches have a product ceiling of 2,931 objects before regional rules are applied.
4. The Crown tier name must be resolved through the compute quota policy to obtain concurrent compute capacity.
5. Retention is derived from the Amber storage class and may be replaced by a region-specific retention assignment.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `platform.infrastructure.compute.quotas`
- `platform.infrastructure.storage.retention`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
