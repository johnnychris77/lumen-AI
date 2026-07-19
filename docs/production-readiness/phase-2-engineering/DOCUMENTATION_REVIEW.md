# LPR-DIR-013 — Documentation Review (Phase 2)

**Basis:** repository docs inventory + inline-comment/docstring sampling. Baseline
`c9797b2`.

## Inventory (measured)

| Location | Count |
|---|---|
| `docs/**/*.md` | **1,062** |
| Root `*.md` | 13 (README, ARCHITECTURE_SUMMARY, VERSION_1_0, RELEASE_NOTES, DEMO_*, PRODUCTION_HARDENING, PITCH_DECK, PORTFOLIO_*, SCREENSHOT_CHECKLIST) |
| README.md | present |
| Inline `# noqa` acknowledgements | 157 |

The documentation surface is **very large** — 1,062 markdown files under `docs/`,
reflecting the multi-phase program (foundation, clinical-pilot, ML governance,
baseline-library, decision-engine, per-agent docs, and the Phase 1 architecture
freeze). Coverage breadth is a strength.

## README / developer guides

- `README.md` present at root; `CLAUDE.md` provides authoritative developer
  workflow (test-from-`backend/`, ruff, frontend build, commit/push conventions,
  security constraints). This is effective, actionable developer documentation.
- Architecture docs exist at multiple layers (`ARCHITECTURE_SUMMARY.md`,
  `docs/production-readiness/phase-1-architecture/*`).

## Architecture / API docs

- Phase 1 delivered a full architecture set (freeze declaration, current-state,
  inventories, trust boundaries, ADR register). API surface is inventoried
  (`INTERFACE_AND_API_INVENTORY.md`, 1,912 endpoints) and OpenAPI is generated from
  the app.
- **Gap DOC-01 (MINOR):** OpenAPI is generated but there is **no CI schema-diff
  gate** (carryover Phase 1 I-04) — API docs can silently drift from code.

## Runbooks

- `DEMO_RUNBOOK.md`, `PRODUCTION_HARDENING.md`, `ops/`, `observability/` provide
  operational guidance; foundation phase delivered DR/backup runbooks with measured
  RTO/RPO. Runbook coverage is good for the current stage.

## Comments / inline documentation

- Sampled modules carry **purposeful docstrings** that document *intent and
  honesty constraints* (e.g. `app/ai/inference.py` explicitly states the
  deterministic placeholder is "not a trained CV model";
  `enterprise_audit_service` documents the deprecated shim delegation). This is
  high-value inline documentation — it encodes the safety/honesty posture in the
  code itself.
- 157 `# noqa` / `# nosec` sites are **annotated with rationale** in the cases
  sampled (e.g. `# nosec B608 - set_clause built only from explicit server-side
  allowlisted columns`), i.e. suppressions are documented, not blind.

## Consistency / drift risks

- **DOC-02 (MINOR) — documentation volume vs consolidation.** With 1,062 docs
  across many program phases, some overlap and potential staleness is expected
  (Phase 1 already flagged Directive 005 doc consolidation, AR-10). Recommend a
  docs index / ownership pass in a later phase so readers can find the current
  authoritative doc per topic.
- No evidence of misleading capability claims in sampled docs; the honesty posture
  (placeholder disclosure, "no clinical/regulatory claim without evidence") is
  consistently applied — and this review continues it.

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| DOC-01 | MINOR | OpenAPI generated but no CI schema-diff gate (carryover I-04) |
| DOC-02 | MINOR | Large doc corpus (1,062 files) needs a consolidation/index + ownership pass |

**Positives:** README + CLAUDE.md actionable; architecture/runbook coverage strong;
inline docstrings encode intent + honesty constraints; suppressions annotated with
rationale.
