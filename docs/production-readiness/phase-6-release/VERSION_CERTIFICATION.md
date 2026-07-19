# LPR-DIR-017 — Version Certification (Phase 6)

Certifies the versioned state of the LumenAI v1.0 Release Candidate baseline.

| Item | Value / Verdict |
|---|---|
| Product | LumenAI Version 1.0 |
| Release candidate | **RC1** |
| Certified baseline commit | `bd94bc5` (main, post-Phase-2 merge) + this Phase-6 certification commit |
| Repository state | frozen architecture; documentation-only certification (no code change) |
| Suggested Git tag | **`lumenai-v1.0.0-rc1`** (annotated) |
| Release notes | `RELEASE_NOTES.md`, `VERSION_1_0.md` present |
| Artifact integrity | GHCR image release is checksummed by digest; app images built by `release-ghcr.yml` on `v*` tags |
| SBOM | CycloneDX SBOM (100 components) generated in Phase 3 (`docs/production-readiness/phase-3-security/SBOM.cyclonedx.json`, in PR #111) |
| Evidence completeness | Phases 1–5 deliverable sets complete (Phase 1–2 merged to main; Phase 3–5 in open PRs #111/#112/#113) |

## ⚠️ Tagging safety notice (important)
`release-ghcr.yml` triggers on **`push: tags: - 'v*'`** and **publishes production
container images to GHCR**. Therefore:
- The suggested tag **`lumenai-v1.0.0-rc1`** does **NOT** match `v*` → pushing it does
  **not** publish images (safe as a certification marker).
- A **`v1.0.0-rc1`** (or any `v*`) tag **WOULD publish production images** — this is a
  release action and **must NOT be pushed until SEC-C-01 is closed** and production
  is authorized.

This certification therefore recommends creating the annotated tag
`lumenai-v1.0.0-rc1` on the certification commit as a **frozen RC baseline marker for
the hardening cycle**, and **withholding any `v*` release tag** until the blocking
conditions close.

## Evidence completeness note (honest)
The certification synthesizes Phases 1–5. Phase 1–2 deliverables are merged to `main`;
**Phase 3 (security), Phase 4 (performance), Phase 5 (operations) live in open draft
PRs #111, #112, #113** and are not yet on `main`. The RC baseline is therefore
"certified pending merge of #111–#113"; the executive decision accounts for this.

## Certification statement
**Version: CERTIFIED as RC1 baseline (documentation/marker only).** The annotated
`lumenai-v1.0.0-rc1` tag may mark the baseline; **no `v*` release tag and no GHCR
publish is authorized** until the blocking conditions close.
