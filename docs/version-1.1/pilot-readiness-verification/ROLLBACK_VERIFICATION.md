# ROLLBACK VERIFICATION — LPR-DIR-030 (Workstream 5)

**Scope:** Verify rollback capability — the coded rollback path **and** whether an executed
rollback drill with measured MTTR exists (blocker **OPS-DEP-02**, tracker **E-04**).

## 1. Artifact verification (independently re-inspected)
`.github/workflows/deploy.yml` implements a **fail-closed** rollback: on
`kubectl rollout status` timeout/failure, the workflow runs `kubectl rollout undo` and
surfaces the failure (it does not swallow it or report a false success).

**Artifact classification: VERIFIED** — the rollback verb is present, real, and correctly
triggered on deploy failure.

## 2. Execution verification (the operational question)
| Check | Result |
|---|---|
| An executed A→B→A rollback drill on a real cluster | **NONE** |
| Measured MTTR / rollback duration | **NONE** — never timed against a live target |
| Post-rollback smoke test proving service restored | **NONE** |
| Repeatable rollback (≥2 drills) | **NONE** |

**Execution classification: NOT VERIFIED** — no rollback has been performed; MTTR is
unmeasured.

## 3. Classification summary
| Item | Classification |
|---|---|
| Rollback path in workflow (`rollout undo` on failure) | **VERIFIED** (artifact) |
| Executed rollback drill (E-04 / OPS-DEP-02) | **NOT VERIFIED** |
| Measured MTTR | **NOT VERIFIED** |
| Post-rollback smoke evidence | **NOT VERIFIED** |

## 4. What would close the gap
A deploy A → deploy B → forced failure → `rollout undo` transcript with a **timestamped MTTR**
and a post-rollback `/health` 200 smoke log, repeated at least twice.

## 5. Determination
**Rollback *artifact* VERIFIED; rollback *execution* NOT VERIFIED.** Blocker **OPS-DEP-02
remains OPEN**. A coded `rollout undo` is not a performed, timed rollback drill.
