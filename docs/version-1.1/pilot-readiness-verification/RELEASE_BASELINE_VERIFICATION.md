# RELEASE BASELINE VERIFICATION — LPR-DIR-030 (Workstream 1)

**Directive:** LPR-DIR-030 — Pilot Infrastructure and Operational Capability Verification.
**Standard:** implementation ≠ verification; documentation ≠ operational evidence;
configuration ≠ operational capability. Only independently reproduced evidence moves a
classification.

## 1. What was verified
That the artifacts under verification are built **only from merged code plus the
DIR-029 engineering delta**, and that the internal release candidate (IRC-1) baseline is
an ancestor of the branch being verified — i.e., no unmerged app/frontend behavior has
been smuggled into the verification baseline.

## 2. Objective evidence (independently reproduced this pass)
| Check | Command | Result |
|---|---|---|
| Verification branch HEAD | `git rev-parse HEAD` | `b96971a` |
| IRC-1 baseline is an ancestor | `git merge-base --is-ancestor 5c22345 HEAD` | **TRUE** (5c22345 is an ancestor) |
| Delta scope vs `origin/main` | `git diff --stat origin/main...HEAD` | 43 files, **+2318 / −17** |
| **Application-code delta** vs `origin/main` | `git diff --stat origin/main...HEAD -- backend/app frontend/src` | **EMPTY — zero delta** |
| Delta composition | (same) | docs under `docs/version-1.1/**`, `.github/workflows/deploy.yml`, `scripts/pilot-verification/verify_capabilities.py` |

## 3. Interpretation
- The branch under verification carries **no runtime application or frontend change** over
  merged `main`. Every code change in scope is (a) a CI/CD workflow artifact
  (`deploy.yml`) or (b) a self-contained verification harness script — neither of which
  alters shipped product behavior.
- IRC-1 (`5c22345`) is a genuine ancestor, so the release baseline the verification speaks
  to is the merged internal release candidate, not a feature-branch snapshot.
- **Consequence:** the verification cannot and does not claim any *new product capability*.
  It verifies engineering *techniques* and a deploy *artifact* only.

## 4. Classification
| Item | Classification |
|---|---|
| Verification baseline == IRC-1 lineage (merged code) | **VERIFIED** |
| No unmerged app/frontend behavior in scope | **VERIFIED** |
| New product/clinical capability introduced | **NOT APPLICABLE** (none introduced by design) |

## 5. Determination
**Release baseline VERIFIED.** The verification operates on merged code (IRC-1 ancestor)
plus a docs + workflow + harness delta with **zero application-code change**. This is the
correct, honest baseline for an infrastructure/operational verification and prevents any
feature-branch capability from being mistaken for verified product behavior.
