# LPR-DIR-014 — Supply Chain Security (Phase 3)

**Basis:** `pip-audit`, `npm audit`, `bandit`, manifest inspection, SBOM generation
at `f889d95`.

## Scanner results (measured)

| Tool | Command | Result |
|---|---|---|
| pip-audit | `pip-audit -r requirements.txt` | **No known vulnerabilities** |
| npm audit | `npm audit --omit=dev` (frontend) | **0 vulnerabilities** |
| bandit | `bandit -r backend/app` | 29 High (all **MD5 non-security**: PRNG seed/etag), 10 Med, 142 Low; SQL sites allowlisted `# nosec` |
| safety | (CI `security-baseline.yml`) | gated in CI |

CI runs `pip-audit`, `npm audit`, `safety`, `bandit`, and secret-scan
(`security-baseline.yml`, `security-hardening-validation.yml`) — supply-chain
scanning is **continuously gated**.

## SBOM
Generated with CycloneDX (`cyclonedx-py requirements requirements.txt`):
**`SBOM.cyclonedx.json`** (100 components) is committed alongside this review.

## Manifests / packages

| Manifest | Pinned | Installed by |
|---|---|---|
| `requirements.txt` (root) | **100/100** | Dockerfile (production image) — deterministic |
| `backend/requirements.txt` | **7/27** | CI (`ci.yml`) — mostly unpinned |

### SEC-SC-01 (MEDIUM) — divergent + partially-unpinned CI manifest (=DH-01)
The production image installs the fully-pinned root manifest, but CI installs a
mostly-unpinned `backend/requirements.txt` (incl. `cryptography`, `sqlalchemy`,
`uvicorn`, `httpx`, `pytest`, `ruff`). CI can validate against different — and
floating — versions than ship. Supply-chain determinism + "tests validate what
ships" gap. **Mitigation:** install the pinned production manifest in CI (or a
pinned superset).

## Outdated / duplicate / abandoned / license

- **Outdated:** no pinned dependency is flagged vulnerable by pip-audit; a routine
  freshness review is recommended but nothing is a known CVE.
- **Duplicate:** two Python manifests (SEC-SC-01); mainstream single-purpose deps
  otherwise.
- **Abandoned:** none surfaced; the stack is mainstream/maintained
  (FastAPI/SQLAlchemy/pydantic/alembic/cryptography/reportlab/boto3).
- **License:** no automated license scan is gated (SEC-SC-02, OBSERVATION). The
  stack is OSI-licensed (MIT/BSD/Apache/PSF); no GPL-viral runtime dep observed.

## Other supply-chain surfaces
- **Docker:** single pinned Python base; `--no-cache-dir` install (see INFRA for
  container-user finding).
- **GitHub Actions:** 11 workflows; actions not confirmed SHA-pinned (SEC-SC-03,
  OBSERVATION — recommend SHA-pinning + dependabot).
- **Terraform:** not present in repo (Helm/K8s/Compose used); no IaC drift scan.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| SEC-SC-01 | MEDIUM | CI installs mostly-unpinned `backend/requirements.txt` vs pinned prod manifest (=DH-01) |
| SEC-SC-02 | OBSERVATION | No gated license scan |
| SEC-SC-03 | OBSERVATION | GitHub Actions not SHA-pinned; no container-image CVE scan (add Trivy/Grype) |

**Positive:** 0 Python CVEs, 0 Node CVEs, production manifest fully pinned, scanners
already gated in CI, SBOM generated.
