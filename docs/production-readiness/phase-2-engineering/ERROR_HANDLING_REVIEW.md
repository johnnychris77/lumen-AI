# LPR-DIR-013 — Error Handling Review (Phase 2)

**Basis:** grep-quantified exception patterns + contextual inspection. Baseline
`c9797b2`.

## Exception hygiene (measured, `backend/app`)

| Pattern | Count | Assessment |
|---|---|---|
| Bare `except:` | **0** | Excellent — no blanket swallow |
| `except Exception` (named) | 277 | Broad but named |
| `except Exception: pass` (silent) | **~70** | Only ~10 log before continuing |

## Finding EH-01 (MAJOR) — broad silent exception suppression

~70 sites catch `Exception` and `pass` (or continue) without logging. Inspected
examples:

- `main.py:220` — best-effort wiring of the optional slowapi rate-limit handler
  (degrade gracefully if slowapi absent). **Acceptable** but should log at debug.
- `services/digital_twin_engine.py:170` — throughput proxy fallback; swallows and
  continues with a default. **Advisory/analytics path.**
- Similar patterns in benchmark/forge/dashboard analytics services.

**Nuance (important):** these silent handlers are concentrated in **advisory,
analytics, telemetry, and best-effort-degradation** paths — *not* in the
fail-closed security path. The authoritative guards (auth 401, tenant 403,
authorization 403, evidence quarantine, unavailable-model safe states) raise/deny
**explicitly** and are verified by the Phase 1 + this-phase test subset (28/28).
So the risk of EH-01 is **reduced observability / masked non-critical failures**,
not a security bypass. Recommendation: narrow the caught type where possible and
add `logger.debug/warning` so failures are visible — a mechanical Phase 3 cleanup.

## Retry

- **DB readiness retry** on startup (`main.py`) loops with attempt logging
  (`Database ready on attempt N` / `Database not ready (attempt N/max)`) before
  hard-failing — a correct bounded retry with a fail path.
- Network/webhook retry semantics are handled at the integration layer; no
  unbounded retry loop was observed. (Idempotency for duplicate webhook writes is
  the Phase 1 FR-02/AR-18 item, tracked separately.)

## Rollback / transaction boundaries

- SQLAlchemy session-per-request via `get_db` dependency; commits are explicit in
  services/routes.
- **Cross-reference (not re-litigated here):** Phase 1 recorded that several write
  paths `commit()` business data *before* the audit write (FR-01/AR-16, audit not
  atomic). That is an architecture/transaction-boundary finding already tracked for
  Phase 2; this review confirms the pattern exists (commit-then-audit) but does not
  duplicate the finding.

## Timeouts

- The DB readiness probe and `/ready` hard-gate bound startup/health. Outbound HTTP
  timeouts depend on `httpx`/client defaults; no explicit repo-wide timeout policy
  constant was found — recorded as EH-02 (MINOR): standardize outbound-call
  timeouts.

## Logging consistency

| Pattern | Count |
|---|---|
| `logger.` / `logging.` | 39 |
| `print(` | 29 |

**Finding EH-03 (MINOR) — logging inconsistency.** 29 `print()` calls coexist with
logging. Most are startup/seed bootstrap (`main.py` DB-readiness, `routers/users.py`
admin-seed warning with `# noqa: T201`), i.e. before logging is configured or in
one-shot scripts — partly legitimate. Still, standardizing on the logger (with a
startup-safe fallback) is recommended for uniform, structured, filterable logs.

## Fail-closed behavior

Verified intact (this is the safety-critical property):
- Auth: 401 on invalid/unverifiable token.
- Tenant: 403 fail-closed on no membership; header cannot grant authority.
- Authorization: 403 before side effects.
- Evidence: incomplete bundle not promoted (quarantined).
- Model: safe unavailable-model state; no confident result on missing model.
- Unknown: governed non-approving outcome.

None of these paths is among the silent-`pass` sites — confirmed by inspection.

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| EH-01 | MAJOR | ~70 broad silent `except: pass` (advisory/analytics paths; reduces observability) |
| EH-02 | MINOR | No standardized outbound-call timeout policy constant |
| EH-03 | MINOR | Logging inconsistency (29 `print()` vs logger) |

**Positives:** 0 bare excepts; fail-closed security paths raise explicitly and are
test-verified; bounded startup retry with logging.
