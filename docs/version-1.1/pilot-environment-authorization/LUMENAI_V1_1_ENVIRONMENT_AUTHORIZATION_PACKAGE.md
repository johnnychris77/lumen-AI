# LumenAI — Version 1.1 Environment Authorization Package
## LPR-DIR-031A — Master Index

**Purpose:** convert **RR-10** (from DIR-031 — "the execution context cannot provision a
managed environment") into an actionable, signable authorization. This package **authorizes
nothing on its own**; it is the request + specification + requirements + budget frame +
acceptance criteria + an unsigned decision record.
**Commit:** `61b96c0` · **Program state at authorship:** DIR-031 INCOMPLETE, **Pilot Entry
DENIED**, 0/23 pilot gates VERIFIED. Unchanged by this package.

## 1. Why this package exists
Every remaining operational Pilot-Entry blocker (SCAL-01, OPS-DEP-01/02, OPS-INC-01, DR, E-02)
depends on one external thing: a **provisioned managed environment + scoped credentials**.
DIR-031 proved the sandbox cannot self-provision it. DIR-031A packages the authorization needed
so that **DIR-032** can then execute and generate the evidence.

## 2. Package contents
| # | File | Role |
|---|---|---|
| 1 | `ENVIRONMENT_AUTHORIZATION_REQUEST.md` | the formal request + scope + non-goals |
| 2 | `MANAGED_ENVIRONMENT_SPECIFICATION.md` | C1–C8 provisioning spec, sizing, data policy, "provisioned" definition |
| 3 | `CREDENTIAL_AND_ACCESS_REQUIREMENTS.md` | exact credentials DIR-032 needs; delivery + least-privilege rules (names only, no values) |
| 4 | `COST_AND_BUDGET_ENVELOPE.md` | cost drivers + placeholder envelope (Finance to confirm) |
| 5 | `DIR_032_ACCEPTANCE_CHECKLIST.md` | the objective evidence DIR-032 must produce, per WP |
| 6 | `AUTHORIZATION_DECISION_RECORD.md` | **unsigned/PENDING** decision + sign-off matrix |
| 7 | `LUMENAI_V1_1_ENVIRONMENT_AUTHORIZATION_PACKAGE.md` | this index |

## 3. Honesty + constraint compliance
- No environment is claimed to exist; the decision record is **PENDING/NOT SIGNED**.
- No secret values; only credential **names + delivery methods**. No repo secret introduced;
  no `Bearer dev-token`; auth not weakened.
- Data policy: **synthetic/non-PHI only** in the pilot-grade environment.
- No pilot/production/clinical/regulatory authorization or claim.
- Budget figures are labeled **placeholders** pending Finance validation.

## 4. Critical path (what happens after signature)
```
DIR-031A signed  →  infra owner provisions C1–C8 + delivers credentials
                 →  precondition check (health 200 / auth reachable / budget cap)
                 →  DIR-032 executes WP-2..WP-7, captures evidence
                 →  DIR-033 re-certifies engineering Pilot-Entry blockers
                 →  (clinical/executive tracks) →  DIR-034 Pilot Authorization  →  DIR-035 Pilot Execution
```

## 5. Decision needed from the governance authority
Sign (or deny) `AUTHORIZATION_DECISION_RECORD.md`, confirm the budget, and name the
infrastructure owner who will provision. Until then, the program holds at **DIR-031 —
Pilot Entry DENIED**, and this is stated without hedging.
