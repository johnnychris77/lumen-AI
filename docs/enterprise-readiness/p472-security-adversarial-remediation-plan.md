# P4.7.2 — Security Assurance Hardening and Adversarial Verification

**Baseline:** PR #181, commit `c13c5ebd4390b634e4766429969d732a82370bc8`.
**Disposition:** HOLD / NO-GO. This is a test-first remediation work item, not an approval or completed security verification.
**Boundary:** No merge, deploy, model training, production image access, or modification of frozen P4.5/P4.6 evidence.

## Security review findings to reproduce

### P472-01 — Operational evidence provenance
`backend/app/cv/evidence.py:operational_sql_criteria` currently admits a successful non-mock row by searching `result_json` for the literal string `"evidence_class":"model_inference"`. The row classification also trusts `model_integrity.verified` and `evidence_class` from stored JSON. These are not independently authenticated provenance. The current model assumes a single trusted writer.

**Adversarial tests:** create synthetic DB rows through a second writer with (a) forged evidence marker, (b) forged `model_integrity.verified`, (c) conflicting provider/simulated/status, (d) malformed JSON, (e) legacy records, (f) cross-tenant records. Assert none enter KPI, ranking, review, or downstream analytics as genuine measurements. Include raw SQL inserts that bypass the application pipeline.

**Remediation:** use schema-backed, server-owned inference-run provenance tied to an approved model artifact and immutable run identity; enforce writer authorization and DB constraints. Do not accept client/provider JSON claims as proof. Define a safe migration/backfill policy that defaults existing records to unverified. Do not fabricate historic approvals.

### P472-02 — Image URL transport
`backend/app/cv/safe_fetch.py` resolves DNS and connects to a pinned address via HTTPX with `sni_hostname` and `Host`. Unit mocks do not establish actual socket destination or certificate verification.

**Adversarial tests:** instrument socket connections in an isolated network; verify pinned destination, hostname certificate validation, DNS-rebinding resistance, redirect refusal, proxy bypass, IPv4/IPv6 edge cases, response size and timeout enforcement. Assert zero connections for rejected URLs. Use only test-controlled servers; do not probe cloud metadata endpoints or live production.

**Remediation:** retain remote fetch disabled by default; prefer authorized uploaded bytes or internal object references. If TLS hostname verification or DNS pinning is not proven, disable remote fetching entirely pending correction.

### P472-03 — Cross-route tenant authorization
The P4.7.1 author report identifies roughly 180 dependencies across 46 files still using a header-trusting tenant resolver, `routes/benchmarking.py` accepting tenant ID in request body, and an unauthenticated `POST /baseline-ranking/audit-evidence`.

**Adversarial tests:** generate an inventory of all mounted routes and dependencies. For every sensitive object read/write, attempt anonymous, wrong-tenant, forged-header, mismatched-body and admin-policy cases. Ensure authorization precedes side effects and data access. Record any routes whose auth policy is intentionally public.

**Remediation:** centralize membership-verified tenant resolution and object authorization, avoiding blanket changes without contract review. Require authenticated approval for platform-admin cross-tenant access. Cover the baseline-ranking audit endpoint explicitly.

### P472-04 — Streaming metering availability
`/api/stream/frame` reportedly returns HTTP 500 before inference because the metering dependency references a missing model export.

**Adversarial tests:** end-to-end authenticated request with real metering dependency (no stubs); missing model must produce `ai_unavailable`, never an invented finding or unhandled 500. Check authorization and quota enforcement.

### P472-05 — Remaining checks and outbound evidence
Verify PR #181's final SQLite/PostgreSQL CI outcomes and investigate `frontend-security-and-build` / picomatch advisory in a separately scoped dependency patch. Capture outbound network traffic in an isolated Render-equivalent environment, inventory S3/GCS and webhook paths, and document what data each sender transmits.

## Evidence and acceptance
For each finding: failing regression test first; exact path/line and root cause; smallest reviewed correction; passing targeted and full tests; commit SHA; CI run URL; residual risk; non-author reviewer disposition. A test authored by the same engineer is not independent assurance. Preserve all finding IDs as OPEN until formally reviewed.

## Implementation sequence
1. Reproduce provenance forgery and cross-tenant negative cases with fixtures.
2. Fix authorization bypasses and untrusted provenance at the owning boundaries.
3. Verify or disable remote URL fetch until real-network tests establish TLS/DNS properties.
4. Repair stream metering and run end-to-end tests.
5. Resolve CI and collect outbound evidence; obtain non-author security review.

No trained model or eligible scientific dataset is present. Scientific classification remains NOT EVALUABLE.
