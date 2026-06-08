# LumenAI Security Risk Register

## Purpose

This register tracks security baseline findings from Bandit, pip-audit, npm audit, Gitleaks, and architecture review.

The goal is to convert security scan output into documented, triaged, and remediated enterprise engineering work.

## Risk Severity Definitions

| Severity | Meaning | Required Action |
|---|---|---|
| Critical | Exploitable issue that could expose data, secrets, auth, tenant isolation, or production systems | Fix immediately before production use |
| High | Significant security or dependency risk with practical exploit potential | Fix before making scan blocking |
| Medium | Security concern requiring review, mitigation, or documented acceptance | Fix or document exception |
| Low | Low-risk finding or false positive | Document and monitor |

## Current Scan Status

| Area | Tool | CI Mode | Status |
|---|---|---:|---|
| Python lint | Ruff | Blocking | Passing |
| Backend compliance tests | Pytest | Blocking | Passing |
| Backend static security | Bandit | Reporting | Pending triage |
| Python dependency vulnerabilities | pip-audit | Reporting | Pending triage |
| Frontend dependency vulnerabilities | npm audit | Reporting | Pending triage |
| Secrets scanning | Gitleaks | Blocking/reporting by action behavior | Pending review |

## Open Risks

| ID | Severity | Area | Finding | Owner | Status | Remediation |
|---|---|---|---|---|---|---|
| SEC-001 | Medium | Authentication | Demo token/header-based role model remains in MVP paths | Engineering | Open | Replace with OIDC/JWT/RBAC |
| SEC-002 | Medium | Tenant isolation | Tenant enforcement needs full automated test coverage | Engineering | Open | Add tenant isolation tests |
| SEC-003 | Medium | Audit immutability | Audit events are persistent but not fully append-only enforced | Engineering | Open | Add DB constraints/policy |
| SEC-004 | Pending | Bandit | Pending baseline scan review | Engineering | Pending | Run and triage Bandit |
| SEC-005 | Pending | pip-audit | Pending baseline scan review | Engineering | Pending | Run and triage pip-audit |
| SEC-006 | Pending | npm audit | Pending baseline scan review | Engineering | Pending | Run and triage npm audit |

## Remediation Roadmap

1. Run Bandit, pip-audit, and npm audit locally.
2. Record critical/high findings in this register.
3. Fix critical/high findings.
4. Re-run scans.
5. Make Bandit/pip-audit/npm audit blocking after findings are clean or documented.
