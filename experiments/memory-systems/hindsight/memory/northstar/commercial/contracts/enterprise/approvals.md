---
id: commercial.contracts.enterprise.approvals
title: Enterprise Contract Approvals
description: Enterprise contract approval bands for discounts, concessions, and non-standard terms. Use when an enterprise contract question asks who/code approves a discount or concession and no more specific renewal or regional rule supplies the decision.
version: 2
---

# Enterprise Contract Approvals

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers enterprise contracts, discount approval, contract concessions. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. An enterprise discount up to 13.4 percent requires Team CEDAR approval with code BRONZE-27.
2. A discount above 13.4 percent and up to 21.8 percent requires Team CYPRESS with code MARBLE-24.
3. A discount above 21.8 percent requires Team TUNDRA with code ELM-79.
4. Any concession that changes data-retention terms requires the applicable regional data-handling policy in addition to commercial approval.
5. Renewal-specific timing rules do not change these approval percentages unless the renewals policy names an exception.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.contracts.enterprise.renewals`
- `governance.regions.eu.billing-overrides`
