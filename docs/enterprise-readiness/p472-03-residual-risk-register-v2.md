# P472-03 — Residual Risk Register (v2 — Batch 3 update)

**Program:** P472-03 · **PR #181 (DRAFT)** · supersedes `p472-03-residual-risk-register-v1.md`
(preserved). Residual risks after Batch 3. Severity is the residual exposure given current code.

| ID | Risk | Status after Batch 3 | Residual severity | Owner / next step |
|----|------|----------------------|-------------------|-------------------|
| R-AW07 | Any authenticated user assumes any manufacturer identity | **Technically remediated** (`e615afd`): verified `ManufacturerMembership`. Open pending IAM review; onboarding workflow not built | Low (fail-closed; portals 403 until onboarded) | IAM reviewer; manufacturer onboarding |
| R-AW04-accred | Accreditation reads scoped by a client `tenant_id` | **Remediated** for programs (Day 3) + evidence-items/readiness/trend/survey/certifications (Batch 3) | Low | independent security review |
| R-AW04-rest | Foreign tenant parameter on 32 non-accreditation routes (network-intelligence, enterprise, intelligence, commercial, olympus, genesis-ai, billing, infinity, growth) | **OPEN** (analyzed, roadmap in Batch 3 review §3) | Medium–High (cross-tenant read via parameter) | Batch 3b per-module remediation |
| R-AW03 | Foreign `X-LumenAI-Tenant-Id` binds data on 118 routes | **OPEN** (roadmap) | Medium–High | Batch 3b |
| R-AW06N | No-membership principal served in `default-tenant` on 28 routes | **OPEN** (roadmap) | Medium | Batch 3b |
| R-AW06M | Verified member with no header pooled in `default-tenant` on 122 routes | **OPEN**; sweep classifies as pooling, "no attack" | Low–Medium (correctness/pooling, not exfiltration) | Batch 3b |
| R-PA1 | Platform-admin reaches any tenant | Access unchanged; now **logged** (Day 3) | Medium (privileged, now detectable) | Governance decision + tamper-evident sink |
| R-GD3B | Cross-tenant vendor-baseline sharing | Design-only, blocked on AW-07 + governance | N/A (not built) | Clinical + security governance |
| R-DAY3 | 4 AW-04/08 findings remediated but open | Day-3 tripwires red by design | Low (code secure) | Independent-review closure |
| R-LEGACY | NULL-tenant vendor baselines + unattributed data | Quarantined fail-closed | Low (unreachable) | Clinical attribution packet |

## Aggregate
The most serious residual exposure is the **AW-03/AW-04/AW-06N exfiltration tail (174 routes across
~18 modules)**, analyzed but not yet remediated. This alone keeps the enterprise release at
**NO-GO**. AW-07 and the accreditation AW-04 routes are technically remediated and awaiting
independent review.
