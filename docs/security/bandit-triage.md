# LumenAI Bandit Triage

## Purpose

This document tracks Bandit static security findings and remediation decisions.

## Current Policy

- High severity findings must be fixed before production use.
- Medium severity findings must be fixed or documented with rationale.
- Low severity findings may be documented and reviewed during scheduled security hardening.
- `# nosec` comments are allowed only when:
  - the finding is a false positive,
  - the code path is constrained by allowlisted server-side values,
  - a clear explanation is included on the same line.

## Current Baseline

Initial baseline:

- High: 0
- Medium: 8
- Low: 21

## Triage Log

| ID | Bandit Rule | File | Severity | Decision | Rationale | Status |
|---|---|---|---|---|---|---|
| BANDIT-001 | B608 | app/tenant_remediations.py | Medium | Documented exception | Dynamic SQL SET clause is built from server-side allowlisted columns, not raw user input. Parameters remain bound. | Mitigated |

## Next Actions

1. Re-run Bandit after each remediation.
2. Add additional rows for each remaining Medium finding.
3. Make Bandit blocking after Medium findings are fixed or documented.
