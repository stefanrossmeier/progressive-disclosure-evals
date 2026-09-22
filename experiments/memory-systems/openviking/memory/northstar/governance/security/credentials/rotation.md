---
id: governance.security.credentials.rotation
title: Credential Rotation
description: Routine service-credential rotation policy with product-specific intervals and rotation markers. Use for questions about how often Atlas, Nova, or Zephyr credentials rotate or which schedule marker identifies the rotation; not for break-glass access.
version: 2
---

# Credential Rotation

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers credentials, rotation, security, product credentials. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Atlas service credentials rotate every 53 days under rotation marker CRED-A53.
2. Zephyr service credentials rotate every 43 days under rotation marker CRED-Z43.
3. Nova service credentials rotate every 61 days under rotation marker CRED-N61.
4. A credential replaced through emergency access resets its normal rotation clock from the replacement timestamp.
5. Ownership teams may schedule rotations, but emergency-access approval is governed separately.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `governance.security.credentials.emergency-access`
- `platform.products.atlas.ownership`
- `platform.products.zephyr.ownership`
- `platform.products.nova.ownership`
