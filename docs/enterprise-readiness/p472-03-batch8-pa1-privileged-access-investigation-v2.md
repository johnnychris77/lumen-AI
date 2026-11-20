# P472-03 — PA-1 Privileged Access: Environment-Gate Investigation and Remediation (v2)

**Issue #190 · PR #181 (DRAFT)** · supersedes v1 (preserved). §1–§4 are the Batch 8 investigation, unchanged
except for the status column. §5–§7 record the **PA-1 remediation** (`c2014ff` reproduction, `829f36a` fix), done
under the user's explicit direction. **PA-1 is still unsigned:** the remediation is an author fail-closed floor that
the PA-1 decision must ratify or replace. RB-T38…T40 are author-converted and pending non-author review.

Evidence:
- `scripts/p472_03_pa1_env_probe.py` runs each configuration in a fresh subprocess with a throw-away SQLite
  database. Output: `evidence/p472-03-batch8/pa1/pa1_env_probe_c22a879.json`.
- `tests/test_p472_03_batch8_pa1_env_gates.py`.
- Local only. No production system was contacted. The probe uses a fixed local token, never a deployed secret.

## 1. The gates and what each reads

| Gate | Code | Production signal it reads | Effect |
|---|---|---|---|
| Startup refusal | `app/main.py` | `APP_ENV` **or** `ENVIRONMENT` ∈ {production, prod} (lower-cased) | refuses to start on a weak `SECRET_KEY`, on unset `AUTH_MODE`, or on `AUTH_MODE=dev` without `ALLOW_DEV_AUTH_IN_PROD=true` |
| Config validation | `app/config.py::Settings.validate` | `APP_ENV` only | **logs** issues (`ENABLE_DEV_AUTH` true, `DEV_AUTH_TOKEN == "dev-token"`) and does not refuse |
| Dev-token map (`get_current_user`, principal) | `app/deps.py` | `ENABLE_DEV_AUTH` **and** `APP_ENV` ∉ {production, prod} — `ENVIRONMENT` ignored | `DEV_*_TOKEN` env values map to admin / spd_manager / operator / vendor_user / viewer |
| Enterprise auth mode | `app/enterprise_auth.py::get_auth_context` | `AUTH_MODE` (default **`dev`**) | `dev`: bearer `DEV_AUTH_TOKEN` (default literal `dev-token`), actor/role/tenant read **from request headers** |
| Enterprise JWT-shape check | `require_enterprise_auth` | `ENVIRONMENT == "production"` exactly (case-sensitive; `APP_ENV` ignored) | rejects non-JWT bearer tokens |
| Demo routes | `app/routes/demo.py` | `DEMO_MODE == "1"` only | accepts the public literals `Bearer dev-token` / `Bearer demo-token` with **no other authentication**; `/api/demo/reset` deletes `demo` / `default-tenant` pilot rows |
| Portfolio routes | `app/portfolio_authz.py` | none | allows the literal token `dev-token`. Also allows roles {platform_admin, portfolio_admin, tenant_admin} and emails {admin@local, portfolio@local, platform@local}, but these read keys (`role_name`, `user_email`) the principal does not carry (`role`, `email`), so **they never match** |

## 2. Probe results (selected; full JSON in evidence)

| Configuration | Starts | Dev token accepted as admin | JWT-shape check | `/api/demo/reset` with public `dev-token` |
|---|---|---|---|---|
| 1 `render.yaml` (APP_ENV=ENVIRONMENT=production, AUTH_MODE=oidc, ENABLE_DEV_AUTH=false) | yes | no | on | 403 |
| 2 APP_ENV=production only | yes | no | **off** | 403 |
| 3 **ENVIRONMENT=production only, ENABLE_DEV_AUTH=true** | yes; `validate()` reports **nothing** | **yes** | on | 403 |
| 4 APP_ENV=prod, AUTH_MODE unset | **refused** (AUTH_MODE not set) | — | — | — |
| 5 APP_ENV=production, AUTH_MODE=dev, ALLOW_DEV_AUTH_IN_PROD=true | yes (acknowledged exception) | no | **off** | 403 |
| 6 **production + DEMO_MODE=1** | yes | no | on | **200** (destructive reset with a public token) |
| 7 APP_ENV=ENVIRONMENT=`Production` (capitalised) | yes | no | **off** | 403 |
| 8 development defaults, ENABLE_DEV_AUTH=true | yes | yes (intended) | off | 403 |

Portfolio access, probed with JWTs for users holding global roles `platform_admin`, `tenant_admin`, `admin` and the
identity `admin@local`: **403 for all**. In a deployment with dev auth active and `DEV_AUTH_TOKEN=dev-token` (the
`.env.example` default), the literal token is the only way in.

## 3. Findings (open; pinned; not fixed)

| ID | Finding | Exposure | Tripwire / status after `829f36a` |
|---|---|---|---|
| PA1-01 | A process marked production only through `ENVIRONMENT` (the docker-compose convention) activates dev tokens as admin when `ENABLE_DEV_AUTH=true`. The startup guard sees production; the token map does not; `validate()` is silent | configuration-dependent; not the Render config | RB-T38 — **author-remediated**, review pending |
| PA1-02 | `DEMO_MODE=1` exposes `/api/demo/*`, including a data-deleting reset, to the **public** literal `Bearer dev-token`, with no production check. This contradicts the standing rule against hard-coded dev tokens | configuration-dependent; `DEMO_MODE` is not set by `render.yaml` | RB-T39 — **author-remediated in production**, review pending; outside production unchanged |
| PA1-03 | The enterprise JWT-shape check runs only for `ENVIRONMENT == "production"` exactly: off with `APP_ENV` alone, with `prod`, or with any capitalisation | defence-in-depth gap | RB-T40 — **author-remediated**, review pending |
| PA1-04 | `portfolio_authz` grants are dead code (key mismatch), leaving the literal `dev-token` as the only working grant. "Correcting" the keys would **activate** all-tenant, non-anonymised portfolio access for any `tenant_admin`. That needs a PA-1/GD-8 decision, not a key fix | latent escalation | none — **deliberately unchanged** (no new privileged pathway); literal `dev-token` grant now inert in production |
| PA1-05 | `AUTH_MODE` defaults to `dev` in `enterprise_auth`. Outside production every enterprise route trusts actor, role and tenant headers to anyone holding `DEV_AUTH_TOKEN` (default literal `dev-token`). Production refuses to start without an explicit `AUTH_MODE` | non-production environments, shared staging | none — **unchanged outside production**; in production `AUTH_MODE` must be `oidc` and the static dev token is refused at request time |
| PA1-06 | `Settings.validate()` only logs `ENABLE_DEV_AUTH=true` and a default `DEV_AUTH_TOKEN` in production | silent misconfiguration | **remediated**: the dev-auth and demo items now refuse startup instead of only logging |
| PA1-07 | `render.yaml` hard-codes a personal pilot administrator in `BOOTSTRAP_TENANT_ADMINS`. That is an identity grant held in deployment config with no expiry or recorded approval (the value is not repeated here) | standing privilege | none — **unchanged** (PA-1/AUTH-1 decision) |

## 4. What a PA-1 decision must settle before any change

1. **A single production signal.** One function, read by every gate, case-insensitive, with both variables honoured.
   Should disagreement between `APP_ENV` and `ENVIRONMENT` refuse to start? (Recommended: yes.)
2. **Refuse instead of log** for `ENABLE_DEV_AUTH=true`, `DEV_AUTH_TOKEN` default, and `DEMO_MODE=1` in any
   production signal.
3. **Demo routes.** Remove the public literal tokens, unmount them in production, or keep them behind an
   authenticated platform role.
4. **Portfolio access.** Who, if anyone, may see all tenants. If someone does: anonymised (hospital identities must
   be anonymised), purpose-bound and audited. Delete the literal `dev-token` and `@local` grants either way.
5. **Platform-admin purpose binding** (from the Batch 7 PA-1 packet): purpose, ticket, time limit, tamper-evident
   log, periodic review.
6. **Bootstrap administrators:** recorded approval and expiry for any identity granted through deployment config.

Rollback criterion for any implementation: the Render configuration control
(`test_control_render_configuration_is_closed`) and the startup refusal control must keep passing.



## 5. Remediation (`829f36a`) — what changed

**One determination.** `backend/app/core/environment.py`:
- `determine_environment()` reads `APP_ENV` and `ENVIRONMENT`, stripped and lower-cased.
- Production is either variable in {`production`, `prod`}.
- A conflict is one variable production and the other set to anything else. A conflict counts as production, so
  every runtime gate fails closed.

**Startup refusal** (`production_configuration_errors`, enforced by `app.main`). In production the process exits
`FATAL: refusing to start …` when any of these hold:

| Condition | Before | After |
|---|---|---|
| `APP_ENV` / `ENVIRONMENT` conflict | started (dev tokens active with `ENVIRONMENT=production`, `APP_ENV=development`) | **refused** |
| `SECRET_KEY` unset / weak | refused | refused (unchanged) |
| `AUTH_MODE` unset | refused | refused (message keeps `AUTH_MODE is not set`) |
| `AUTH_MODE=dev` + `ALLOW_DEV_AUTH_IN_PROD=true` | **started; dev token + header-supplied `admin` role and any tenant accepted** | **refused**; the exception is no longer honoured |
| `AUTH_MODE` other than `oidc` | started (500 at request time) | **refused** |
| `ENABLE_DEV_AUTH` true | started; logged only | **refused** |
| `DEMO_MODE` enabled | started; public reset 200 | **refused** |

**Runtime gates** re-read the determination at call time (defence in depth for workers, scripts, harnesses):

| Gate | Production behaviour now |
|---|---|
| `deps.dev_token_role()`, the only dev-token check (`deps`, `app.auth`, `tenant_authz`, `enterprise_access_control`) | `None` → 401 |
| demo token (`app.auth`, `enterprise_access_control`, `enterprise_auth.is_demo_mode`) | refused |
| `/api/demo/*` | **403 whatever `DEMO_MODE` says**; nothing deleted |
| `enterprise_auth._require_dev_auth_context` | static dev token refused; a signed per-user JWT still accepted |
| `require_enterprise_auth` JWT-shape check | on for any production signal, any case |
| `portfolio_authz` literal `dev-token` | inert (role/email keys untouched: PA1-04) |
| `Settings.is_production`, `auth_simple` SECRET_KEY guard, `users` seed guard, CORS, OpenAPI, HSTS | same determination |

**Not changed:**
- the global-`admin` cross-tenant rule;
- break-glass and purpose binding;
- PA1-04 (portfolio access);
- PA1-05 outside production;
- PA1-07 (bootstrap administrator).

No role, membership or administrator is created anywhere.

## 6. Evidence

| | SQLite | PostgreSQL 16.15 |
|---|---|---|
| Reproduction before (`8bfcc9a`, `scripts/p472_03_pa1_remediation_repro.py`) | RB-T38/39/40 + AUTH_MODE=dev path reproduced | identical |
| Tripwires `--runxfail` before | 3 failed / 2 passed | 3 failed / 2 passed |
| Reproduction after (`829f36a`) | all production rows closed; dev controls unchanged | identical |
| `test_p472_03_batch8_pa1_env_gates.py` after | 8 passed | 8 passed |
| `test_p472_03_pa1_remediation.py` | 53 passed | 53 passed |
| Review kit RB-T38…T40 | 12/12 variants matched | 12/12 matched |

Evidence: `evidence/p472-03-pa1-remediation/{before-8bfcc9a,after-829f36a,kit,final-829f36a}/`. Test changes are
listed separately: `p472-03-pa1-remediation-assertion-change-log-v1.md`.

## 7. Still for the PA-1 decision (§4, re-stated)

1. Ratify or replace the single signal and refusal list, including removal of `ALLOW_DEV_AUTH_IN_PROD`.
2. Allowed environment vocabulary (`prd`, `live`, … are non-production today: R-PA1-ENV-VALUES).
3. Whether shared staging counts as production (public literals and header-trusting dev mode still work outside
   production: R-PA1-NONPROD).
4. Demo routes: keep (non-production only), remove, or put behind an authenticated platform role.
5. Portfolio access (PA1-04 with GD-8): who, if anyone; anonymised, purpose-bound, audited.
6. Platform-admin break-glass and purpose binding; bootstrap administrators (PA1-07).

Signature (PA-1): Decision ____ · Name ____ · Role ____ · Date ____ · Second approver ____ — **UNSIGNED**
