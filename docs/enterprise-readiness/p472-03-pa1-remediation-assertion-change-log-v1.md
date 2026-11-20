# P472-03 PA-1 Remediation — Assertion and Test Change Log (v1)

**PR #181 (DRAFT) · Issue #190 · PA-1 governance OPEN (unsigned).** This log lists every test change made by the
PA-1 remediation, separately from the fix, so that a non-author reviewer can judge each one. Nothing here is a
reviewer decision. All conversions are **author conversions** and stay release blockers until dispositioned.

Commits:

| SHA | Content | Application code? |
|---|---|---|
| `c2014ff` | Reproduction on SQLite + PostgreSQL; test **set-up** option `PA1_PG_ADMIN_URL`; RB-T38…T40 still strict-xfail and failing | no |
| `829f36a` | Canonical production determination and fail-closed gates; conversions and amendments below | **yes** |

Original tripwire text: `backend/tests/test_p472_03_batch8_pa1_env_gates.py` at `6b2a8d6`.

## 1. Tripwire conversions

| Tripwire | Test | Assertion line | Marker | Helper | Classification |
|---|---|---|---|---|---|
| RB-T38 (PA1-01) | `test_dev_tokens_are_inactive_whenever_any_production_signal_is_set` | **unchanged** `assert result["dev_token_admin"] is False` | removed | `_probe` **amended (A-1)** | conversion with amended helper |
| RB-T39 (PA1-02) | `test_demo_reset_is_not_reachable_with_the_public_token_in_production` | **unchanged** `assert result["demo_reset_public_token"] in (401, 403, 404)` | removed | `_probe` **amended (A-1)** | conversion with amended helper |
| RB-T40 (PA1-03) | `test_enterprise_jwt_shape_check_follows_every_production_signal` | **unchanged** | removed | A-1 has no effect: both configurations start | conversion, assertion and probe unchanged in substance |

Each marker is replaced by a comment that quotes the original `@_tripwire(...)` reason.

## 2. Amendments

### A-1 — `_probe` / `CHILD` in `test_p472_03_batch8_pa1_env_gates.py` (affects RB-T38, RB-T39 and the two controls)

* **Before (`6b2a8d6`).** The child process ran `import app.main` and the parent asserted
  `proc.returncode == 0`. The probe could only observe a gate inside a process that **started**.
* **Why it had to change.** The remediation makes both configurations **refuse to start** (`sys.exit("FATAL: …")`).
  That is the intended fail-closed behaviour. With the original helper, RB-T38 and RB-T39 now fail on
  `returncode == 0`, even though the gate they assert on is closed.
* **After (`829f36a`).** The child catches `SystemExit` from `import app.main` and records the refusal. It then
  evaluates the **same three expressions** at layer level:
  - `app.deps` is imported directly (the same `deps._DEV_ROLE_MAP` read);
  - `enterprise_auth._AUTH_ENV` is read the same way;
  - the demo router is mounted on a minimal FastAPI app over the same database, with the same request.
  When startup succeeds, the probe is byte-for-byte the original path (`TestClient(m.app)`). The refusal message is
  returned under `_startup`. `_probe` strips it, so the tripwires and `test_control_render_configuration_is_closed`
  compare exactly the original three keys.
* **Why this is not a weakening.**
  - The layer probe is strictly harder to pass than "the app did not start": the gate must be closed even inside
    a process that skipped `app.main`'s refusal.
  - Run against the pre-fix code (`c2014ff`), the amended tests still **fail** (kit variant `before/final`, both
    DBs), because nothing refuses to start there and the gates are open.
  - Startup refusal is pinned separately by `test_rb_t38_configuration_refuses_to_start` and
    `test_rb_t39_configuration_refuses_to_start`.
* **Reviewer must judge:** whether the layer-level probe is an acceptable stand-in for the original whole-app
  probe. The kit records the expected `after/original` failure as
  *"original probe requires app.main to start; startup is now refused"*.

### A-2 — set-up only: `PA1_PG_ADMIN_URL` (commit `c2014ff`, before the fix)

* Optional. When set, each probe gets a fresh PostgreSQL database that is dropped afterwards. Default stays SQLite.
* It changes no assertion and no marker. It was committed **before** the fix, and RB-T38…T40 were shown failing
  with it on both DBs (`evidence/p472-03-pa1-remediation/before-8bfcc9a/`).

### A-3 — `test_p472_03_batch2_remediation.py::test_development_tokens_do_not_exist_in_production` (source pin)

* Before: `'_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and _APP_ENV not in {"production", "prod"}' in source`. That line
  is the RB-T38 defect (`APP_ENV` only).
* After: `"_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and not _is_production()" in source`, plus a new pin for the call-time
  re-check `"if not _DEV_AUTH_ACTIVE or _is_production():"`. The map pin `"} if _DEV_AUTH_ACTIVE else {}"` is
  unchanged. The original line is quoted in a comment.
* Not a tripwire. The amendment is necessary because the pinned text was the defect. Behaviour is covered by
  RB-T38 and `test_p472_03_pa1_remediation.py`.

### A-4 — `test_p471_fail_closed_inference.py`: credentials in production-configured cases (set-up)

* Six cases set `APP_ENV=production` (or `prod`) at runtime and then authenticated with the **public dev token**
  (`Bearer dev-token`):
  - `TestStreamFrameRoute::test_route_never_returns_a_fabricated_finding`;
  - `TestStreamFrameRoute::test_production_configured_route_reports_unavailable[production]`;
  - `TestCVProviderFailsClosed::test_analyze_returns_explicit_unavailable[production]`;
  - `TestCVProviderFailsClosed::test_analyze_and_rank_does_not_rank_an_unevaluated_image`;
  - `TestCVProviderFailsClosed::test_video_analysis_is_unavailable_not_a_synthesized_timeline`;
  - `TestCVProviderFailsClosed::test_provider_info_reports_unavailable`.
  They passed only because the dev token kept working after a production signal appeared. That is exactly
  RB-T38/RB-T40.
* After the fix, the dev token is refused (401) once production is signalled. These cases now authenticate with a
  real member JWT. The role (`spd_manager`) is resolved server-side through the existing `_user_role` stub that
  the same file already uses. **Every assertion is unchanged.**
* `test_route_never_returns_a_fabricated_finding` gains `assert res.status_code != 401`. Without it, a 401 would
  make its `if res.status_code == 200:` body vacuous, so it now has to reach the route. This only strengthens the
  test.
* The non-production parameters (`research`, `None`) still use the dev token, as before.

## 3. New tests (not amendments)

| File | Tests | Purpose |
|---|---|---|
| `test_p472_03_batch8_pa1_env_gates.py` | `test_rb_t38_configuration_refuses_to_start`, `test_rb_t39_configuration_refuses_to_start`, `test_rb_t40_configurations_start` | pin the startup outcome for each converted configuration |
| `test_p472_03_pa1_remediation.py` | 53 | determination matrix (any signal, case, whitespace, conflicts); startup refusal list (conflict, AUTH_MODE unset / dev / other, `ALLOW_DEV_AUTH_IN_PROD` not honoured, ENABLE_DEV_AUTH, DEMO_MODE, weak SECRET_KEY); runtime gates under a production signal set **after import** (dev-token map, legacy `get_current_user`, three demo-token readers, `tenant_authz`, enterprise dev mode, JWT-shape check, portfolio literal token, demo reset refused **and nothing deleted**, `Settings.is_production`); dev workflows preserved outside production; OIDC and signed per-user JWT preserved in production; PA1-04 portfolio role / email grants still inert; environment module grants nothing |

## 4. Unchanged on purpose

- `test_control_render_configuration_is_closed` keeps its exact expected dict (`403` for the demo reset).
- `test_control_unset_auth_mode_in_production_refuses_to_start`: the refusal message still contains
  `AUTH_MODE is not set`.
- `test_directive_002_tenant_context.py::TestDevAuthDisabledInProduction`: unchanged and passing.
- `test_p14_recommendations.py::TestDemoMode` (DEMO_MODE outside production): unchanged and passing.
