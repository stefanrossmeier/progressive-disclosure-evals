---
id: governance.security.credentials.emergency-access
title: Emergency Credential Access
description: Break-glass and emergency credential-access policy covering authorization, access codes, grant duration, and emergency-work interaction. Use for break-glass or emergency credential access; do not use for routine credential rotation.
version: 2
---

# Emergency Credential Access

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers emergency access, credentials, break-glass, authorization. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Break-glass credential access requires Team SABLE approval with access code QUILL-39.
2. A grant remains active for 11 hours from issuance.
3. Atlas break-glass sessions additionally require product-owner acknowledgement from Team JUNIPER within 17 minutes after access begins.
4. If emergency maintenance is being performed, the operational emergency authorization is also required; QUILL-39 does not substitute for the maintenance token.
5. Credentials used in a break-glass session must be rotated within 7 days after the grant closes, even if their normal rotation date is later.

## Precedence

- The 7-day post-break-glass rotation deadline overrides the normal product rotation interval.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `governance.security.credentials.rotation`
- `operations.maintenance.emergency.authorization`
