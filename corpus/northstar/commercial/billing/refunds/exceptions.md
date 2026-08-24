---
id: commercial.billing.refunds.exceptions
title: Refund Exceptions
description: Named refund-exception policy for D-8, verified duplicate billing, eligibility, limits, partner exclusions, and fallback. Use when D-8 or duplicate-billing exception scope is active; prefer this over standard refunds. If a region is explicitly named and the question asks which authority governs or what happens after fallback, include the applicable regional billing override as the competing/fallback authority needed to establish precedence.
version: 3
---

# Refund Exceptions

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers refund exceptions, duplicate billing, partner refunds, special markers. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. A refund marked D-8 for verified duplicate billing may be approved up to EUR 11,625 by Team PEBBLE using code GLASS-12.
2. The D-8 rule overrides the monetary approval bands in the standard refund policy, but it does not override a matching regional prohibition on refund method.
3. Refunds originating from partner-sold contracts do not use D-8 routing even if the duplicate charge is verified; partner exception rules determine authority.
4. A refund requested more than 61 days after the duplicate charge is ineligible for D-8 and returns to standard refund handling.
5. A D-8 refund above EUR 11,625 is not partially delegated; the full amount returns to standard or applicable regional handling.

## Exceptions

- Verified D-8 duplicate billing overrides standard refund monetary bands within its amount and age limits.
- Partner-sold contracts are excluded from the D-8 route.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.standard`
- `commercial.contracts.partner.exceptions`
