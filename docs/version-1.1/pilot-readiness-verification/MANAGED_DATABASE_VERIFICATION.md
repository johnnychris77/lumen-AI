# MANAGED DATABASE VERIFICATION — LPR-DIR-030 (Workstream 2)

**Scope:** Verify whether a **managed, backed-up authoritative database** exists and is
operational for the pilot (blocker **SCAL-01**, tracker **E-01/E-05**). This is an
operational-capability question, not a schema-correctness question.

## 1. Objective evidence reproduced this pass
| Check | Basis | Result |
|---|---|---|
| Alembic single head | `verify_capabilities.py §6` | **PASS** — 13 revisions, single head `e7b2f4a86c31` |
| Every migration reversible | Prior audit; re-derived | 13/13 define `downgrade()` |
| PostgreSQL support exercised in CI | PR #122 check "Backend tests (PostgreSQL 16)" | **success** (01:16 UTC) |
| SQLite tests | PR #122 check "Backend tests (SQLite)" | **success** (01:08 UTC) |
| Managed Postgres **server** reachable in this environment | attempted | **NONE** — no Postgres server / cloud DB provisioned in sandbox |
| Managed backup snapshot + restore transcript | attempted | **NONE** — no managed DB to snapshot |

## 2. What the evidence supports vs does not
- **Supported (VERIFIED technique):** the schema is migration-managed with a single head and
  reversible migrations; the application runs its full test suite against **PostgreSQL 16**
  in CI, proving the code is Postgres-compatible.
- **Not supported (NOT VERIFIED):** the existence of a **managed, provisioned, backed-up
  authoritative Postgres instance** for the pilot. CI's ephemeral Postgres service container
  is a test fixture torn down at job end — it is **not** a managed pilot database, has no
  backup policy, no retention, no restore drill, and no operational ownership.

## 3. Classification
| Item | Classification | Reason |
|---|---|---|
| Postgres compatibility of the code | **VERIFIED** | PG16 CI job green |
| Migration chain integrity + reversibility | **VERIFIED** | single head; 13/13 downgrades |
| Managed authoritative DB provisioned | **NOT VERIFIED** | none exists in this environment |
| Managed backup + retention configured | **NOT VERIFIED** | no managed DB to back up |
| Restore drill on managed DB (E-05) | **NOT VERIFIED** | see `BACKUP_AND_RECOVERY_VERIFICATION.md` |

## 4. What would close the gap (objective evidence required)
Managed Postgres connection string + `alembic upgrade head` transcript against it + an
automated backup snapshot + a restore-to-clean-instance transcript with measured RTO/RPO.

## 5. Determination
**Database *code readiness* VERIFIED; managed database *operational capability* NOT
VERIFIED.** Blocker **SCAL-01 remains OPEN**. CI's Postgres service container must not be
represented as a managed pilot database.
