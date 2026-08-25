---
id: operations.maintenance.scheduled.windows
title: Scheduled Maintenance Windows
description: Standard scheduled-maintenance window policy by product, including weekday, start/end times, and overrun interpretation. Use for authorized-window facts. When the same question also asks approval by change duration, include scheduled maintenance approvals as a separate evidence obligation.
version: 3
---

# Scheduled Maintenance Windows

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers maintenance windows, scheduled maintenance, product windows, overruns. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Atlas standard maintenance begins Wednesday at 02:17 UTC and ends at 03:41 UTC.
2. Zephyr standard maintenance begins Thursday at 04:23 UTC and ends at 05:36 UTC.
3. Nova standard maintenance begins Tuesday at 01:11 UTC and ends at 02:08 UTC.
4. A maintenance action may start up to 7 minutes before its listed window only when the approval record contains early-start marker ES-7; the official window start does not move.
5. Any work continuing beyond the listed end is an overrun even if it began under ES-7.

## Exceptions

- ES-7 permits an early start but does not extend the official maintenance window.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.maintenance.scheduled.approvals`
- `operations.incidents.communication.customer-notification`
