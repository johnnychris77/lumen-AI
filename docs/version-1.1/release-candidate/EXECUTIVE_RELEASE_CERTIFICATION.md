# LPR-DIR-026 — Executive Release Certification (Workstream 8)

## Integrated scope (on the merged baseline `main @ 5c22345`)

The Version 1.1 Internal Release Candidate integrates exactly one application-code change
over the v1.0 baseline: the **SEC-C-01 webhook hardening** (PR #119, merged
2026-07-19T22:28:14Z) — fail-closed HMAC verification and server-side tenant binding on
both the integrations and Stripe billing webhooks, with rewritten security tests. All
other merged Version-1.1 work (#108–#118) is documentation and assessment; it adds no
code.

## Outstanding exclusions (not in the RC)

- **PR #120** (LPR-DIR-023 controlled pilot) — OPEN/draft; documents **EXECUTION BLOCKED**.
  Excluded (unmerged, docs-only).
- **PR #121** (LPR-DIR-025 baseline verification) — OPEN/draft; a snapshot of `main @
  3c30d8a` now superseded by the #119 merge. Excluded (unmerged, docs-only).
- No unmerged *implementation* work exists to exclude.

## Known risks

1. **Operational activation risk (by design):** the RC's webhooks are now **fail-closed**.
   Until operators set `WEBHOOK_SECRET_{SYSTEM}`, `WEBHOOK_TENANT_{SYSTEM}`, and
   `STRIPE_WEBHOOK_SECRET`, those endpoints reject all traffic (503/400). This is the
   intended safe posture, but it is a required deployment step.
2. **Stale tag risk:** `v1.1.0` exists but is divergent from `main` (not an ancestor of the
   RC). It must **not** be treated as the V1.1 release marker.
3. **Infrastructure gap risk:** 8 HIGH blockers remain OPEN — production load (PERF-07), HA
   Postgres + worker sizing (SCAL-01), scheduler leader election (RES-01), alerting/IR
   (OPS-INC-01), deploy automation (OPS-DEP-01, a stub), and an executed rollback drill
   (OPS-DEP-02). None is closable from the repository.
4. **Docs-as-delivery risk:** the large merged documentation set describes target-state
   readiness; it is assessment, not delivered hardening. Only the SEC-C-01 code change is
   delivered functionality.

## Residual blockers

**1 CRITICAL (SEC-C-01) → CLOSED on the baseline.** **8 HIGH → OPEN** (SEC-H-01/02
partially mitigated in code; six infra/real-world). MEDIUM/LOW → OPEN, non-blocking.
Real-world pilot gate (site/operators/equipment/managed env/real images) → OPEN.

## Executive recommendation

**Certify the Internal Release Candidate at `main @ 5c22345` — with blockers remaining.**
The CRITICAL gate is genuinely cleared on merged evidence (not feature-branch CI): the
SEC-C-01 fix is on `main`, code-verified fail-closed, and regression-clean. This is the
correct baseline to freeze as the V1.1 Internal RC and to build the next milestone on.

**Do not** advance to Pilot or Production on this RC:

- Pilot advancement requires resolving the HIGH pilot blockers on a **managed
  environment** and satisfying the real-world pilot entry gate; controlled pilot execution
  is independently **EXECUTION BLOCKED** (LPR-DIR-023).
- **Do not cut a `v1.1.*` release tag** yet (a `v*` tag also triggers a GHCR image
  publish). Tag only after the HIGH production blockers are closed on a managed
  environment and an authorized build is produced.

No production authorization. No clinical claims. No regulatory-clearance claims.
