# LPR-DIR-014 — Authentication Security Review (Phase 3)

**Basis:** code inspection at baseline `f889d95` + live test subset. Scope: identity,
JWT, sessions, tokens, service/API auth, credential storage.

## Implemented controls (verified)

| Area | Implementation | Evidence |
|---|---|---|
| Primary token validation | **OIDC/JWKS** (`auth/jwks_validator.py`, `auth/jwt_validator.py`): explicit `algorithms=` allowlist, `options.require=["exp","iat","sub"]`, issuer + audience validation, expired/invalid-issuer/invalid-audience raise | `jwks_validator.py:142-160` |
| Password hashing | **PBKDF2-SHA256** (`services/security.py`) and **bcrypt** (`auth_simple`, `admin_users`, `system`) — both strong KDFs, no plaintext/MD5/SHA1 password storage | `services/security.py:2-12` |
| Token expiry | `exp` enforced (`jwt_validator.py:61-62` with bounded clock-skew; JWKS `require exp`); HS256 issuers set `exp = now + ACCESS_TOKEN_EXPIRE_MINUTES` | `services/security.py:15` |
| Dev-token gating | `deps.py`: `_DEV_AUTH_ACTIVE = ENABLE_DEV_AUTH and APP_ENV not in {production,prod}` — "a dev token can never authenticate in prod" | `deps.py:17-20,132` |
| Algorithm confusion | JWKS decode passes an explicit `algorithms` list → **`none`-alg tokens rejected**; no unsafe `verify=False` on the primary path | `jwks_validator.py:141` |
| Live verification | `test_enterprise_auth`, header-role escalation, high-risk guards | **50/50 subset passed** |

**Positive:** the primary/enterprise authentication path is a correctly-built
OIDC/JWKS validator (zero-trust, fail-closed, explicit-allowlist) and credential
storage uses strong KDFs. Dev auth is gated out of production.

## Findings

### SEC-AUTH-01 (HIGH) — hardcoded HS256 secret fallbacks (token-forgery risk)
Several HS256 code paths fall back to **publicly-known dev secrets** when
`SECRET_KEY` is unset:
- `app/main.py:177` → `os.getenv("SECRET_KEY", "dev-secret-change-in-production")`
- `app/core/config.py:5` → `os.getenv("SECRET_KEY", "dev-secret")`
- `app/routers/auth_simple.py:37` → `"dev-only-secret-not-for-production"`
- `app/deps.py:49-57` → if `SECRET_KEY` unset, imports `auth_simple.SECRET_KEY`
  (the known fallback) to decode tokens on history/summary endpoints.

**Impact:** a production deployment that forgets to set `SECRET_KEY` signs and
verifies HS256 tokens with a **known secret**, allowing an attacker to **forge a
valid JWT (including admin `sub`)** on the HS256 paths → authentication bypass.
**Likelihood:** requires `SECRET_KEY` to be unset — but **nothing forces it to be
set** (see SEC-AUTH-02). **Blocking:** mandatory pre-production remediation.
**Mitigation:** remove all fallback literals; require `SECRET_KEY` at startup
(fail closed); prefer the OIDC/JWKS path and retire the standalone HS256 issuers
(SEC-AUTH-03).

### SEC-AUTH-02 (HIGH) — no fail-closed startup secret/config validation
`config.Settings.validate()` exists and flags dev-auth misconfig, but it **(a)
does not check `SECRET_KEY`** and **(b) is not invoked at startup** (no
`.validate()` call in `main.py`). So insecure secret states (unset `SECRET_KEY`,
unset webhook signing secrets — see the CRITICAL webhook finding) **do not fail the
boot**. This is the systemic root cause linking SEC-AUTH-01 and the Phase 1 AR-15
webhook fail-open. **Mitigation:** call `validate()` at startup, extend it to
require `SECRET_KEY` + webhook signing secrets in production, and **refuse to start**
when a required secret is missing.

### SEC-AUTH-03 (MEDIUM) — authentication path fragmentation
Multiple token issuers/validators coexist: the OIDC/JWKS enterprise path plus
standalone HS256 issuers (`services/security.py`, `routers/auth_simple.py`,
`deps.py`, `routers/auth.py`) and mixed hashing (PBKDF2 vs bcrypt). This enlarges
the authentication attack surface and is why SEC-AUTH-01 has multiple sites.
**Mitigation:** consolidate onto the JWKS/OIDC path (or a single signed-token
service) and retire the legacy HS256 issuers (tracked as Directive 002 F5).

## Not observed (good)
- No bare `verify=False` / disabled signature verification on the primary path.
- No plaintext credential storage; secret API keys stored SHA-256-hash-only.
- Session fixation/replay: stateless JWT with `exp`; no server session to fixate.
  (MFA is not implemented — future control, documented in COMPLIANCE_READINESS.)

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| SEC-AUTH-01 | HIGH | Hardcoded HS256 secret fallbacks → token forgery if `SECRET_KEY` unset |
| SEC-AUTH-02 | HIGH | No fail-closed startup secret validation (omits `SECRET_KEY`; not invoked) |
| SEC-AUTH-03 | MEDIUM | Multiple auth token issuers/validators + mixed hashing (consolidate) |
