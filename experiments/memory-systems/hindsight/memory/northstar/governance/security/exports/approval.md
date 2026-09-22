---
id: governance.security.exports.approval
title: Export Approval
description: Governed export package-size approval policy. Use for approval team/code by GiB. When a product and region are named and the question also asks an object-count constraint, include BOTH the product limits document (product ceiling/baseline) and the regional data-handling document (regional ceiling/override) so the effective constraint chain is established.
version: 3
---

# Export Approval

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers exports, approval, package size, security review. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Export packages of 214 GiB or less require Team PEBBLE approval with code SHORE-33.
2. Packages above 214 GiB and up to 863 GiB require Team CYPRESS with code DUNE-64.
3. Packages above 863 GiB require Team SABLE with code PRISM-86.
4. Product object-count ceilings and regional object-count ceilings are separate from package-size approval bands; both must be satisfied.
5. If a region sets a lower product export object ceiling, the lower regional ceiling takes precedence for object count, while this document still determines approver by GiB.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `governance.security.exports.retention`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
