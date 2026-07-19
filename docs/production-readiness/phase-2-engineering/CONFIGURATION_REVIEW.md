# LPR-DIR-013 — Configuration Review (Phase 2)

**Basis:** inspection of `app/config.py`, env-access grep, secrets handling review.
Baseline `c9797b2`.

## Environment variables (measured)

| Metric | Value |
|---|---|
| `os.getenv` / `os.environ` call sites | **215** |
| Files touching env directly | **58** |
| Env reads inside `app/config.py` | 16 |
| Env reads **bypassing** central config | **~199** |

`app/config.py` defines a proper centralized, **frozen** `Settings` dataclass with
typed helpers (`_bool_env`, `_int_env`) and documented fields (app env, DB URL,
dev-auth toggle, SMTP, scheduler intervals, artifact roots, enterprise
audit/RBAC toggles, coverage-gate flag, etc.). This is the right pattern.

## Finding CFG-01 (MAJOR) — configuration sprawl

Despite the central `Settings`, ~199 of 215 env reads happen via **direct
`os.getenv`** scattered across 58 modules rather than through `Settings`. This
means:
- configuration is **not auditable from one place** (no single source of truth for
  "what env vars does this service consume?");
- typing/defaults/validation applied in `config.py` are **bypassed** by ad-hoc
  reads;
- it is the same class of gap the Phase 1 review flagged for webhook secrets
  (I-05 / AR-15): env-driven behavior with **no startup validation**.

Recommendation (Phase 3): route configuration through `Settings` (extend it with
the remaining keys), and add a startup validation step that fails closed when a
required production secret/URL is missing. This dovetails with the Phase 1 AR-15
remediation (require webhook signing secrets at startup).

## Feature flags

- Flags are env-driven booleans surfaced through `Settings`
  (`enable_dev_auth`, `enable_enterprise_audit`, `enable_enterprise_rbac`,
  `require_full_coverage_before_final_decision`, …) with documented defaults and
  safe (non-blocking / off) defaults. This is good practice.
- Flags read directly via `os.getenv` elsewhere fold into CFG-01.

## Configuration duplication

- **Two dependency manifests** (`requirements.txt` vs `backend/requirements.txt`)
  are the main config-artifact duplication — see DH-01 (MAJOR).
- Multiple `docker-compose.*.yml` variants (prod/reset/example) exist; these are
  intentional environment variants, not duplication (OBSERVATION CFG-02).

## Hard-coded values

- `bandit` flagged `B104` (bind-all-interfaces) in `cv/image_validator.py` and
  `B108` (hardcoded tmp dir) in `cv/image_store.py`. Inspection: these are
  default/constant values in CV utility code, not secrets. Recommend making the
  bind host and temp root configurable via `Settings` (CFG-03, MINOR).
- No hard-coded credentials were found in application code (see secrets below).

## Secrets handling

- **Positive / policy-aligned:** secret API keys are issued once via
  `secrets.token_urlsafe` and stored as **SHA-256 hash only** (never retrievable) —
  consistent with the project's non-negotiable secret policy. Admin seed password
  is generated at runtime and printed once with `# noqa` (not committed).
- `pip-audit`/`npm audit`/secret-scan run in CI; **secret-scan is gated** and no
  committed secret surfaced (Phase 1 + CI green).
- **Gap (carryover, not new):** no startup validation that required secrets
  (webhook signing, SMTP, DB) are present — folded into CFG-01 and Phase 1 AR-15.

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| CFG-01 | MAJOR | Config sprawl — ~199/215 env reads bypass central `Settings`; no startup validation of required secrets |
| CFG-03 | MINOR | Hard-coded bind host / tmp dir in CV utilities should be config-driven |
| CFG-02 | OBSERVATION | Multiple compose variants (intentional, not duplication) |

**Positives:** central frozen `Settings` with typed helpers and safe-default flags;
SHA-256-only secret storage; secret-scan gated in CI; no committed credentials.
