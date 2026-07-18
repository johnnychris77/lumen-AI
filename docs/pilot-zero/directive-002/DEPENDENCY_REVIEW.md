# LPZ-DIR-002 — Dependency Review (increment 2)

## Manifests present and their role

| File | Lines | Role | Authoritative? |
|---|---|---|---|
| `backend/requirements-lock.txt` | 100 | fully-pinned, tested backend lock (Py 3.11) | **YES (backend)** |
| `backend/requirements.txt` | 44 | direct/top-level backend deps (deduplicated) | input to the lock |
| root `requirements.txt` | 106 | generated from the lock (Docker/Render install target) | mirror of the lock |
| `frontend/package.json` | — | frontend manifest | **YES (frontend)** |
| `frontend/package-lock.json` | 77031 B | npm lockfile | **YES (frontend, resolved)** |

Which file each consumer uses:
* **Docker / Render** — root `requirements.txt` (generated from the lock), so
  images build exactly the tested set (fixed under WS1).
* **CI** — `.github/workflows/pilot-zero-gate.yml` installs the lock.
* **Developers** — `backend/requirements.txt` (direct deps) or the lock for an
  exact environment.
* **Frontend** — `npm ci` against `package-lock.json`.

## Findings

| Check | Method | Result |
|---|---|---|
| Duplicate manifests disagree? | line/content compare | Root `requirements.txt` is a superset of the lock (adds dev tooling); no *conflicting* version pins. |
| Duplicate dependency lines (e.g. `psycopg2-binary` ×3)? | `grep -c` | **Fixed under WS1** — now single. |
| Invalid / non-existent versions? | clean install (below) | None — clean install succeeds. |
| Unused packages? | not exhaustively pruned | Root manifest carries dev/audit tooling (`pytest`, `ruff`, `pip-audit`) — safe superset, not minimal. Recorded bound. |
| Obsolete packages? | `pip-audit` | No known-vulnerable versions. |
| Backend clean install | `pip install -r requirements-lock.txt` (CI) | succeeds (WS1 + gate workflow). |
| Frontend clean install + build | `npm ci` + `npm run build` | **2761 modules, built in 4.99s** (this increment). |
| Python vulnerabilities | `pip-audit -r requirements-lock.txt` | **No known vulnerabilities found**. |
| Frontend vulnerabilities | `npm audit` (WS1) | 0 vulnerabilities. |

## Known bounds (recorded, not hidden)

* Root `requirements.txt`, being generated from the full lock, includes
  development/audit tooling. A runtime-only slim lock is a documented follow-up
  (not a Directive 002 blocker).
* Backend SBOM component licenses are **undeclared** when generated from the
  requirements file (no PyPI metadata resolution) — see `SBOM_REPORT.md` for the
  license-enrichment follow-up.

## Disposition

Dependency manifests are **reproducible and non-conflicting**. F7 (WS1) remains
REMEDIATED and is re-verified here with a fresh frontend build and `pip-audit`.
