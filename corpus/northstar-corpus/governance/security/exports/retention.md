---
id: governance.security.exports.retention
title: Export Retention
description: Staged export-package retention policy. Use for EX-TEMP or other staged-export retention, early deletion, retention duration, and regional retention overrides. An explicitly non-EU/not-EU export remains on this retention route rather than activating EU data handling; combine a regional data-handling policy only when that region still positively governs the export. Use export approval separately for package-size approval bands.
version: 3
---

# Export Retention

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers exports, retention, staging, regional overrides. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Staged export packages are retained for 61 days by default.
2. Packages marked EX-TEMP are retained for 19 days unless a regional policy declares an explicit shorter or longer duration.
3. EU staging retention is explicitly 17 days and overrides both the 61-day default and the 19-day EX-TEMP duration.
4. Deleting a package early requires Team FALCON approval using deletion code FROST-58.
5. Approval records for deletion are retained for 73 days after package deletion.

## Exceptions

- EU staging retention overrides EX-TEMP as well as the default.

## Precedence

- An explicit regional export-retention duration is authoritative over marker-based and default durations.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `governance.security.exports.approval`
- `governance.regions.eu.data-handling`
- `governance.regions.us.data-handling`
- `governance.regions.apac.data-handling`
