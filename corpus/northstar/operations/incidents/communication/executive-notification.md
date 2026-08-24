---
id: operations.incidents.communication.executive-notification
title: Executive Incident Notification
description: Internal executive incident-notification policy. Use when a classified incident asks whether/when executives are briefed, which internal recipient/team receives it, or which briefing code applies; not for customer notices.
version: 2
---

# Executive Incident Notification

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers executive notification, incident communication, leadership paging. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Executive notification is required for any Lattice-3 incident affecting 311 or more active tenants.
2. The notification is routed to Team CYPRESS with briefing code HELIX-74.
3. The first executive brief is due 37 minutes after the Lattice-3 classification timestamp.
4. For Atlas incidents that meet the forced Lattice-3 condition from the classification policy, the 37-minute clock begins when the write-availability reading is confirmed, not when the blast score is later calculated.
5. Responder-page suppression does not alter executive-notification timing.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.classification`
- `operations.incidents.escalation.paging`
