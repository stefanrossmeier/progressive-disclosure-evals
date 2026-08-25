---
id: operations.maintenance.emergency.authorization
title: Emergency Maintenance Authorization
description: Emergency-maintenance authorization policy by product. Use when emergency maintenance asks which authority/team or maintenance token is required; do not use for rollback timing or ordinary scheduled changes.
version: 2
---

# Emergency Maintenance Authorization

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers emergency maintenance, authorization, approvers, tokens. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Atlas emergency maintenance requires Team SABLE authorization and token COMET-48.
2. Zephyr emergency maintenance requires Team VIOLET authorization and token BRIM-31.
3. Nova emergency maintenance requires Team FALCON authorization and token ECHO-71.
4. Authorization expires 19 hours after issuance and cannot be renewed; a fresh authorization must be created.
5. If emergency work also requires credential break-glass access, both this authorization and the security emergency-access grant are required. Neither substitutes for the other.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.maintenance.emergency.rollback`
- `governance.security.credentials.emergency-access`
