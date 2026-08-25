---
id: governance.regions.apac.billing-overrides
title: APAC Billing Overrides
description: APAC regional billing override policy for standard refunds, credits, disputes, and partner payment instruments. Use when APAC-governed billing scope remains active, including an ordinary standard refund. Excluding an unrelated exception does not remove APAC scope; prefer this over the global base policy unless a narrower still-active authority takes precedence.
version: 3
---

# APAC Billing Overrides

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers APAC, billing overrides, refunds, partner contracts, payment instruments. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. APAC-governed standard refunds above EUR 6,480 require Team VIOLET with approval code JADE-66.
2. For APAC Nova refunds above EUR 4,420, the payment instrument is account credit code AC-73 rather than cash.
3. PINE-6 partner authority remains determined by the partner exception policy, but this document still controls the APAC payment instrument after approval.
4. APAC Zephyr outage credits use a cap of EUR 5,840 instead of the general outage-credit cap.
5. Migration-credit MIG-2 authority remains higher than these billing overrides.

## Precedence

- APAC payment-instrument rules apply after partner approval authority is resolved.
- MIG-2 migration credit authority supersedes APAC billing overrides.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.standard`
- `commercial.contracts.partner.exceptions`
- `commercial.billing.credits.outage`
