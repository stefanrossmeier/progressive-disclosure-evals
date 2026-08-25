---
id: operations.incidents.communication.customer-notification
title: Customer Incident Notification
description: Customer-facing incident notification policy. Use when a question asks first customer-notice timing, customer channel/code, or notification exceptions for a classified incident; do not use for internal executive briefings.
version: 2
---

# Customer Incident Notification

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers customer notification, incident communication, timing, status notices. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. For Lattice-3 incidents, the first customer notice must be issued within 29 minutes of classification.
2. For Lattice-2 incidents, a notice is required only after 53 continuous minutes at Lattice-2.
3. Atlas customers receive notice channel code CIRRUS-29; Zephyr uses VELA-44; Nova uses OAK-63.
4. EU-governed tenants require the regional processing statement from the EU data-handling policy to be attached to the first notice.
5. A scheduled maintenance event that remains wholly inside its approved window does not trigger the Lattice-2 53-minute notice rule, but any overrun is measured from the approved window end rather than the event start.

## Exceptions

- In-window scheduled maintenance is exempt from the ordinary Lattice-2 persistence notice rule.

## Precedence

- For maintenance overruns, the approved window end replaces incident start as the notification timer origin.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.classification`
- `governance.regions.eu.data-handling`
- `operations.maintenance.scheduled.windows`
