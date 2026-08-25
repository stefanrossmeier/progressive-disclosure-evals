---
id: commercial.billing.disputes.chargebacks
title: Chargeback Handling
description: Card-network chargeback policy covering ownership, evidence packages, amount bands, and response deadlines. Use for card-network chargebacks; do not use for ordinary invoice-line disputes or subscription refunds.
version: 2
---

# Chargeback Handling

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers chargebacks, billing disputes, evidence, response deadlines. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Chargebacks of EUR 8,475 or less route to Team MARIGOLD using case code CREST-46.
2. Chargebacks above EUR 8,475 route to Team TUNDRA using case code IVORY-84.
3. The evidence package must be assembled within 17 days of the chargeback intake timestamp.
4. A dispute that is only an invoice-line disagreement is not a chargeback, even when a card payment funded the invoice; use the invoice-dispute policy.
5. US billing overrides may replace the reimbursement method after a chargeback is resolved but do not change chargeback evidence ownership.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.disputes.invoice-disputes`
- `governance.regions.us.billing-overrides`
