# LumenAI — Support Operations Manual

Objective 4 review. Distinguishes product/customer support (this document's real scope) from security-incident response (a separate, and per this review's findings, currently-unimplemented process — see `docs/commercial-readiness/LEGAL_GOVERNANCE_PACKAGE.md`).

## Support levels

- **Level 1**: initial triage against `PilotErrorLog`'s five real, structured failure categories (upload failure, AI-analysis failure, baseline-lookup failure, role-permission failure, report-generation failure) — a Level 1 agent should check this log first before escalating, per `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md`'s troubleshooting guidance.
- **Level 2**: platform-configuration issues (role/tenant setup, SSO integration problems) — reference `docs/customer/customer-onboarding-playbook.md`'s SSO/OIDC setup detail as the Level 2 knowledge base for those specific issues.
- **Level 3 / Engineering**: code-level defects. Use the real severity classification already documented in `docs/regulatory/software-lifecycle-readiness.md` §8.1 (Critical/P0 = 4hr response, High/P1 = 24hr, Medium/P2 = 1 week, Low/P3 = next release cycle) as the Level 3 SLA framework, rather than inventing a separate one.
- **Clinical**: escalations involving a disputed AI finding, disposition, or clinical-safety concern should route to a clinical reviewer, not Engineering — reference `docs/clinical-validation/PATIENT_SAFETY_MODEL.md`'s automation-bias and false-reassurance mitigations as the framework a clinical escalation reviewer should apply.

## Support hours

Tie support-hour commitments to the tier/cadence model already documented in `docs/customer/customer-success-playbook.md` (CSM tier/cadence: Starter/Professional/Enterprise/Health System) rather than a single flat support-hours policy — higher tiers warrant more responsive coverage windows, consistent with the same document's QBR cadence scaling by tier.

## Incident response (product/support scope — not security)

Use the same P0-P3 severity/response-time framework as Level 3 above for product incidents (a dashboard outage, a broken workflow). **This is distinct from a security incident**, for which — per this review's security-operations recon — **no operational runbook currently exists in this codebase**; `docs/security/compliance-control-matrix.md` itself lists "completing incident response and operational runbooks" as open, unimplemented work. Do not conflate the two: a product-support incident (e.g., "dashboards are returning stale data") has a real, referenceable severity/response framework; a security incident (e.g., "we suspect unauthorized access") currently does not, beyond the FDA-submission-oriented narrative process described in `docs/regulatory/cybersecurity-readiness.md` §7, which is not wired to any actual engineering runbook.

## Severity matrix and SLA definitions

| Severity | Definition | Response time | Source |
|---|---|---|---|
| Critical / P0 | Production outage, data-integrity risk, patient-safety-relevant failure | 4 hours | `docs/regulatory/software-lifecycle-readiness.md` §8.1 |
| High / P1 | Major feature broken, no workaround | 24 hours | same |
| Medium / P2 | Feature degraded, workaround exists | 1 week | same |
| Low / P3 | Cosmetic/minor issue | Next release cycle | same |

This table is real, already documented, and code-adjacent (it governs the same defect-classification process referenced in `docs/commercial-readiness/PRODUCT_OPERATIONS_GUIDE.md`) — use it as the single shared severity vocabulary across support, engineering, and product operations rather than each function defining its own.

## What genuinely needs new authorship

A dedicated support-ticketing/case-management process description (which system, what fields, how L1→L2→L3 handoff is actually recorded) was not found documented anywhere in this repository and would need new authorship — this manual's contribution is the severity/tier framework above, assembled from real sources, not a from-scratch support-ops design.
