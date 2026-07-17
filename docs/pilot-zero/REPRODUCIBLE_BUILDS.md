# Reproducible Builds — Pilot Zero

## The dependency chain (single source of truth)

```
backend/requirements.txt        # human-edited: DIRECT dependencies only
        │  (resolve + test)
        ▼
backend/requirements-lock.txt   # AUTHORITATIVE: exact pins, frozen from a
        │                       # fully green test environment (Py 3.11)
        ├──► CI (pilot-zero-gate.yml installs ONLY from the lock)
        └──► requirements.txt (root) — GENERATED copy of the lock;
             consumed unchanged by Dockerfile / docker/Dockerfile.api /
             docker/Dockerfile.worker (python:3.11-slim)
```

Frontend: `frontend/package-lock.json` is authoritative; CI and builds
use `npm ci` (never bare `npm install`).

## Change procedure (any backend dependency change)

1. Edit `backend/requirements.txt` (direct deps only, one entry per
   package).
2. Build a fresh Python 3.11 venv from it; run the **full** backend
   suite on SQLite and PostgreSQL.
3. Only from that green venv: `pip freeze | sort >
   backend/requirements-lock.txt`.
4. Copy the lock into root `requirements.txt` beneath its GENERATED
   header.
5. One PR carries the manifest edit + both regenerated files + the
   green gate. Lock changes without a green suite are rejected in
   review.

## Environment fingerprint (this lock's provenance)

* Python 3.11.15; 100 pinned packages; frozen 2026-07-17 from the
  environment in which the full suite passed (3,683 passed / 2 skipped
  on SQLite; PostgreSQL 16.13 suite green — see
  `docs/foundation/FOUNDATION_ACCEPTANCE.md`).
* `pip-audit` at freeze time: no known vulnerabilities.

## Known bounds (honest)

* The lock is a faithful freeze of the tested environment and therefore
  includes development/verification tooling present in it (`pytest`,
  `ruff`, `pip_audit` and their transitives). Runtime images built from
  it carry that tooling — reproducible, slightly larger than minimal. A
  separate slim runtime lock is deliberate follow-up work, not done yet.
* Pins are exact but not hash-locked; hash-locking (`--require-hashes`
  via pip-tools) is a candidate WS1 follow-up, noted not yet adopted.
* System-level reproducibility (OS packages such as `libzbar0`,
  PostgreSQL client tools) is governed by the Docker base images; local
  dev environments may vary — CI is the arbiter.
* Model-artifact reproducibility is separately governed by the training
  pipeline's seeded configuration and checksums
  (`docs/model-development/TRAINING_CONFIGURATION.md`); this document
  covers application builds.
