---
id: commercial.billing.credits.migration
title: Migration Credits
description: Migration-credit policy for qualifying product migrations. Use for migration-credit questions, especially Atlas-to-Zephyr migrations, marker MIG-2, eligibility, caps, approval routing, and precedence over standard refunds or regional billing rules.
version: 2
---

# Migration Credits

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers migration credits, product migration, credit caps, precedence. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. A qualifying Atlas-to-Zephyr migration labeled MIG-2 receives a credit equal to 17.3 percent of the affected monthly platform charge, capped at EUR 4,285.
2. MIG-2 credits require Team VIOLET approval using code SABLE-88.
3. The migration event must complete within 29 days of the migration authorization date.
4. For MIG-2 only, this document is authoritative over regional billing overrides and over standard refund routing.
5. A migration that is reversed back to Atlas within 17 days is not eligible for a MIG-2 credit even if the original migration completed successfully.

## Exceptions

- A reversal to Atlas within 17 days cancels MIG-2 eligibility.

## Precedence

- MIG-2 migration credit rules supersede regional billing overrides and standard refund routing for the credit decision.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `commercial.billing.refunds.standard`
- `governance.regions.eu.billing-overrides`
- `platform.products.atlas.ownership`
- `platform.products.zephyr.ownership`
