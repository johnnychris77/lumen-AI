# LPR-DIR-014 — Compliance Readiness (Phase 3)

**No certification is claimed.** This maps *implemented / partial / missing / future*
controls against common frameworks for a future clinical-software posture. Baseline
`f889d95`.

## OWASP ASVS (Application Security Verification Standard)

| Area | Status |
|---|---|
| V2 Authentication | **Partial** — strong OIDC/JWKS + KDF hashing; insecure HS256 secret defaults (SEC-AUTH-01) + no startup validation (SEC-AUTH-02) |
| V3 Session | **Implemented** — stateless JWT with `exp`; no server session to fixate |
| V4 Access Control | **Implemented** — default-deny, `require_*` guards, tenant-membership authority, escalation tested |
| V5 Validation/Encoding | **Implemented** — pydantic; ORM parameterization |
| V7 Error/Logging | **Partial** — fail-closed errors; logging inconsistent + silent excepts (SEC-INF-03) |
| V9 Communications | **Deploy** — TLS at ingress |
| V10 Malicious code | **Partial** — bandit/secret-scan gated; no SAST beyond bandit |
| V12 Files/Resources | **Partial** — upload hash-validation; bind/tmp constants (CFG-03) |

## OWASP API Top 10 (2023)
Full mapping in `API_SECURITY_REVIEW.md`: mostly mitigated; **conditions** on API2
(auth secret defaults), API8 (misconfig: secret defaults, container-root), API10
(webhook fail-open, SEC-C-01).

## NIST SSDF (SP 800-218)
- **Implemented:** version control, code review (Codex + this program), CI security
  gates (pip-audit/npm/bandit/secret-scan), pinned production deps, SBOM.
- **Partial:** no fail-closed secret validation at startup; CI/prod manifest
  divergence (SEC-SC-01); no gated SAST/type-check/image-scan.

## SOC 2 (Security criteria — illustrative)
- **Implemented:** logical access controls (RBAC/tenant), audit logging
  (hash-chained), change management (PR + CI), backup/DR with measured RTO/RPO.
- **Partial:** secrets management (fallback defaults), monitoring/alerting depth,
  formal access-review + incident-response runbooks (present but not exercised here).

## HIPAA Security Rule safeguards (where applicable — future clinical use)
- **Technical:** access control ✅, audit controls ✅ (immutable), integrity ✅
  (hashing/immutability), transmission security ✅ (TLS). **Encryption at rest** is
  an infra control to enforce per deployment (SEC-DP-01). **No PHI** in demo
  data/image metadata (policy-aligned).
- **Administrative/Physical:** out of software scope; the physical lab is not built
  (program-level).

## FDA cybersecurity guidance (future medical-software readiness)
- SBOM ✅ (generated), threat-modeling/trust-boundaries ✅ (Phase 1 + this phase),
  secure-update/patch process (partial), coordinated-disclosure policy (not present
  — future). **No regulatory clearance or claim is made.**

## Net readiness
**Foundational security controls are implemented and test-verified**; the platform
is **not certified** and is **not production/clinically authorized**. The gating
items for any future attestation are: fix SEC-C-01 (webhook), SEC-AUTH-01/02 (secret
defaults + startup validation), and stand up formal IR/access-review/disclosure
processes. **Do not claim certification or clearance.**
