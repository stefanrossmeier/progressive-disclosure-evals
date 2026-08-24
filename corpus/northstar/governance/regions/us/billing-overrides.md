---
id: governance.regions.us.billing-overrides
title: US Billing Overrides
description: US regional billing authority for standard refunds, disputes, and outage credits. Use when US billing scope remains active, including fallback after an excluded/inapplicable D-8 exception. For a US D-8 question asking which rule governs, combine this document with the D-8 exception policy to establish whether the exception wins or the US fallback reactivates.
version: 4
---

# US Billing Overrides

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers US, billing overrides, refunds, disputes, outage credits. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. US-governed standard refunds above EUR 8,940 require Team FALCON with approval code RIDGE-91 instead of the standard high-band route.
2. For Atlas outage credits in the US, the general cap is increased to EUR 7,125.
3. Resolved chargebacks for US-governed customers must reimburse to invoice balance code IB-29 rather than to the original payment instrument.
4. The US refund override does not apply to D-8 duplicate-billing cases that remain within the D-8 exception limits.
5. If a D-8 case exceeds its exception limit and returns to standard handling, the US override becomes applicable again.

## Exceptions

- Valid in-limit D-8 duplicate-billing refunds bypass the US standard-refund override.

## Precedence

- D-8 controls within its valid scope; otherwise the US regional override supersedes standard refund routing.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.standard`
- `commercial.billing.disputes.chargebacks`
- `commercial.billing.credits.outage`
