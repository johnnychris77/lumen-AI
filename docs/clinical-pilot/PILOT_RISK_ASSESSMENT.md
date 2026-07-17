# Pilot Risk Assessment — Phase 1

Assessment of the risks of running LumenAI advisory-only in a real SPD,
with the controls that exist in code today (each control cites its
enforcement point). This is an engineering risk assessment of the
software and pilot design; site-specific risks (staffing, network,
physical) are assessed with the site during selection.

## R1 — Experimental model presented in a clinical setting (first-order risk)

The only registered model is `Experimental`, trained exclusively on
synthetic images. Risk: users treat its output as validated guidance.
Controls: observe-only framing in protocol and training; result
contract carries model maturity/disclosure fields surfaced in the UI;
promotion ladder blocks any "validated" presentation
(`candidate_promotion.py`); technician/supervisor guides state it
bluntly. Residual risk: automation bias — monitored explicitly
(supervisor guide) and a standing pause trigger.

## R2 — False reassurance (false-PASS class)

Risk: a contaminated instrument reads as clean. Controls (all
regression-tested after the false-PASS remediation): absence of
findings is never evidence of cleanliness; probable contamination can
never produce PASS (decision-engine override); AI-unavailable and
analysis-failure states are explicit and never PASS-like; baseline
similarity can never cancel a contamination observation (Section 17
separation + contamination override); and the pilot's controlling rule —
the site's normal manual inspection continues unchanged for every
instrument.

## R3 — Wrong image/instrument association

Controls: image-identity verification at analysis time (LCID + SHA-256
in the result contract; mismatch fails closed and is audited); barcode
or confirmed manual selection step; technician instruction to verify
context before capture. Any occurrence is a SEV-1 pilot event.

## R4 — Baseline comparator limitations

The aHash comparator has a documented, reproduced collision limitation
on visually different images with similar statistics
(`FALSE_PASS_MANUAL_RETEST.md`) and has never been validated on real
instrument images. Controls: comparison is a separate evidence channel
that never alters the observation (tested); compatibility-first gating;
`no_approved_baseline` shown honestly (expected to be the dominant
state early in the pilot since the baseline library starts empty).

## R5 — Data loss / integrity

Controls: governed object storage with hash-verified fail-closed reads;
append-only audit with ORM immutability guards + hash chain;
backup/restore/DR procedures executed with evidence
(`docs/foundation/DISASTER_RECOVERY.md`) and re-executed on site
infrastructure before go-live (site guide gate). Zero-loss is an exit
criterion.

## R6 — Privacy / tenant isolation

Controls: single-tenant pilot scope; tenant filtering enforced across
queries and tested; imaging metadata PHI-free by policy and ingest
validation; anonymization enforced on any cross-facility surface; audit
of every access. Any cross-tenant event is SEV-1 + pilot pause.

## R7 — Workflow burden / disruption

Risk: the pilot slows real work or interrupts sterile-processing flow.
Controls: advisory panel is additive; upload failure never blocks
manual inspection; timing capture quantifies burden; sponsor holds a
scope-reduction/stop lever; workflow-burden threshold set pre-launch in
the site record.

## R8 — Security

Controls: TLS-only transport (site gate), RBAC with real accounts,
dev-auth disabled in production (config validation), secrets
env-managed only, API keys hashed-only. Security incidents are recorded
per mission Section 7 and pause the pilot at SEV-1.

## Explicitly out of scope for Phase 1

No autonomous decisions, no performance claims, no model retraining or
redeployment during the pilot, no scope expansion without amendment, no
use of pilot data as Ground Truth without the full annotation and
independent-review governance.
