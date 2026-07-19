# LPR-DIR-026 — Baseline Security Verification (Workstream 3)

**Re-evaluated on the merged baseline only** (`main @ 5c22345`). Feature branches were NOT
used. Findings are graded by whether the *merged code on the RC* closes them — not by
feature-branch CI.

## Method

- Code inspection of the RC tree (`git checkout -B … origin/main` → tip `5c22345`).
- The release-blocker register merged into the baseline (`docs/version-1.1/RELEASE_BLOCKER_REGISTER.md`, shipped by PR #119).
- Direct verification of the SEC-C-01 fix on `main` (below).

## CRITICAL

| ID | Finding | Status on RC | Evidence (merged baseline) |
|---|---|---|---|
| **SEC-C-01** | External + billing webhooks failed OPEN on missing secret; tenant derived from attacker-controllable input → unauthenticated cross-tenant injection. | **✅ CLOSED (code)** | On `main`: `integrations.py` reads `secret=os.getenv("WEBHOOK_SECRET_{SYS}")` → **503** if unset; HMAC always verified with `hmac.compare_digest` → **401** on mismatch; tenant from server-side `WEBHOOK_TENANT_{SYS}` (**503** if unset); the `X-Tenant-Id` header is no longer read. `billing.py::stripe_webhook` requires `STRIPE_WEBHOOK_SECRET` (**503** if unset), **400** on invalid signature; only signature-verified payload metadata is trusted. Fix commit `f291186` ∈ RC (`git merge-base --is-ancestor` → true). Corrected tests on `main` assert 503/401/400 and prove server-bound tenant wins over attacker `X-Tenant-Id`. |

**CRITICAL open on the RC: 0.**

## HIGH

Re-verified on the RC; none closed by merged code beyond the partial startup mitigations
already on `main`.

| ID | Finding | Status on RC | Class |
|---|---|---|---|
| SEC-H-01 | Hardcoded HS256 secret fallbacks in `core/config.py` / `auth_simple.py` | **OPEN (PARTIAL)** — prod guard `sys.exit`s on default `SECRET_KEY` in `main.py`; dev fallbacks still present | Must Fix Before Production |
| SEC-H-02 | No fail-closed startup secret validation; `Settings.validate()` omits `SECRET_KEY`/webhook secrets | **OPEN (PARTIAL)** — prod SECRET_KEY + AUTH_MODE guards at startup; webhook secrets now enforced per-request (fail-closed) but not in `Settings.validate()` | Must Fix Before Production |
| PERF-07 | No production/representative load test executed | **OPEN (infra)** | Must Fix Before Production |
| SCAL-01 | Single Postgres SPOF + single uvicorn worker/pod | **OPEN (infra)** | Must Fix Before Production |
| RES-01 | In-process APScheduler duplicates across replicas | **OPEN (infra)** | Must Fix Before Production |
| OPS-INC-01 | No incident-response/on-call + no alerting | **OPEN (infra/process)** | Must Fix Before Production |
| OPS-DEP-01 | Production deploy is a stub (`deploy.yml` echoes kubectl) | **OPEN (infra)** | Must Fix Before Production |
| OPS-DEP-02 | No executed rollback drill | **OPEN (infra)** | Must Fix Before Production |

**HIGH open on the RC: 8** (2 partially mitigated in code; 6 infra/process, not closable
from a repository).

## MEDIUM / LOW

| Tier | Items | Status |
|---|---|---|
| MAJOR/MEDIUM | AR-16..18 (audit atomicity, dataset-freeze enforcement, dedup TOCTOU) | **OPEN** — targeted code items, not pilot-blocking; no fix merged in V1.1. |
| LOW | Stale docstring at `integrations.py:796` ("validates HMAC if secret set") no longer matches the fail-closed behavior | **OPEN (cosmetic)** — documentation nit only; the code is fail-closed. Not a security defect. Deliberately not patched here (this directive integrates merged code; it does not modify RC source). |
| GATE (real-world) | No pilot site, trained operators, imaging equipment, managed environment, or real facility images | **OPEN (real-world)** — cannot be satisfied from a repository. |

## Determination

On the merged baseline `main @ 5c22345`:

- **1 CRITICAL (SEC-C-01) → CLOSED in code.**
- **8 HIGH → OPEN** (SEC-H-01/02 partially mitigated; the remaining six are infrastructure
  or real-world and **cannot be truthfully closed from this repository**).
- MEDIUM/LOW → OPEN, non-blocking.

The RC clears the CRITICAL security gate. It does **not** clear the HIGH production gate.
