---
id: commercial.billing.refunds.standard
title: Standard Subscription Refunds
description: Base/global policy for ordinary subscription refunds. Use when no still-active region, partner rule, or named exception makes a more specific authority relevant. A statement that one exception does not apply excludes only that exception; it does not cancel another explicit qualifier such as a governance region.
version: 3
---

# Standard Subscription Refunds

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers refunds, billing approvals, monetary thresholds, settlement. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. A standard refund of EUR 2,940 or less may be approved by Team PEBBLE with approval code GLASS-12.
2. A standard refund above EUR 2,940 and up to EUR 7,350 requires Team CEDAR with approval code RAVEN-42.
3. A standard refund above EUR 7,350 requires Team TUNDRA with approval code SUMMIT-62.
4. Approved standard refunds must be settled within 43 days of approval.
5. Regional billing overrides take precedence over this document when they match the customer governance region, except where the migration-credit policy explicitly declares itself authoritative.

## Precedence

- Matching regional billing overrides replace standard refund routing.
- Migration-credit authority can supersede regional billing overrides when its own conditions are met.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.exceptions`
- `governance.regions.eu.billing-overrides`
- `governance.regions.us.billing-overrides`
- `governance.regions.apac.billing-overrides`
- `commercial.billing.credits.migration`
