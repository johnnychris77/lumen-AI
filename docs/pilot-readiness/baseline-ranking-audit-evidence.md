
Purpose
This document describes the baseline ranking audit/evidence helper added after the baseline-aware inspection ingestion work. The helper builds a deterministic in-memory evidence record for a single inspection payload and does not write files or call external services.

The documentation is limited to the current backend helper and tests. It does not claim production deployment, database persistence, or external audit export integration.

Implementation Reference
Backend helper:

backend/app/core/baseline_ranking_contract.py

build_baseline_ranking_audit_evidence(payload)

Test coverage:

backend/tests/test_baseline_ranking_audit_evidence.py

backend/tests/test_baseline_ranking_contract.py

backend/tests/test_inspection_baseline_ranking_ingestion.py

Related pull requests:

PR #18 added baseline-aware inspection ingestion contract tests.

PR #19 added validation/error-handling coverage for malformed, partial, unsupported, and unsafe baseline-aware payloads.

PR #20 added deterministic audit/evidence record construction for baseline ranking decisions.

Evidence Record Fields
The helper resolves the authoritative baseline ranking contract first and then emits the evidence record from that result. This keeps client-provided ranking fields from overriding the backend decision.

Core decision fields emitted for each evidence record:

Field	Source	Purpose
instrument_match_status	Backend-coerced contract input	Instrument match state used by the ranking contract.
baseline_status	Backend-coerced contract input	Baseline status used by the ranking contract.
baseline_confidence	Backend-coerced contract input	Baseline confidence submitted with the payload.
ranking_mode	Backend-resolved contract output	Canonical ranking mode.
baseline_review_required	Backend-resolved contract output	Whether review is required before final ranking.
final_ranking_allowed	Backend-resolved contract output	Whether a final baseline-confirmed ranking is allowed.
baseline_review_reason	Backend-resolved contract output	Human-readable reason for the decision.
Identity fields included when present and non-empty:

Field	Purpose
capture_method	How instrument identity was captured, such as Barcode or Manual Entry.
barcode_value	Barcode scan value when supplied.
instrument_name	Human-readable instrument name when supplied.
model_number	Model number when supplied.
instrument_category	Instrument category when supplied.
Expected Outcomes
Approved Baseline
When baseline_status is Approved Baseline Found and instrument_match_status is Matched, the evidence record shows:

{
  "ranking_mode": "Baseline-confirmed ranking",
  "baseline_review_required": false,
  "final_ranking_allowed": true,
  "baseline_review_reason": "Approved baseline matched."
}
Pending Baseline
When baseline_status is Pending Baseline Review, the evidence record shows a provisional result:

{
  "ranking_mode": "Provisional ranking",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline pending approval; ranking remains provisional."
}
Manual Review
When baseline_status is No Approved Baseline or Baseline Not Available, the evidence record shows manual review is required:

{
  "ranking_mode": "Manual review required",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "No approved baseline available for final ranking."
}
Malformed or Non-String Baseline Inputs
Malformed or non-string baseline ranking inputs are treated as unconfirmed baseline context for evidence purposes. The helper emits a safe review-required record with final_ranking_allowed set to false.

{
  "instrument_match_status": "",
  "baseline_status": "",
  "baseline_confidence": "",
  "ranking_mode": "Pending baseline check",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline status has not been confirmed."
}
Unsafe Client-Supplied Ranking Overrides
If the payload includes client-supplied values such as ranking_mode, baseline_review_required, final_ranking_allowed, or baseline_review_reason, the evidence helper does not trust those values. It rebuilds the evidence record from the backend ranking contract.

For example, a payload that claims final ranking is allowed but has instrument_match_status other than Matched emits a fail-closed evidence record:

{
  "ranking_mode": "Pending baseline check",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline status has not been confirmed."
}
