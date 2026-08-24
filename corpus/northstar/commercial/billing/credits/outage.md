---
id: commercial.billing.credits.outage
title: Outage Credits
description: Service-outage credit policy. Use when an outage or service-credit question already involves a Lattice incident class and asks about credit eligibility, approval, codes, caps, or regional adjustments; do not use for migration credits.
version: 2
---

# Outage Credits

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers outage credits, incident severity, service credits, caps. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. A Lattice-3 outage qualifies for a service credit of 12.7 percent of the affected monthly service charge, capped at EUR 6,650.
2. Approval is owned by Team QUARTZ using code FORGE-35.
3. A Lattice-2 outage qualifies only if it persists for at least 137 continuous minutes and then receives a 6.3 percent credit capped at EUR 2,175.
4. Planned maintenance wholly within an approved window is not an outage-credit event.
5. Regional billing overrides may modify the cap or payment instrument, but they do not change the required Lattice classification.

## Exceptions

- Approved in-window planned maintenance is excluded from outage-credit eligibility.

## Precedence

- Incident classification determines eligibility before any regional billing adjustment is applied.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.classification`
- `governance.regions.eu.billing-overrides`
- `operations.maintenance.scheduled.windows`
