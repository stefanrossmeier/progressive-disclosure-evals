---
id: operations.maintenance.scheduled.approvals
title: Scheduled Maintenance Approvals
description: Scheduled non-emergency maintenance approval policy based on duration, product, and change characteristics. Use for approval team/record code. When the same question also asks the product standard window, include scheduled maintenance windows as a separate evidence obligation.
version: 3
---

# Scheduled Maintenance Approvals

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers maintenance approvals, change authorization, duration thresholds. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Scheduled changes lasting 47 minutes or less require Team PEBBLE approval with record code CLOVE-32.
2. Scheduled changes lasting more than 47 minutes and no more than 83 minutes require Team CEDAR approval with record code HARBOR-47.
3. Changes longer than 83 minutes require Team SABLE approval with record code PINION-55.
4. EU-governed Atlas storage changes additionally require the regional handling confirmation described by the EU data-handling policy, regardless of duration.
5. Emergency work does not use these approval bands; apply the emergency authorization policy instead.

## Exceptions

- Emergency work is outside the scheduled-maintenance approval bands.

## Precedence

- Emergency authorization replaces scheduled approval when emergency criteria are satisfied.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.maintenance.scheduled.windows`
- `governance.regions.eu.data-handling`
- `operations.maintenance.emergency.authorization`
