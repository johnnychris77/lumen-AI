# LumenAI — Database Catalog

**417 tables across 140 SQLAlchemy model files.** SQLite locally, Postgres in production (per `docs/deployment/`). All figures below are from direct inspection of `app/models/*.py`, not estimated.

## Tables

See [ARCHITECTURE_INVENTORY.md](./ARCHITECTURE_INVENTORY.md) and [MODULE_CATALOG.md](./MODULE_CATALOG.md) for the full per-module table list, grouped by specialist. This document covers cross-cutting schema-quality findings that apply across all 417 tables.

## Naming

Table names are consistently `snake_case`, and the vast majority follow a `<specialist_prefix>_<noun>` convention (`oracle_hypotheses`, `governed_actions`, `council_cases`) that maps 1:1 to the owning module — a real strength for navigability. Two exceptions are worth noting:

- `EnterpriseFacility`/`EnterpriseDepartment` — identical **class** names in `enterprise_quality.py` and `enterprise_hierarchy.py`, but different **table** names (`enterprise_facilities` vs. `enterprise_hierarchy_facilities`). See Dependency Map §4.
- `TenantMembership` — identical class name **and** identical table name (`tenant_memberships`), defined independently in `app/models/tenant_membership.py` and inline in `app/db/models.py`, with different column sets. See Dependency Map §4 and Technical Debt Register TD-14.

## Relationships / Referential Integrity — **primary finding**

**Only 6 of 140 model files use a real SQLAlchemy `ForeignKey()` constraint (12 constraints total).** The other 134 files reference related rows with a plain `Integer` column (e.g. `governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)`) — a same-shape, same-name convention, but with **no database-level referential-integrity enforcement**. This is consistent across nearly the entire codebase (it is, in fact, the exact pattern used when Steward and Oracle were built in this same review cycle), so it is a deliberate, uniform architectural choice rather than an oversight in any one file — but it means:

- Deleting a parent row (e.g. a `GovernedAction`) does not cascade or block on its children (`GovernedActionAuditEvent`, etc.) — orphaned child rows are possible and the database will not prevent or flag them.
- There is no `ON DELETE CASCADE`/`RESTRICT` policy anywhere in the schema — cleanup, if needed, must happen entirely in application code.
- Referential integrity is enforced (if at all) only by the service layer's own query discipline, not by the schema.

**Recommendation**: this is the single highest-value schema-hardening item for Phase 2. It does not need to be fixed everywhere at once — a good first step would be adding real `ForeignKey` constraints to the highest-value integrity boundaries (audit/governance tables, where an orphaned row is a compliance problem) without touching the other 130+ files in the same pass.

## Constraints

- **Zero `CheckConstraint` usage anywhere in the schema.** Every "enum-like" string field (status, category, risk_level, confidence_level, etc. — and there are dozens of these across specialists) is validated only in the Python service layer (e.g. `if x not in VALID_STATUSES: raise ValueError`), never at the database level. A direct SQL write (migration script, manual fix, future service bypassing the validated constructor) could insert an invalid enum value with no database-level objection.
- **Only 3 files use `UniqueConstraint`.** Several tables that look like they should have a natural uniqueness requirement (e.g., one `TenantMembership` row per `(tenant_id, user_email)`) rely on service-layer "check then insert" logic rather than a database-enforced unique constraint — a known race-condition class (two concurrent requests both pass the check, both insert) that a real constraint would close for free.

## Indexes

**1439 `index=True` column declarations** — indexing discipline is genuinely good at the column level; `tenant_id`, `created_at`, and the primary lookup key of nearly every table are indexed. No composite/multi-column indexes were found in this pass (each `index=True` is a single-column index) — for tables that are always queried by `(tenant_id, some_other_column)` together, a composite index would outperform two single-column indexes, but this is a performance-tuning refinement, not a correctness gap.

## Tenant scoping

**125 of 140 model files have a `tenant_id` column; 15 do not.** Most of the 15 are legitimately tenant-agnostic by design (network-wide registries like `baseline_library.py`/`instrument_registry.py` which are explicitly anonymized cross-tenant aggregates, or platform-internal tables like `admin_credential.py`, `user.py`, `alert_event.py`, `digest_subscription.py`/`digest_delivery.py`). Two are worth a second look since their owning specialist is otherwise tenant-scoped everywhere else: **`guardianx_assurance.py`** and **`industry_collaboration.py`** (Beacon) — confirm whether their lack of `tenant_id` is intentional (cross-tenant by design, matching their "cross-cutting assurance"/"industry collaboration" mission) or a gap (Technical Debt Register TD-15).

## Normalization

No obvious over-normalization or under-normalization issues found at the schema level — most tables are reasonably flat, JSON-text columns (`*_json` suffix convention) are used consistently and deliberately for genuinely variable-shape data (evidence lists, JSON snapshots of another service's output) rather than as a substitute for real relational columns. This convention is applied consistently enough across specialists that it reads as an intentional design choice, not schema drift.

## Migration History — **second major finding**

**Only 4 Alembic migration files exist**, despite 417 tables:
1. `001_initial_schema.py` — legacy sequential-numbered initial migration.
2. `4b336d3ed612_full_schema_baseline.py` — a large squash/baseline migration (this is almost certainly where the bulk of the 400+ tables actually get created in a tracked migration).
3. `f29f1456bdec_add_governed_action_tables.py` — incremental, adds Steward's 7 tables.
4. `a1ba6c5ed8f8_add_oracle_discovery_tables_and_.py` — incremental, adds Oracle's 6 tables + the `GovernanceApproval`/`KnowledgeArticle` import fix.

Given the codebase has ~25 named specialist sprints, and only the most recent 2 (Steward, Oracle) have their own tracked incremental migration, **the overwhelming majority of the schema's historical growth was never captured in a tracked Alembic migration** — it relied on `Base.metadata.create_all()` at app startup (referenced explicitly in several model docstrings, e.g. `admin_credential.py`, `user_role_assignment.py`) being re-run against a database that already had the baseline squash applied. This works in SQLite/dev but is a real production-deployment risk against Postgres: `create_all()` is not idempotent-safe against manual schema drift the way a tracked migration chain is, and there is no way to `alembic downgrade` any of those ~23 un-migrated sprints individually. This is the most significant Technical Debt finding in the entire review (Technical Debt Register TD-02, Critical).

**Recommendation**: before Phase 2 begins, run `alembic revision --autogenerate` against the current model state and verify it produces an empty diff against the actual running schema (the same verification methodology already used for the Steward/Oracle migrations) — if it's empty, the current `create_all()`-grown schema is at least captured correctly going forward even though its history wasn't tracked at each step.
