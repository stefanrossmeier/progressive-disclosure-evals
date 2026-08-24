---
id: operations.incidents.severity.overrides
title: Incident Severity Overrides
description: Named incident-severity exception policy. Use for P-17 or another explicit severity override and for how it modifies an ordinary Lattice classification. If the ordinary level is already stated, do not re-open base classification. If the override outcome depends on an explicitly governed region/product combination such as APAC Nova, include the applicable regional data-handling authority to establish that scope.
version: 4
---

# Incident Severity Overrides

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers severity overrides, incident exceptions, maintenance conditions, regional conditions. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. An incident carrying finance marker P-17 is set to Lattice-2 when the ordinary classification would be Lattice-1.
2. If the same P-17 incident affects Nova tenants governed by APAC data handling, keep the ordinary classification; the P-17 floor does not apply.
3. During an approved scheduled maintenance window, a Zephyr queue-stall may be reduced by one Lattice level only when the affected queue is listed on the approved change record.
4. Credential-exposure incidents tagged Quartz-Red are not assigned a Lattice band for escalation purposes; security handling replaces severity routing.
5. A rollback that uses an emergency authorization does not qualify for the scheduled-maintenance severity reduction.

## Exceptions

- APAC-governed Nova incidents ignore the P-17 minimum-severity rule.
- Emergency-authorized rollbacks cannot use the scheduled-maintenance severity reduction.

## Precedence

- Quartz-Red security handling takes precedence over all Lattice routing rules in the severity corpus.
- The emergency-rollback exclusion takes precedence over the scheduled-window reduction.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.classification`
- `operations.maintenance.scheduled.windows`
- `governance.regions.apac.data-handling`
