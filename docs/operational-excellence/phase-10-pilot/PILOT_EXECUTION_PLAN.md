# LPR-DIR-021 — Pilot Execution Plan (Phase 10)

## Status framing (honesty mandate)

This is a **real, executable plan** for a controlled clinical pilot. It is **not** a
record of an executed pilot. **No controlled pilot has run** — consistent with the
existing `docs/clinical-pilot/PILOT_EXECUTION_STATUS.md` (**PILOT_NOT_EXECUTED — REAL-
WORLD PRECONDITIONS NOT IN PLACE**) and Pilot Alpha (physical lab not built, no
governed model). Pilot execution is also **gated** by 1 CRITICAL (SEC-C-01) + 8 HIGH
open blockers and the absence of a managed production-representative environment. This
plan defines *how* the pilot runs *once* those preconditions exist.

## Pilot objectives (evidence to collect)

Observe-only, workflow/operational evidence — **no clinical performance measurement**:
1. Workflow integration (does the governed pipeline fit real SPD/OR workflow?).
2. Operator usability (can trained technicians/supervisors operate it?).
3. System stability (uptime, error rates in a real environment).
4. Inspection throughput (time per inspection; operational, not diagnostic).
5. Data quality (real image quality, metadata completeness, annotation consistency).
6. Human-review efficiency (queue turnaround, adjudication rate).

## Participating sites

**NONE SELECTED (requires real engagement).** `docs/clinical-pilot/
PILOT_SITE_SELECTION.md` provides selection criteria + an intentionally unfilled
record. Target profile: 1 hospital SPD with a named executive sponsor, SPD manager,
Infection Prevention, Biomed, and IT security contacts. Single-site, supervised.

## Pilot users

**NONE EXIST.** Roles to staff (from the annotation/inspection governance): Image
Acquisition Operator, Primary Annotator, Secondary Reviewer, Supervisor/Approver,
Quality Auditor, Program Admin — with separation of duties. Training curriculum ready
(`docs/clinical-pilot/PILOT_TRAINING_MANUAL.md` / `PILOT_SITE_GUIDE.md`).

## Inclusion criteria

- Instruments with a governed baseline (`BaselineLibraryEntry` ACTIVE) and a
  Digital Twin identity (LCID/`digital_twin_id`).
- Trained, competency-signed operators; separation of duties satisfiable.
- Managed environment provisioned (PostgreSQL, durable storage, TLS, alerting).
- **AI runs observe-only / advisory** — never autonomous disposition.

## Exclusion criteria

- Any instrument without a governed baseline or identity.
- Any pathway requiring an autonomous AI decision.
- Any PHI in images/metadata.
- Execution while SEC-C-01 or the HIGH operability blockers remain open.

## Governance

Weekly governance review (Form E), mandatory human review (`human_review_required:
true`), hash-chained audit on every action, contamination-safety fail-closed states,
Unknown/Unable-to-Determine as valid outcomes. Supervisor authority over every AI
advisory. No general deployment authorized.

## Success metrics (measurement sources; `insufficient_data` rule)

| Metric | Source | Target framing |
|---|---|---|
| Workflow completion rate | inspection state machine | descriptive, not pass/fail (no premature threshold) |
| Inspection duration | timestamps | descriptive distribution |
| Upload success rate | ingestion service | operational reliability |
| Error rate / stability | logs + `/health` `/ready` | operational |
| Annotation consistency | double-blind review agreement | descriptive |
| Audit completeness | audit chain verification | target 100% |
| Human-review turnaround | reviewer queues | descriptive |

Metrics are reported from **real records only**; where data is absent, report
`insufficient_data` — never a fabricated number.

## Entry gate (must ALL be true before Day 1)

1. SEC-C-01 closed (webhook fail-closed + startup secret validation).
2. HIGH operability closed: load test, HA/workers, scheduler leader-election,
   alerting + incident response, deploy/rollback drill.
3. Managed environment provisioned + smoke-verified.
4. Site agreement signed; users trained + competency-signed; equipment validated.
5. Governed baselines + Digital Twins seeded for in-scope instruments.

## Determination

The **execution plan is complete and real.** The pilot is **not executed** and
**cannot start** until the entry gate is satisfied. This document is the protocol,
not a result.
