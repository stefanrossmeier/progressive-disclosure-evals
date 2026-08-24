---
id: operations.maintenance.emergency.rollback
title: Emergency Rollback
description: Emergency rollback policy covering product rollback markers, start timing, and checkpoints after a rollback decision. Use for rollback-specific questions during emergency maintenance; combine emergency authorization only when its token/authority is also requested.
version: 2
---

# Emergency Rollback

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers rollback, emergency maintenance, recovery checkpoints. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. An emergency rollback must be initiated within 23 minutes after the rollback decision is recorded.
2. Atlas rollback checkpoints use marker LYNX-14; Zephyr uses marker GARNET-52; Nova uses marker NIMBUS-34.
3. If rollback has not restored the pre-change health marker within 41 minutes, open a new incident and classify it without using scheduled-maintenance reductions.
4. A rollback authorization remains valid only while its parent emergency authorization is unexpired.
5. Rollback records are retained for 73 days in the operations archive.

## Exceptions

- A failed emergency rollback cannot claim scheduled-maintenance severity reduction.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.maintenance.emergency.authorization`
- `operations.incidents.severity.overrides`
