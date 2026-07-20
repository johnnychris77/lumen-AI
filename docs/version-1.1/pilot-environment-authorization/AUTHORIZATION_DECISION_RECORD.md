# AUTHORIZATION DECISION RECORD — LPR-DIR-031A

Formal decision record for the Environment Authorization request. **Status: PENDING — NOT
SIGNED.** No authorization is in effect until the accountable authorities sign below. This
document does not, by its existence, authorize provisioning, spend, or any pilot activity.

## 1. Decision requested
Authorize provisioning of the pilot-grade, non-production managed environment specified in
`MANAGED_ENVIRONMENT_SPECIFICATION.md`, delivery of scoped credentials per
`CREDENTIAL_AND_ACCESS_REQUIREMENTS.md`, and the budget envelope per
`COST_AND_BUDGET_ENVELOPE.md`, to unblock **DIR-032 (Operational Execution)**.

## 2. Decision options
- **APPROVED** — provision + supply credentials + release budget; DIR-032 may begin.
- **APPROVED WITH CONDITIONS** — approved subject to listed conditions.
- **DENIED** — do not provision; program holds at DIR-031 (Pilot Entry DENIED).

## 3. Decision
> **Recorded decision:** ☐ APPROVED ☐ APPROVED WITH CONDITIONS ☐ DENIED
> **Conditions (if any):** ____________________________________________
> **Decision date (UTC):** __________

## 4. Sign-off (all required for APPROVED)
| Role | Name | Decision | Date | Signature/ref |
|---|---|---|---|---|
| CTO | | | | |
| CISO | | | | |
| COO | | | | |
| Chief Quality Officer | | | | |
| Release Engineering Director | | | | |
| DevSecOps Director | | | | |
| Finance (budget) | | | | |
| Infrastructure/Cloud owner (provisioner) | | | | |

## 5. What signing authorizes (and what it does NOT)
**Authorizes:** provisioning C1–C8, scoped credentials, and the confirmed budget for a
pilot-grade, **synthetic/non-PHI** environment.
**Does NOT authorize:** any pilot (DIR-034), pilot execution (DIR-035), production, clinical
use, PHI processing, or any regulatory claim.

## 6. Post-signature preconditions (before DIR-032 starts)
- [ ] Environment C1–C8 provisioned + reachable from the executing context.
- [ ] Credentials delivered per requirements (presence-verified, values never in repo).
- [ ] `GET /health` 200 over HTTPS at the ingress.
- [ ] Billing cap / budget alert active.

## 7. Integrity note
Until this record is signed and section 6 is satisfied, **DIR-032 cannot begin** and the
program state is unchanged: **Pilot Entry DENIED; no production/clinical/regulatory claim.**
