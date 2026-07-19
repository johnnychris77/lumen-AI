# LPR-DIR-013 — Dependency Hygiene Report (Phase 2)

**Basis:** `pip-audit`, `npm audit`, manifest inspection, Dockerfile + CI grep.
Baseline `c9797b2`.

## Security advisories (measured)

| Ecosystem | Command | Result |
|---|---|---|
| Python | `pip-audit -r requirements.txt` | **No known vulnerabilities found** |
| Node (prod) | `npm audit --omit=dev` | **found 0 vulnerabilities** |

Both ecosystems are clean of known advisories at baseline. `pip-audit`, `npm audit`,
and `safety` also run inside CI (`security-baseline.yml`,
`security-hardening-validation.yml`), so this is continuously gated.

## Python packages

| Manifest | Lines | Pinned (`==`) | Installed by |
|---|---|---|---|
| `requirements.txt` (root) | 100 deps | **100 / 100** | **Dockerfile** (production image) |
| `backend/requirements.txt` | 27 deps | **7 / 27** | **CI** (`ci.yml`) |

**Finding DH-01 (MAJOR) — divergent, partially-unpinned dependency manifests.**
Two Python manifests exist with different contents, and they are installed by
different environments:
- The **production image** (`Dockerfile`) installs the **fully-pinned** root
  `requirements.txt` — deterministic and reproducible. ✅
- **CI** (`ci.yml`) installs `backend/requirements.txt`, of which only **7 of 27**
  entries are pinned; 20 float (incl. `sqlalchemy`, `uvicorn`, `cryptography`,
  `httpx`, `pytest`, `ruff`, `alembic`, `boto3`).

Consequences: (1) CI can validate against **different dependency versions than
ship in the image**, weakening the "tests validate what ships" guarantee and
introducing non-determinism into the pipeline; (2) two manifests can drift.
Recommendation (Phase 2): make the CI manifest a pinned superset of — or identical
to — the production manifest, or install the same `requirements.txt` in both.
This is the single most material dependency-hygiene item.

## Duplicate / unused packages

- **Duplicate manifests** (DH-01) are the main duplication.
- No automated unused-import-package analysis is CI-gated. Spot review shows the
  root manifest is coherent (FastAPI/SQLAlchemy/alembic/boto3/reportlab/openpyxl/
  cryptography stack matching used features). A formal unused-dependency scan
  (e.g. `deptry`/`pip-check`) is recommended for a later phase (DH-04, MINOR).

## Node packages

- `npm audit --omit=dev` clean. Frontend is Vite/React/TS (224 source files).
- Dev vs prod separation exists (`--omit=dev` succeeds). No advisory action needed.

## Docker images

- `Dockerfile` uses a single pinned Python base and installs the pinned root
  manifest with `--no-cache-dir`. Compose/Helm/K8s manifests exist (Phase 1
  inventory). No image-scan gate identified in CI (DH-05, MINOR — recommend adding
  a container-image CVE scan such as Trivy/Grype in a later phase).

## GitHub Actions

- 11 workflows present. Actions pin to marketplace actions; a formal
  action-SHA-pinning / `dependabot` policy for Actions was not confirmed
  (DH-06, OBSERVATION — recommend pinning action versions by SHA).

## Development dependencies

- Test/lint tooling (`pytest`, `ruff`) appears in both manifests. `bandit`/`safety`
  are invoked in CI but were **not** found installed in the base venv (installed
  ad-hoc for this review) — recommend adding them explicitly to a dev-requirements
  manifest so local runs match CI (DH-07, MINOR).

## License issues

- No license scan is currently gated. The stack is mainstream OSI-licensed
  (MIT/BSD/Apache/PSF); no GPL-viral runtime dependency was observed in the root
  manifest. A formal license scan is recommended for a later phase (DH-08,
  OBSERVATION) — not a blocker.

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| DH-01 | MAJOR | CI installs mostly-unpinned `backend/requirements.txt`; prod image installs pinned `requirements.txt` — divergence + non-determinism |
| DH-04 | MINOR | No unused-dependency scan gated |
| DH-05 | MINOR | No container-image CVE scan gated |
| DH-06 | OBSERVATION | GitHub Actions not SHA-pinned / no dependabot policy confirmed |
| DH-07 | MINOR | bandit/safety not in a committed dev-requirements manifest |
| DH-08 | OBSERVATION | No automated license scan |

**Positives:** 0 Python CVEs, 0 Node CVEs, production manifest fully pinned,
security scanners already in CI.
