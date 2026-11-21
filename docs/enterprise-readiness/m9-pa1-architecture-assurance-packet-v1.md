# Milestone 9 — PA-1 Privileged-Access Architecture Assurance Packet (v1)

**Issue #191 (M9.2) · PR #181 (DRAFT) · baseline `bed42c8` (application code `829f36a`).** Prepared by the change
author for an **independent architecture reviewer** and for the PA-1 decision owners. It describes the current
design with file:line references, lists findings with a proposed severity and owner, and poses the questions
the PA-1 decision must answer.

**Status: PA-1 UNSIGNED. No reviewer has assessed this packet.** Severities are the author's proposals for the
reviewer to confirm or change. No production system was accessed and no role was activated.

Line references are at `bed42c8`.

## 1. Scope and method

| In scope | Method used by the author |
|---|---|
| Production-environment determination (startup, deps, enterprise auth, demo routes, portfolio) | code reading; reproduction script `p472_03_pa1_remediation_repro.py` on SQLite + PG16; 53 layer tests; A-1 mutation check |
| Global-admin authority and how admins are created | code reading only |
| Break-glass access | code reading (none exists) |
| Bootstrap administrators (`BOOTSTRAP_TENANT_ADMINS`, `ADMIN_BOOTSTRAP_TOKEN`) | code reading; `render.yaml` |
| Portfolio permissions | code reading; Batch 8 probe (JWT users with global roles: 403) |
| Staging / non-production security | code reading; probe controls |
| Deployment contract | `render.yaml`, compose files; **deployed variables not seen** |

## 2. Architecture as built

### 2.1 Production determination (remediated in `829f36a`; review pending)

| Element | Where | Behaviour |
|---|---|---|
| Canonical determination | `app/core/environment.py:67` `determine_environment`, `:84` `is_production` | production if `APP_ENV` **or** `ENVIRONMENT` ∈ {production, prod}, stripped and case-insensitive; a conflict (one production, other set to anything else) counts as production |
| Startup refusal | `environment.py:89` `production_configuration_errors`, `:134`; `app/main.py:319-321` | `sys.exit` on conflict, weak `SECRET_KEY`, `AUTH_MODE` ≠ `oidc` (unset included), `ENABLE_DEV_AUTH` on, `DEMO_MODE` on |
| Dev-token gate | `app/deps.py:24` (import time), `:38` `dev_token_role` (call time) | no dev role when production; used by `deps`, `app.auth`, `tenant_authz`, `enterprise_access_control` |
| Demo routes | `app/routes/demo.py:29` | 403 in production whatever `DEMO_MODE` says |
| Demo token readers | `enterprise_auth.py:27` `is_demo_mode`; `app/auth/__init__.py`; `enterprise_access_control.py` | refused in production |
| Enterprise static dev token | `enterprise_auth.py:151` | refused in production; signed per-user JWT still accepted |
| JWT-shape check | `enterprise_auth.py:318`, `:322` | on for any production signal |
| Portfolio literal token | `portfolio_authz.py:33` | inert in production |

**Workers and other entry points.** `render.yaml:84` defines a `worker` service built from the same image
(`Dockerfile.api`), whose command is `uvicorn app.main:app`. It therefore passes the same startup refusal. Its
variables (`render.yaml:84-111`) set both production signals, `AUTH_MODE=oidc` and `ENABLE_DEV_AUTH=false`.
Entry points that do **not** import `app.main` (e.g. `backend/run_reset_app.py`, `app/seed_demo.py`, Alembic,
ad-hoc scripts) get only the call-time gates, not the startup refusal. **Reviewer task:** enumerate them and
confirm none grants access or resets data in production.

### 2.2 Global-administrator authority (unchanged; open)

| Element | Where | Behaviour |
|---|---|---|
| Definition | `app/security/principal.py:81` | `is_platform_admin` ⇔ `role == "admin"` |
| Role source (app-issued JWT) | `app/routers/auth_simple.py:103-112` | `user_role_assignments.role`, else `users.role`, else `viewer` |
| Cross-tenant resolution | `app/auth/tenant_scope.py:147-165` | an admin resolves to `own tenant or the named header or default-tenant`, with **no membership check** |
| Platform-wide views | `tenant_scope.py:193-203` | admin gets tenant-less views on routes that allow it |
| Membership listing | `app/routes/tenant_admin.py:58` | admin sees all memberships |
| Record of use | `tenant_scope.py:158`, `:197` | a structured `WARNING` to the application log. **No audit event, no purpose, no ticket, no expiry, not tamper-evident** |

### 2.3 How administrators come into existence (unchanged; open)

| Path | Where | Behaviour | Observations |
|---|---|---|---|
| Bootstrap endpoint | `app/routes/admin_users.py:60-122` | `POST /api/admin/bootstrap` with `X-Bootstrap-Token` = `ADMIN_BOOTSTRAP_TOKEN` grants **global `admin`** to any username and can set a login password | Inert (404) when the variable is unset. When set, it is **not one-shot**: unlimited admins, any time, by anyone holding the token. The audit event records `actor_email=body.username` (`:110`), i.e. the *grantee*, not the caller. Not in `render.yaml`; whether it is set in the deployed environment is unknown |
| Role assignment | `admin_users.py:150-154` | any `admin` can assign any role, including `admin` | no second approver |
| Tenant bootstrap | `app/services/tenant_bootstrap.py:26-58`; called at startup `app/main.py:208-212` | every email in `BOOTSTRAP_TENANT_ADMINS` gets an enabled `tenant_admin` membership in `BOOTSTRAP_TENANT_ID` (default `default-tenant`) | runs on **every** startup and **re-enables** a membership that was disabled, so revoking a listed administrator is undone at the next restart. `render.yaml:73` lists a personal identity (not repeated here) with no recorded approval or expiry |
| Seed | `app/routers/users.py` | admin seed password required in production | — |

### 2.4 Break-glass

None exists. There is no purpose-bound, time-limited, second-person-approved elevated access path. The only
elevated paths are a standing `admin` role (2.2) and the bootstrap paths (2.3).

### 2.5 Portfolio permissions (unchanged on purpose)

`app/portfolio_authz.py:9-40`: grants for `platform_admin`/`portfolio_admin`/`tenant_admin` and three `@local`
emails read keys (`role_name`, `user_email`) that the principal does not carry, so they never match. The only
working grant was the literal `dev-token`, which is now inert in production (`:33`). Fixing the keys would give
**every `tenant_admin`** an all-tenant, non-anonymised portfolio view. That contradicts the anonymisation rule
for cross-hospital data and needs PA-1 + GD-8 first. The current state is pinned by `TestNoNewPrivilegedPathway`.

### 2.6 OIDC role mapping

`app/auth/jwt_validator.py:83`: the enterprise role is the `lumenai_role` claim, else the first of
`roles`/`groups`, else `viewer`. The tenant comes from the token and an enabled membership is required
(`enterprise_auth.py:203-235`). **Reviewer task:** confirm that no enterprise check lets an IdP-asserted role
cross tenants. The roles granted are as trustworthy as the IdP's group administration, which is outside this
repository.

### 2.7 Non-production / staging

Outside production (no production signal):
- the dev-token map works if `ENABLE_DEV_AUTH=true`;
- the public literals `dev-token` / `demo-token` work on demo routes when `DEMO_MODE=1`;
- `AUTH_MODE` defaults to `dev`, which trusts actor/role/tenant headers for the holder of `DEV_AUTH_TOKEN`
  (PA1-05).

A shared staging or pilot environment that is not marked production is exposed to anyone who knows the
public literals.

## 3. Findings (author-proposed severity; reviewer to confirm)

| ID | Finding | Proposed severity | Status | Proposed owner (role) |
|---|---|---|---|---|
| PA1-01/02/03 | Environment-gate defects (RB-T38…T40) | was High | author-remediated `829f36a`; review pending | platform security |
| PA1-04 | Dead portfolio grants; latent all-tenant escalation | Medium (latent) | open, deliberately unchanged | PA-1 + GD-8 |
| PA1-05 | Header-trusting dev mode and public literals outside production | Medium (any shared non-prod) | open | PA-1 |
| PA1-06 | `validate()` logged only | — | remediated (startup refusal) | — |
| PA1-07 | Personal bootstrap administrator in `render.yaml`, no approval/expiry | Medium | open | PA-1 / AUTH-1 |
| **PA1-08 (new)** | `ADMIN_BOOTSTRAP_TOKEN` mints unlimited global admins at any time; audit names the grantee, not the caller | **High if the variable is set in production**; Low if unset | open; deployed value unknown | PA-1 + operations |
| **PA1-09 (new)** | `BOOTSTRAP_TENANT_ADMINS` re-enables disabled memberships on every startup; revocation is not durable | Medium | open | PA-1 / AUTH-1 |
| **PA1-10 (new)** | Global-admin cross-tenant use is recorded only as an application-log WARNING (no audit event, purpose or expiry) | High (standing privilege, weak accountability) | open | PA-1 |
| **PA1-11 (new)** | Any admin can grant `admin` with no second approver | Medium | open | PA-1 |
| PA1-12 | Production vocabulary limited to `production`/`prod` (R-PA1-ENV-VALUES) | Low–Medium | open | platform security |
| PA1-13 | Entry points outside `app.main` lack the startup refusal (call-time gates only) | Low (to be enumerated) | open | platform security |
| PA1-14 | Removed `ALLOW_DEV_AUTH_IN_PROD` exception: deployments relying on it will not start (R-PA1-CONTRACT) | Medium (availability) | intended; needs ratification | PA-1 + operations |

PA1-08…PA1-11 are recorded here for the first time. They are code observations only. Nothing was changed,
and no production configuration was inspected.

## 4. Reviewer checklist

1. Confirm every reader of a production signal goes through `app/core/environment.py`:
   `grep -rn "APP_ENV\|ENVIRONMENT\|DEMO_MODE\|ENABLE_DEV_AUTH\|AUTH_MODE" backend/app`.
   Known non-gate readers: `inference_gate.py`, `config.demo_scoring_env_permitted`, `/health` display.
2. Re-run `p472_03_pa1_remediation_repro.py` at `c2014ff` and `bed42c8` on both DBs, and the A-1 mutation
   check (handbook §5).
3. List every entry point that does not import `app.main` (PA1-13), and check its behaviour under
   `ENVIRONMENT=production`.
4. Trace every `is_platform_admin` / `role == "admin"` reader and classify it: cross-tenant read,
   cross-tenant write, platform-wide view, management.
5. Trace every path that can create `admin` or `tenant_admin` (2.3), and confirm none is reachable without a
   secret or an existing admin.
6. Confirm the OIDC role mapping cannot cross tenants (2.6).
7. Assess the staging posture against the organisation's policy (2.7).
8. Record findings with severity and owner in the risk register (new rows), under your own identity.

## 5. Decisions PA-1 must make (owner: platform security + compliance; second approver: independent security)

| # | Question | Options | Author recommendation (no authority) |
|---|---|---|---|
| 1 | Ratify the production-determination floor and the refusal list, including removal of `ALLOW_DEV_AUTH_IN_PROD` | ratify / amend / replace | ratify |
| 2 | Production vocabulary | keep {production, prod} / add values / refuse unknown values when a deployment marker is present | refuse unknown values in deployed images |
| 3 | Global admin | keep standing / break-glass only / remove cross-tenant reach | break-glass only: purpose + ticket + expiry + second approver + tamper-evident audit event |
| 4 | `ADMIN_BOOTSTRAP_TOKEN` | keep / one-shot (self-disabling after first use) / remove from production | one-shot or remove; audit the **caller** |
| 5 | `BOOTSTRAP_TENANT_ADMINS` | keep / record approval + expiry / remove after onboarding | record approval + expiry; do not re-enable disabled memberships |
| 6 | Admin-grants-admin | keep / require second approver | second approver |
| 7 | Portfolio access (with GD-8) | none / anonymised, purpose-bound and audited for a named role | decide before touching the code |
| 8 | Staging | treat shared staging as production / remove the public literals entirely | remove the public literals; dev tokens only on developer machines |
| 9 | Deployment attestation | operations attests the deployed variables against the refusal list before each deploy | yes (template: governance matrix §4) |

Signature: PA-1 Decision ____ · Owner ____ · Second approver ____ · Date ____ — **UNSIGNED**
