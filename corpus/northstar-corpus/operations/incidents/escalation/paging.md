---
id: operations.incidents.escalation.paging
title: Incident Paging Rules
description: Responder paging policy applied after escalation routing is known. Use for first-page codes, paging sequence, or acknowledgement timers for a product/Lattice incident; combine with escalation routing when the question also asks the owning team or queue, but do not use paging to determine severity.
version: 2
---

# Incident Paging Rules

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers paging, responders, acknowledgement, incident escalation. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Pages for Lattice-3 incidents are sent with paging code VX-17 after the escalation queue is resolved.
2. Team JUNIPER has 11 minutes to acknowledge an Atlas Lattice-3 page; Team QUARTZ has 13 minutes for Zephyr; Team LANTERN has 17 minutes for Nova.
3. If the first acknowledgement timer expires, the second page goes to Team FALCON using code TALON-67.
4. An approved scheduled-maintenance incident suppresses the second page only when the change approval record carries suppression token SM-43.
5. Paging suppression never suppresses customer or executive notification obligations.

## Exceptions

- A valid SM-43 approved-maintenance record suppresses only the second responder page.

## Precedence

- Notification policies remain authoritative even when responder paging is suppressed.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.escalation.routing`
- `operations.incidents.communication.executive-notification`
- `operations.maintenance.scheduled.approvals`
