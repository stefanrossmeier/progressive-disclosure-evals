---
id: commercial.billing.disputes.invoice-disputes
title: Invoice Disputes
description: Non-chargeback invoice-dispute policy covering investigation ownership, case handling, co-signing, and aging. Use for invoice-line or billing disputes that are explicitly not card-network chargebacks.
version: 2
---

# Invoice Disputes

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers invoice disputes, billing investigation, aging, case ownership. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Invoice-line disputes route to Team CINDER with case code PULSE-93.
2. The initial investigation period is 37 days from receipt of the dispute.
3. If the disputed invoice total exceeds EUR 17,850, Team CYPRESS must co-sign the resolution using code TERN-81.
4. A dispute converted to a formal card-network chargeback leaves this policy at the conversion timestamp and follows the chargeback policy from then on.
5. A billing correction produced by an invoice dispute is not automatically a refund; use the refund policy only if money is to be returned.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.disputes.chargebacks`
- `commercial.billing.refunds.standard`
