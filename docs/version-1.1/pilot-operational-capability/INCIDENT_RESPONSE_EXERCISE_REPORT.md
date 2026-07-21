# INCIDENT RESPONSE EXERCISE REPORT — LPR-DIR-031 / WP-7

**Commit:** `4299c40` · **Operator:** automated · **Attempt timestamp:** 2026-07-20T02:33Z.
**Precondition:** a running managed environment to perturb — **not provisionable here**.

## 1. Objective
Conduct tabletop + controlled operational exercises (database unavailable, application
restart, deployment failure); record timeline, actions, outcome.

## 2. Controlled operational exercises — NOT EXECUTED
No live environment exists to induce a real fault against, so no operational IR exercise with
a measured timeline was performed.
| Scenario | Live exercise | Value |
|---|---|---|
| Database unavailable | **not executed** | no live DB to stop |
| Application restart | **not executed** | no deployed app to restart |
| Deployment failure | **not executed** | no cluster to fail a rollout on |

**No IR timeline is fabricated.**

## 3. Tabletop exercise — CONDUCTED (documentation-level, honestly scoped)
Using the validated runbooks (DIR-030 `RUNBOOK_VALIDATION_REPORT.md`), the following tabletop
walk-throughs are recorded as **planned** procedures — a paper exercise, not an operational drill:
| Scenario | Runbook path | Expected operator actions | Expected outcome |
|---|---|---|---|
| DB unavailable | Runbook §3/§4/§6 | detect (health 5xx) → failover/restore per Data Recovery → validate | service restored; RTO measured *(only in a live drill)* |
| App restart | Runbook §4 | restart deploy → `rollout status` → smoke `/health` | healthy instance |
| Deploy failure | Runbook §1/§2 | `rollout status` fails → auto `rollout undo` → smoke | prior good version restored |

The tabletop confirms the procedures are coherent and map to real automation; it does **not**
produce operational evidence (no delivered alert, no measured recovery).

## 4. Exact procedure that WOULD produce the operational evidence
```
# on a live environment, per scenario, record t0/actions/t_recovered:
kubectl -n lumenai scale deploy/postgres --replicas=0    # DB unavailable
kubectl -n lumenai rollout restart deploy/lumenai        # app restart
#  deploy a knowingly-bad image → observe rollout failure → auto-rollback
# capture: alert receipt, operator actions with timestamps, recovery time, post-smoke
```

## 5. Classification
| Item | Status |
|---|---|
| Controlled operational IR exercise (OPS-INC-01) | **NOT EXECUTED / OPEN** |
| Tabletop walk-through (paper) | **CONDUCTED (documentation only)** |
