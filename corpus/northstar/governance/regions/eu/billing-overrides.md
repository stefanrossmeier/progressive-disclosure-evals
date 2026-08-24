---
id: governance.regions.eu.billing-overrides
title: EU Billing Overrides
description: EU regional billing override policy for standard refunds and service or migration credits. Use when EU-governed billing scope remains active, including an ordinary standard refund. Excluding an unrelated exception does not remove EU scope; prefer this over the global base policy unless a narrower still-active authority takes precedence.
version: 3
---

# EU Billing Overrides

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers EU, billing overrides, refunds, credits, product-specific billing. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. For EU-governed Atlas standard refunds above EUR 5,860, approval moves to Team CYPRESS with code LUCENT-76.
2. For EU-governed Zephyr standard refunds, the standard monetary bands remain in place but settlement must occur within 29 days.
3. For EU-governed Nova standard refunds, amounts above EUR 3,775 must be returned as service credit rather than cash unless a higher-authority policy states otherwise.
4. EU outage-credit caps are reduced to EUR 5,275 for Atlas and EUR 4,915 for Nova; Zephyr keeps the general outage cap.
5. MIG-2 migration credits are explicitly outside these overrides and follow the migration-credit policy.

## Exceptions

- MIG-2 credits ignore EU billing overrides because migration credits declare higher authority.

## Precedence

- This document overrides standard refunds and ordinary outage-credit caps for matching EU cases, but not MIG-2.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.standard`
- `commercial.billing.credits.migration`
- `commercial.billing.credits.outage`
