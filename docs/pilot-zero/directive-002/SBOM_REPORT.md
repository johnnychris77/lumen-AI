# LPZ-DIR-002 — Software Bill of Materials (SBOM) Report

## Tool

* **CycloneDX for Python** (`cyclonedx-bom` 7.3.0 / `cyclonedx-python-lib`
  11.11.0), already present in the environment — no new dependency introduced.

## Backend SBOM

* **Command (exact):**
  ```bash
  cd backend && cyclonedx-py requirements requirements-lock.txt \
      --output-format JSON > \
      ../docs/pilot-zero/directive-002/sbom/backend-sbom.cdx.json
  ```
* **Source manifest:** `backend/requirements-lock.txt` (the authoritative,
  tested lock — so the SBOM describes exactly what runs).
* **Output:** `docs/pilot-zero/directive-002/sbom/backend-sbom.cdx.json`
* **Format:** CycloneDX 1.6 (JSON)
* **Components:** **100** (matches the 100 pinned packages)
* **Known vulnerabilities:** `pip-audit -r requirements-lock.txt` →
  **No known vulnerabilities found** (2026-07-18).

## Frontend SBOM

* The frontend `package-lock.json` is the resolved dependency graph and serves
  as the frontend BOM input. `npm audit` (WS1) reported **0 vulnerabilities**.
  A CycloneDX frontend SBOM (`@cyclonedx/cyclonedx-npm`) is a documented
  follow-up — the npm CLI SBOM tool is not currently installed and adding it is
  outside this increment's scope.

## Known limitation (honest)

* Component **licenses are undeclared** in the requirements-based backend SBOM:
  generating from a requirements file does not resolve PyPI license metadata, so
  every component currently shows no license. Enriching licenses requires the
  environment-based generator (`cyclonedx-py environment`, which reads installed
  package metadata) and is a recommended follow-up. Component **name + version +
  purl** are fully populated, which is sufficient for vulnerability correlation.

## Regeneration

The SBOM is a committed artifact. Regenerate it with the exact command above
whenever `requirements-lock.txt` changes; wire it into the Pilot Zero gate as a
build step in a follow-up.
