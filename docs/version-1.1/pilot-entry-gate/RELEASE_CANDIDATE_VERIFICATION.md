# LPR-DIR-027 — Release Candidate Verification (Workstream 1)

Authorization-only verification of the certified Internal Release Candidate. No pilot is
executed.

## Verification

| Field | Value | Evidence |
|---|---|---|
| **IRC identifier** | **IRC-1** (LumenAI Version 1.1 Internal Release Candidate) | Certified under LPR-DIR-026 (PR #122) |
| **Release commit SHA** | `5c223450b4065011a52ff2dd244c6c5d91321dcc` (`5c22345`) | `git rev-parse` |
| **Still on the baseline?** | **YES** — `5c22345` is an ancestor of current `main` (`d1ab98b`, after #120 merged) | `git merge-base --is-ancestor 5c22345 origin/main` → true |
| **Build provenance** | Merge of PR #119 (SEC-C-01 hardening) into `main`; the **only** V1.1 application-code change. All other V1.1 merges are docs. `git describe` = `lumenai-v1.0.0-rc1-19-g5c22345` | LPR-DIR-026 MERGE_VERIFICATION.md |
| **Release manifest** | Schema head `e7b2f4a86c31` (no V1.1 migration); deps `requirements-lock.txt` sha256 `d96ae3a7…`; **no valid V1.1 tag** (`v1.1.0` stale/divergent) | LPR-DIR-026 RELEASE_CANDIDATE_MANIFEST.md |
| **Release integrity** | Real sha256 for source delta + dep manifests; **container digests NOT AVAILABLE** (no image built); fresh SBOM not regenerated (dep fingerprint pinned) | LPR-DIR-026 RELEASE_INTEGRITY_REPORT.md |

## Determination

**IRC-1 is verified and stable** at commit `5c22345`, confirmed still present on the
authorized baseline. Its provenance, manifest, and integrity are as certified under
LPR-DIR-026. This verification records **no new build** and makes **no production or
pilot claim** — it only confirms the artifact under evaluation for the entry gate.

**Caveat carried forward:** IRC-1 has **no container image or freshly generated SBOM**;
those exist only at an authorized tagged build. This is an operational-readiness gap
(Workstream 3), not a defect in the RC.
