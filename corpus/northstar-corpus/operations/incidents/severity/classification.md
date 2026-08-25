---
id: operations.incidents.severity.classification
title: Incident Severity Classification
description: Base incident severity-classification policy mapping raw blast scores and control-plane/operational signals to Lattice levels. Use when the ordinary/Lattice classification must actually be derived from raw signals. Do not select it merely to re-derive a level already stated; when a named override or regional exception must then be applied, combine the resulting classification with those authorities.
version: 4
---

# Incident Severity Classification

This document is part of the fictional Northstar Systems knowledge base. Values in it are controlled evaluation facts, not general business guidance. Apply only the rules whose stated scope matches the case; do not substitute customary practice for a missing Northstar rule.

## Scope

This policy covers incident severity, Lattice bands, blast score, product conditions. A rule is applicable only when the case facts satisfy its stated condition. Identifiers, queue names, codes, thresholds, and durations are literal Northstar values. Similar-looking values in neighboring documents are distractors unless a rule or cross-reference makes them relevant.

## Rules

1. Compute the Northstar blast score before assigning a Lattice band. Scores from 0 through 27 are Lattice-1; 28 through 63 are Lattice-2; 64 or higher are Lattice-3.
2. A confirmed Atlas control-plane write-availability reading below 91.7 percent is classified as Lattice-3 even when the blast score is lower.
3. A Zephyr queue-stall lasting at least 17 minutes adds 19 points to the blast score before the band is chosen.
4. Nova cache-only degradation never adds blast-score points unless at least 137 tenants are simultaneously affected.
5. Primary severity ownership is Team MARIGOLD for Lattice-1, Team CINDER for Lattice-2, and Team JUNIPER for Lattice-3.

## Exceptions

- Atlas control-plane write availability below 91.7 percent forces Lattice-3 regardless of the computed blast score.

## Precedence

- The forced Atlas condition is evaluated before the normal score bands.

## Interpretation

Apply the narrowest matching rule before falling back to a general rule. When a referenced policy supplies a region, product class, approval authority, or exception condition, combine that fact with this document rather than guessing a default. A code used here is not interchangeable with another code merely because both appear in approval or escalation contexts. Monetary bands are inclusive only where the rule explicitly says so, and timers begin from the event timestamp named in the rule.

If a required region, product, marker, class, or authorization fact is unavailable, the correct behavior is to identify the missing fact rather than invent one. Where this document says another policy takes precedence, follow that relationship even if the result differs from ordinary operational expectations.

## Related documents

- `operations.incidents.severity.overrides`
- `platform.products.atlas.limits`
