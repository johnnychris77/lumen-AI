# P472-03 PA-1 Remediation — Review Packets RB-T38…RB-T40 (v1)

**PR #181 (DRAFT) · Issue #190 · PA-1 UNSIGNED.** Generated from the review kit
(`backend/scripts/p472_03_tripwire_review_kit.py report`). The source data is
`evidence/p472-03-pa1-remediation/kit/{sqlite,postgres}/kit-results-*.json`: **12/12 variants matched expectation on
SQLite and 12/12 on PostgreSQL 16.15.** These packets supersede the RB-T38…T40 sections of
`p472-03-batch8-tripwire-review-packets-generated-v1.md` (preserved). Every reviewer field is **UNASSIGNED**; the
author has filled none.

## What the reviewer should check (beyond the kit table)

1. **A-1 (RB-T38, RB-T39).** Is the layer-level probe an acceptable stand-in for the original whole-app probe once
   startup refuses? See `p472-03-pa1-remediation-assertion-change-log-v1.md`. `before/final` failing on both DBs
   shows the amended helper still detects the defect.
2. **One determination.** `backend/app/core/environment.py::determine_environment` / `is_production`. Every reader:
   - `main.py` (startup refusal, HSTS, OpenAPI);
   - `deps.py` (`_DEV_AUTH_ACTIVE`, `dev_token_role`);
   - `auth/__init__.py`, `tenant_authz.py`, `enterprise_access_control.py` (dev and demo tokens);
   - `enterprise_auth.py` (`is_demo_mode`, `_require_dev_auth_context`, `_AUTH_ENV`, `require_enterprise_auth`);
   - `routes/demo.py`, `portfolio_authz.py`, `config.py`, `routers/auth_simple.py`, `routers/users.py`,
     `core/cors.py`.
   Search for any remaining `APP_ENV` / `ENVIRONMENT` / `DEMO_MODE` reader that grants access.
3. **No new privileged pathway.**
   - `portfolio_authz` role/email keys are unchanged (PA1-04).
   - No membership, role or administrator is created.
   - The environment module imports no model and no session (pinned by `TestNoNewPrivilegedPathway`).
4. **Legitimate authentication preserved.**
   - OIDC passes the production shape check and maps verified claims (header tenant ignored).
   - A signed per-user JWT still authenticates in production.
   - Development and demo workflows are unchanged outside production.
5. **Contract change.** `AUTH_MODE=dev` + `ALLOW_DEV_AUTH_IN_PROD=true` now refuses to start (R-PA1-CONTRACT).
   PA-1 must ratify this.

### RB-T38 — PA1-01 dev tokens active with ENVIRONMENT=production, APP_ENV unset
| Field | Value |
|---|---|
| Test | `tests/test_p472_03_batch8_pa1_env_gates.py::test_dev_tokens_are_inactive_whenever_any_production_signal_is_set` |
| Before (code) | `c2014ff` |
| Original assertions | `6b2a8d6` (marked xfail) |
| Converted in | `829f36a` |
| After (code under review) | `829f36a230` |
| Governance dependency | PA-1 |
| Reviewer note | **ASSERTION LINE UNCHANGED; shared probe helper AMENDED (A-1): startup is now refused, so the probe evaluates the same gate at layer level. Reviewer must judge the helper change** |
| Assertion change | unchanged (AST-identical body; only decorators differ) |
| Same-tenant controls | `test_control_render_configuration_is_closed`, `test_control_unset_auth_mode_in_production_refuses_to_start`, `test_rb_t38_configuration_refuses_to_start`, `test_rb_t39_configuration_refuses_to_start`, `test_rb_t40_configurations_start` |

| DB | Variant | Expected | Author run | Message (first line) |
|---|---|---|---|---|
| postgres | before/final | failed | **failed** | assert True is False |
| postgres | before/original | failed | **failed** | assert True is False |
| postgres | after/final | passed | **passed** |  |
| postgres | after/original | failed (original probe requires app.main to start; startup is now refused, PA-1 A-1) | **failed** | AssertionError: FATAL: refusing to start (production configuration check): ENABLE_DEV_AUTH is enabled in a production environment; developme |
| sqlite | before/final | failed | **failed** | assert True is False |
| sqlite | before/original | failed | **failed** | assert True is False |
| sqlite | after/final | passed | **passed** |  |
| sqlite | after/original | failed (original probe requires app.main to start; startup is now refused, PA-1 A-1) | **failed** | AssertionError: FATAL: refusing to start (production configuration check): ENABLE_DEV_AUTH is enabled in a production environment; developme |

Command: `python backend/scripts/p472_03_tripwire_review_kit.py run --ids RB-T38 --db sqlite --out <dir>`

| Reviewer field | Value |
|---|---|
| Reviewer (name, affiliation) | **UNASSIGNED** |
| Independence statement (not an author of the change) | — |
| Commands run / evidence link | — |
| Authorization predicate inspected (file:line) | — |
| Date | — |
| Disposition (ACCEPT-CONVERSION / REJECT-CONVERSION / ACCEPT-RISK + owner / PENDING) | **PENDING** |

### RB-T39 — PA1-02 DEMO_MODE public dev-token on destructive /api/demo/reset in production
| Field | Value |
|---|---|
| Test | `tests/test_p472_03_batch8_pa1_env_gates.py::test_demo_reset_is_not_reachable_with_the_public_token_in_production` |
| Before (code) | `c2014ff` |
| Original assertions | `6b2a8d6` (marked xfail) |
| Converted in | `829f36a` |
| After (code under review) | `829f36a230` |
| Governance dependency | PA-1 |
| Reviewer note | **ASSERTION LINE UNCHANGED; shared probe helper AMENDED (A-1): startup is now refused, so the probe evaluates the same gate at layer level. Reviewer must judge the helper change** |
| Assertion change | unchanged (AST-identical body; only decorators differ) |
| Same-tenant controls | `test_control_render_configuration_is_closed`, `test_control_unset_auth_mode_in_production_refuses_to_start`, `test_rb_t38_configuration_refuses_to_start`, `test_rb_t39_configuration_refuses_to_start`, `test_rb_t40_configurations_start` |

| DB | Variant | Expected | Author run | Message (first line) |
|---|---|---|---|---|
| postgres | before/final | failed | **failed** | assert 200 in (401, 403, 404) |
| postgres | before/original | failed | **failed** | assert 200 in (401, 403, 404) |
| postgres | after/final | passed | **passed** |  |
| postgres | after/original | failed (original probe requires app.main to start; startup is now refused, PA-1 A-1) | **failed** | AssertionError: FATAL: refusing to start (production configuration check): DEMO_MODE is enabled in a production environment; the demo routes |
| sqlite | before/final | failed | **failed** | assert 200 in (401, 403, 404) |
| sqlite | before/original | failed | **failed** | assert 200 in (401, 403, 404) |
| sqlite | after/final | passed | **passed** |  |
| sqlite | after/original | failed (original probe requires app.main to start; startup is now refused, PA-1 A-1) | **failed** | AssertionError: FATAL: refusing to start (production configuration check): DEMO_MODE is enabled in a production environment; the demo routes |

Command: `python backend/scripts/p472_03_tripwire_review_kit.py run --ids RB-T39 --db sqlite --out <dir>`

| Reviewer field | Value |
|---|---|
| Reviewer (name, affiliation) | **UNASSIGNED** |
| Independence statement (not an author of the change) | — |
| Commands run / evidence link | — |
| Authorization predicate inspected (file:line) | — |
| Date | — |
| Disposition (ACCEPT-CONVERSION / REJECT-CONVERSION / ACCEPT-RISK + owner / PENDING) | **PENDING** |

### RB-T40 — PA1-03 enterprise JWT-shape check ignores APP_ENV / is case-sensitive
| Field | Value |
|---|---|
| Test | `tests/test_p472_03_batch8_pa1_env_gates.py::test_enterprise_jwt_shape_check_follows_every_production_signal` |
| Before (code) | `c2014ff` |
| Original assertions | `6b2a8d6` (marked xfail) |
| Converted in | `829f36a` |
| After (code under review) | `829f36a230` |
| Governance dependency | PA-1 |
| Reviewer note | **assertion and probe unchanged in substance** |
| Assertion change | unchanged (AST-identical body; only decorators differ) |
| Same-tenant controls | `test_control_render_configuration_is_closed`, `test_control_unset_auth_mode_in_production_refuses_to_start`, `test_rb_t38_configuration_refuses_to_start`, `test_rb_t39_configuration_refuses_to_start`, `test_rb_t40_configurations_start` |

| DB | Variant | Expected | Author run | Message (first line) |
|---|---|---|---|---|
| postgres | before/final | failed | **failed** | AssertionError: {'APP_ENV': 'production', 'AUTH_MODE': 'oidc'} |
| postgres | before/original | failed | **failed** | AssertionError: {'APP_ENV': 'production', 'AUTH_MODE': 'oidc'} |
| postgres | after/final | passed | **passed** |  |
| postgres | after/original | passed | **passed** |  |
| sqlite | before/final | failed | **failed** | AssertionError: {'APP_ENV': 'production', 'AUTH_MODE': 'oidc'} |
| sqlite | before/original | failed | **failed** | AssertionError: {'APP_ENV': 'production', 'AUTH_MODE': 'oidc'} |
| sqlite | after/final | passed | **passed** |  |
| sqlite | after/original | passed | **passed** |  |

Command: `python backend/scripts/p472_03_tripwire_review_kit.py run --ids RB-T40 --db sqlite --out <dir>`

| Reviewer field | Value |
|---|---|
| Reviewer (name, affiliation) | **UNASSIGNED** |
| Independence statement (not an author of the change) | — |
| Commands run / evidence link | — |
| Authorization predicate inspected (file:line) | — |
| Date | — |
| Disposition (ACCEPT-CONVERSION / REJECT-CONVERSION / ACCEPT-RISK + owner / PENDING) | **PENDING** |
