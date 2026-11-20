# P472-03 Batch 8 — PA-1 Privileged Access: Environment-Gate Investigation (v1)

**Issue #190 B7.8 · PR #181 (DRAFT).** Investigation only. **PA-1 is unsigned. No privileged-access policy was
implemented or changed.** The findings are pinned by strict tripwires that fail today: RB-T38…RB-T40.

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

| ID | Finding | Exposure | Tripwire |
|---|---|---|---|
| PA1-01 | A process marked production only through `ENVIRONMENT` (the docker-compose convention) activates dev tokens as admin when `ENABLE_DEV_AUTH=true`. The startup guard sees production; the token map does not; `validate()` is silent | configuration-dependent; not the Render config | **RB-T38** (failing) |
| PA1-02 | `DEMO_MODE=1` exposes `/api/demo/*`, including a data-deleting reset, to the **public** literal `Bearer dev-token`, with no production check. This contradicts the standing rule against hard-coded dev tokens | configuration-dependent; `DEMO_MODE` is not set by `render.yaml` | **RB-T39** (failing) |
| PA1-03 | The enterprise JWT-shape check runs only for `ENVIRONMENT == "production"` exactly: off with `APP_ENV` alone, with `prod`, or with any capitalisation | defence-in-depth gap | **RB-T40** (failing) |
| PA1-04 | `portfolio_authz` grants are dead code (key mismatch), leaving the literal `dev-token` as the only working grant. "Correcting" the keys would **activate** all-tenant, non-anonymised portfolio access for any `tenant_admin`. That needs a PA-1/GD-8 decision, not a key fix | latent escalation | none (documented; a reviewer should confirm) |
| PA1-05 | `AUTH_MODE` defaults to `dev` in `enterprise_auth`. Outside production every enterprise route trusts actor, role and tenant headers to anyone holding `DEV_AUTH_TOKEN` (default literal `dev-token`). Production refuses to start without an explicit `AUTH_MODE` | non-production environments, shared staging | none (by design; PA-1 decision) |
| PA1-06 | `Settings.validate()` only logs `ENABLE_DEV_AUTH=true` and a default `DEV_AUTH_TOKEN` in production | silent misconfiguration | covered by RB-T38 for the dev-token path |
| PA1-07 | `render.yaml` hard-codes a personal pilot administrator in `BOOTSTRAP_TENANT_ADMINS`. That is an identity grant held in deployment config with no expiry or recorded approval (the value is not repeated here) | standing privilege | none (PA-1/AUTH-1 decision) |

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

Signature (PA-1): Decision ____ · Name ____ · Role ____ · Date ____ — **UNSIGNED**
