# LPR-DIR-014 — API Security Review (Phase 3)

**Basis:** route inventory (Phase 1) + code inspection at `f889d95`. Evaluated
against **OWASP API Security Top 10 (2023)**.

## API surface (measured, Phase 1 inventory)

| Metric | Value |
|---|---|
| Total endpoints | 1,912 |
| Write endpoints | 728 |
| Unauthenticated writes | 10 (all PUBLIC_BY_DESIGN) |
| AUTHENTICATED / TENANT_SCOPED | 882 / 855 |
| UNKNOWN classification | 0 |

## OWASP API Top 10 (2023) assessment

| # | Risk | Status | Notes |
|---|---|---|---|
| API1 | Broken Object Level Authorization (BOLA) | **Mostly mitigated** | Tenant-scoped queries + guards; recommend per-object ownership pen-test (SEC-TEN-02) |
| API2 | Broken Authentication | **Conditions** | Strong OIDC/JWKS primary path, but HS256 secret fallback (SEC-AUTH-01) + no startup secret validation (SEC-AUTH-02) |
| API3 | Broken Object Property Level Authorization / mass assignment | **Mitigated** | Pydantic request models constrain fields; responses are explicit schemas |
| API4 | Unrestricted Resource Consumption | **Partial** | `slowapi` limiter present but wired best-effort (`main.py:214` try/except pass); rate-limit coverage should be verified (SEC-API-01) |
| API5 | Broken Function Level Authorization | **Mitigated** | 1,593 `require_*` guards; vertical-escalation tested |
| API6 | Unrestricted Access to Sensitive Business Flows | **Mitigated** | Governed workflow state machine; human authority required |
| API7 | Server-Side Request Forgery | **Not observed** | No user-controlled outbound URL fetch surfaced; JWKS URL is config, not user input |
| API8 | Security Misconfiguration | **Conditions** | Insecure secret defaults (SEC-AUTH-01), container-as-root (INFRA), CORS `allow_credentials=True` (verify strict origins) |
| API9 | Improper Inventory Management | **Mitigated** | 0 UNKNOWN endpoints; OpenAPI generated (no CI diff gate — DOC-01) |
| API10 | Unsafe Consumption of 3rd-Party APIs | **Conditions** | Webhook ingress fails open (SEC-C-01); outbound consumption limited |

## Input / output / injection

- **Schema/input validation:** pydantic models on request bodies (422 on bad input).
- **Injection resistance:** SQLAlchemy ORM parameterized queries dominate. `bandit`
  B608 flagged a few string-built SQL sites (`capa_service`, `executive_decisions`,
  `portfolio_tenants`) — inspection shows they use **parameterized `?` values** with
  the SET clause built **only from a server-side allowlist**, annotated `# nosec`
  with rationale. **Low real injection risk** (reviewed defense-in-depth), but
  recommend migrating them to full ORM/expression construction (SEC-API-02, LOW).
- **File/upload validation:** CV image ingestion validates content/hash;
  `bandit` flagged `B104` (bind-all) and `B108` (tmp dir) as constants in CV
  utilities — make configurable (CFG-03), not an injection.
- **Output filtering / secure errors:** explicit response schemas; fail-closed
  status codes (401/403/409/422). No stack traces leaked on the sampled paths.

## Findings
| ID | Sev | Finding |
|---|---|---|
| SEC-API-01 | MEDIUM | Rate limiter wired best-effort (`try/except pass`); verify coverage on public/auth endpoints (API4) |
| SEC-API-02 | LOW | A few allowlisted string-built SQL sites (`# nosec`); migrate to ORM/expression (API of injection defense-in-depth) |
| SEC-API-03 | OBSERVATION | No CI OpenAPI schema-diff gate (API9 inventory drift) |

**Positive:** 0 UNKNOWN endpoints, pydantic validation, ORM parameterization,
guard coverage, explicit response schemas. The material API risks trace back to the
secret-default/startup-validation theme (API2/API8) and the webhook (API10).
