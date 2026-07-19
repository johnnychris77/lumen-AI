# LPR-DIR-014 — Phase 3 Security Validation Report

Production Readiness Program · Phase 3 · Security, Compliance & Trust Validation ·
Baseline `f889d95`. **Documentation/assessment only — no application code modified.**
No production, clinical, or regulatory authorization is granted.

## 1. Executive summary

LumenAI's security **architecture** is well-designed and, for the authenticated
application surface, **test-verified**: zero-trust OIDC/JWKS authentication, strong
password KDFs, default-deny authorization (1,593 `require_*` guards), tenant-
membership authority (header cannot elevate), hash-chained tamper-evident audit,
checksummed authorization-gated evidence, AI-advisory-only with human authority, and
fail-closed behavior throughout. The security subset passed **50/50**; `pip-audit`
and `npm audit` report **0 known vulnerabilities**; an SBOM was generated.

However, one theme prevents an unconditional pass: **secure-by-default is not fully
met.** Several secrets have **insecure fallback defaults** and there is **no
fail-closed startup validation** that required secrets are set. This single
root-cause manifests as **1 CRITICAL** (webhook fail-open → cross-tenant injection)
and **2 HIGH** (HS256 secret fallback → token forgery; no startup secret validation)
findings, all **blocking pre-production**.

**Exit decision: SECURITY VALIDATED — PASS WITH CONDITIONS.** No production or
clinical deployment; no regulatory claim.

## 2. Authentication review
Strong OIDC/JWKS primary path (explicit algorithm allowlist, requires exp/iat/sub,
validates iss/aud); PBKDF2/bcrypt hashing; dev-token gated out of prod.
**SEC-AUTH-01 (HIGH):** hardcoded HS256 secret fallbacks (`"dev-secret"` etc.) →
token forgery if `SECRET_KEY` unset. **SEC-AUTH-02 (HIGH):** `config.validate()`
omits `SECRET_KEY` and is not invoked at startup. **SEC-AUTH-03 (MEDIUM):** multiple
token issuers/validators — consolidate.

## 3. Authorization review
Default-deny; 1,593 guards; vertical + header-role escalation defended (tested). No
bypass found. Open item: complete governance-in-code enforcement (AR-03).

## 4. Tenant isolation
Authenticated surface strong and test-verified (membership-authoritative,
fail-closed). One break: **SEC-C-01** webhook cross-tenant injection via
`X-Tenant-Id` + fail-open. Cache per-tenant isolation is a pen-test candidate.

## 5. API security
1,912 endpoints, 0 UNKNOWN; pydantic validation + ORM parameterization; guard
coverage. OWASP API Top-10 conditions on API2 (auth), API8 (misconfig), API10
(webhook). Rate limiter wired best-effort (SEC-API-01).

## 6. Trust boundaries
13 of 14 boundaries hold and are test-verified. Boundary 13 (external integration)
carries the CRITICAL SEC-C-01; boundary 11 (audit) carries the MEDIUM atomicity gap.

## 7. Audit security
Hash-chained, append-only, tamper-evident, single writer; chain-verification
admin-gated. Gap: audit not atomic with the business write (SEC-AUD-01).

## 8. Evidence integrity
Checksummed, authorization-gated, immutable, quarantine-on-incomplete;
test-verified. No mutation/rewrite path found.

## 9. Data protection
Immutable governed objects (image/annotation/GT/baseline/model/audit), SHA-256-only
secret storage, retention-first deletion, DR with measured RTO/RPO. Gaps:
dataset-freeze not enforced (SEC-DP-03), at-rest encryption is an infra control.

## 10. AI governance security
The three invariants — **AI never finalizes, Unknown never approved, absence never
means clean** — are implemented and test-backed; checksum-pinned models; honest
placeholder disclosure ("not a trained CV model"); no diagnostic claim.

## 11. Supply chain security
0 Python CVEs, 0 Node CVEs; production manifest fully pinned; scanners
(pip-audit/npm/bandit/safety/secret-scan) gated in CI; SBOM generated (100
components). Gap: CI installs mostly-unpinned `backend/requirements.txt`
(SEC-SC-01).

## 12. Infrastructure security
Pinned base, `/ready` dependency hard-gate, config-driven (non-wildcard) CORS,
integrity-hashed storage. Gaps: **container runs as root (SEC-INF-01)**; secret
defaults; logging observability (silent excepts).

## 13. Compliance readiness
Foundational ASVS/API-Top-10/SSDF/SOC2/HIPAA-technical/FDA-SBOM controls implemented
and mapped (implemented/partial/missing/future). **Not certified; no clearance
claimed.** Gating items: SEC-C-01, SEC-AUTH-01/02, and formal IR/access-review/
disclosure processes.

## 14. Security scorecard
Aggregate **~3.2 / 5**. Strong (4): Authorization, Audit, Evidence, AI Governance.
Weakest (2): **Secrets**. No subsystem ≤ 1. (`SECURITY_SCORECARD.md`.)

## 15. Security risk register
1 CRITICAL, 2 HIGH (all blocking), 6 MEDIUM, 3 LOW, 4 OBSERVATION
(`SECURITY_RISK_REGISTER.md`).

## 16. Critical findings
**SEC-C-01 (CRITICAL, blocking):** external-integration webhooks fail open when
signing secret unset; tenant taken from the attacker-controllable `X-Tenant-Id`
header; no startup validation → **cross-tenant data injection on a public write**.
Must be closed and re-verified before any production authorization.

## 17. Major (HIGH) findings
- **SEC-H-01 (HIGH, blocking):** hardcoded HS256 secret fallbacks → JWT forgery /
  auth bypass on HS256 paths if `SECRET_KEY` unset.
- **SEC-H-02 (HIGH, blocking):** no fail-closed startup secret validation (root
  cause of SEC-C-01 and SEC-H-01 reaching production).

## 18. Validation commands
| Command | Result |
|---|---|
| `pytest` (auth, permission-authz, high-risk guards, header-role escalation, tenant isolation, tenant context, audit-chain, evidence authz) | **50 passed, 0 failed (24.2s)** |
| `ruff check backend/app backend/tests` | All checks passed (Phase 2) |
| `bandit -r backend/app` | 29 High (MD5 non-security), 10 Med, 142 Low; SQL sites `# nosec` allowlisted |
| `pip-audit -r requirements.txt` | No known vulnerabilities |
| `npm audit --omit=dev` | 0 vulnerabilities |
| `cyclonedx-py requirements requirements.txt` | SBOM generated (100 components) → `SBOM.cyclonedx.json` |
| secret scan | gated in CI (`security-baseline.yml`) |

Environment: Python 3.11.15 venv; fresh `test.db` per run.

## 19. Limitations
- Full suite (~3,696 tests) not run this phase — a representative security subset
  (50/50) was executed.
- Exploitability of SEC-C-01 / SEC-H-01 was established by **code inspection**, not a
  live exploit; confirmation is a pen-test item (`PENETRATION_TEST_READINESS.md`).
- `bandit` MD5/SQL findings were **characterized by inspection** (non-security /
  allowlisted), not merely counted.
- Cloud IAM, at-rest encryption, and TLS termination are **deployment-side** controls
  assessed from config, not from a running production environment.
- No dynamic DAST/pen-test was performed (out of scope; readiness assessed instead).

## 20. Phase 4 recommendation
**Proceed toward Phase 4 gated on closing the blocking set first**, in order:
1. **SEC-C-01** — require webhook signing secrets at startup (fail closed); reject
   unsigned; bind tenant to the verified signature, not `X-Tenant-Id`.
2. **SEC-H-02 + SEC-H-01** — invoke `config.validate()` at startup, extend it to
   require `SECRET_KEY` (and webhook secrets) in production and **refuse to boot**
   when missing; remove all hardcoded secret fallbacks.
3. Then MEDIUM items: audit atomicity (SEC-AUD-01), auth consolidation (SEC-M-02),
   container non-root (SEC-INF-01), dataset-freeze enforcement (SEC-DP-03), CI
   manifest pinning (SEC-SC-01), rate-limiter verification (SEC-API-01).
4. Commission an authenticated penetration test in a controlled environment to
   confirm remediation.

Phase 4 must add no features/AI-specialists/scope and must preserve the frozen
architecture and all fail-closed/tenant-isolation/audit-integrity invariants.

## Exit decision
**SECURITY VALIDATED — PASS WITH CONDITIONS.** The security architecture is sound
and test-verified; the CRITICAL + two HIGH findings share one root cause (insecure
secret defaults + no fail-closed startup validation) and are mandatory
pre-production remediations. **No production deployment. No clinical deployment. No
regulatory claim.**
