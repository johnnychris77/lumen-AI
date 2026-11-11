# Eliminate Deterministic Placeholder from Clinical Inspection Outcomes

Critical pilot defect correction. PR #148 added the authoritative `ai_analysis`
contract but the deterministic placeholder (`_pseudo()` — a SHA‑256‑seeded
heuristic, **not** computer vision) still generated the inspection score,
baseline‑match %, findings, confidence, risk level, clinical interpretation,
mentor content and executive summary that populated the clinician‑facing result.
This change retires that scorer from the live clinical decision path. It survives
only as an explicitly segregated development/demo fixture.

## 1. The gate (backend)

`analyze_inspection()` now resolves the authoritative live‑model contract first.
When no eligible trained model evaluated the image — every production inspection
today — it returns an **evidence‑only** `AI_UNAVAILABLE` result via
`_ai_unavailable_result()` and the deterministic scorer below the gate never
runs. The placeholder is reachable only with `demo_scoring=True` or
`AI_ALLOW_DEMO_SCORING=true` (a new setting, default **False** everywhere,
including production — `is_production` does not flip it on).

What the AI‑unavailable result carries (all verified, nothing fabricated):

| Field | Value |
|---|---|
| `analysis_status` / `ai_analysis.status` | `ai_unavailable` / `AI_UNAVAILABLE` |
| `inspection_score`, `risk_level`, `confidence` | `null` |
| `predicted_findings`, `kpi_summary` | `[]`, `{}` |
| `baseline_match_score` / `baseline_match_is_image_similarity` | `null` / `false` |
| `not_evaluated` / `not_evaluated_kpis` | `true` / every KPI label |
| `technician_declared_observations` | the human's declared findings, kept distinct |
| `baseline_source` / `baseline_version` | real approved‑baseline metadata (preserved) |
| `overall_cleaning_assessment` | "AI analysis unavailable — manual visual inspection required" |
| `human_review_required` / `ai_analysis.authorizes_release` | `true` / `false` |
| `clinical_decision` | **not attached** (would otherwise fabricate "Acceptable" integrity / 0% confidence) |

Real identifier decode + match, approved‑baseline resolution, image‑quality,
coverage/guidance/risk‑map and any genuine compatible‑image comparison stay
operational.

### Other corrected paths
- **Route** (`routes/inspections.py`): an explicit `ai_unavailable` branch keeps
  the real `baseline_source` visible, marks the record not‑scored, requires
  supervisor review, and persists no fabricated score/risk. The clinical‑report
  PDF endpoint re‑runs the authoritative analysis (AI_UNAVAILABLE → "Not
  evaluated" placeholders, supervisor‑review verdict).
- **`build_clinical_decision()`**: for any non‑completed analysis (no‑baseline or
  AI‑unavailable) it now reports `integrity_assessment = "Not evaluated"` and
  `confidence_pct = null` instead of a fabricated "Acceptable" / `0%`.
- **`clinical_report_pdf`**: renders "Not evaluated" for score/integrity/
  confidence when no completed analysis exists.

## 2. Frontend (no fabricated clinical display)

`NewInspectionPage` distinguishes "no approved baseline" from "baseline resolved
but AI unavailable", shows the neutral "AI model unavailable — manual inspection
required" headline (never the green "✓ AI Analysis Complete" success state),
renders grid fields as "Not evaluated" / "Not scored — AI unavailable", and the
submit toast no longer claims a baseline gap when a baseline was found.
`DecisionEnginePanel` renders the `NOT_EVALUATED_BY_CURRENT_MODEL` contract;
`ClinicalDecisionPanel` is hidden when no clinical decision exists;
`CapturePage`/`StationPage` drop the "Analysis Complete"/PASS tone and route the
unavailable verdict to human review. `InspectionResultsHistory` already renders
`null` scores as "—".

## 3. Tests

- **`tests/test_clinical_placeholder_elimination.py`** — 12 new regression tests
  run with the scorer **OFF** (production default), end‑to‑end through the real
  submission route, proving: AI_UNAVAILABLE not scored; no fabricated score/
  confidence/detection; no pseudo clinical‑decision/mentor/executive content;
  "Not evaluated" categories; metadata‑only baseline → no similarity %; a genuine
  comparison labelled *visual similarity — not verified cleanliness*; the PDF
  carries no fabricated conclusion; declared findings attributed to the human;
  no automatic release authorization; non‑contradictory status; and API +
  history + report agree.
- **`tests/test_inference_provenance.py`** — the 8 existing provenance guarantees
  continue to pass with the scorer off.
- Legacy unit tests that specifically exercise the demo scorer's math/
  interpretation opt in via `pytestmark = pytest.mark.usefixtures("enable_demo_scoring")`
  (a shared `conftest` fixture) — they remain valid *segregated demo* coverage.
- Full suite: **3789 passed, 2 skipped**; `ruff` clean; frontend `vite build`
  clean.

## 4. Pilot validation (local, production path — scorer OFF)

A representative inspection (approved manufacturer baseline, technician‑declared
"blood") submitted through `POST /api/inspections`:

- `ai_analysis.status = AI_UNAVAILABLE`, `model_maturity = unavailable`,
  `authorizes_release = false`, `human_review_required = true`.
- `inspection_score / risk_level / confidence = null`; `predicted_findings = []`.
- `technician_declared_observations = ["blood"]` (human, never AI).
- `baseline_source = manufacturer` (real metadata); `baseline_image_similarity.
  similarity = null` (no ACTIVE baseline image bytes).
- Live‑inference health: `model.status = unavailable` (no registered trained
  model for the tenant).
- History record for the same inspection: `score_status =
  supervisor_review_required`, `inspection_score = null`.
- Clinical report PDF: HTTP 200, no `/ 100` score line.

All clinician‑facing surfaces agree on the honest AI_UNAVAILABLE verdict with no
fabricated clinical outcome, and human review is required.

## 5. Review-driven hardening (post-#149 reconciliation)

Automated code review surfaced ten findings; all were addressed:

- **Reject demo scoring in production** — `Settings.validate()` now fails startup
  when `AI_ALLOW_DEMO_SCORING` is enabled with `APP_ENV=production`.
- **Honest AI-unavailable `model_result`** — advertises no supported categories
  and no model version (every category "not evaluated"), so the UI can't render
  a contradictory "supported" claim under the AI_UNAVAILABLE banner.
- **Baseline-override safety** — the override panel is gated on `baselineMissing`
  (frontend) and the endpoint rejects (409) an override when the blocker is model
  availability (`score_status == "ai_unavailable"`), so it can't mark an
  AI-unavailable record `scored_after_override` via the manual risk calculator.
- **Capture-station bytes** — `/api/capture/ingest` now passes the captured frame
  bytes into inference so an eligible active model can evaluate station captures;
  its persistence mirrors the honest `ai_unavailable` contract.
- **Abstention = not evaluated** — a completed-but-abstained live result
  (insufficient image quality, confidence below threshold, unknown class) is
  treated as not evaluated, so the placeholder can never fabricate a score for it.
- **Durable technician-declared observations** — a new
  `inspections.declared_findings` column (JSON, + migration) preserves the
  human's declaration with explicit provenance; history surfaces
  `technician_declared_observations` and the report prints a
  "Technician-Declared (human)" line, kept distinct from AI findings.
- **Honest workflow audit** — the AI_ANALYSIS timeline event records "AI analysis
  unavailable — manual inspection required" for the no-model path instead of a
  fabricated "AI analysis completed".
- **Clinical report byte reload** — the report path reloads and hash-verifies
  retained image bytes before re-analysis, so a report matches the inspection's
  original evaluation rather than reporting "not evaluated" for a scored row.
- **Risk-metric aggregation** — manufacturer instrument-family performance
  averages only genuinely scored inspections, so an AI-unavailable row's sentinel
  `risk_score=0` is not counted as a verified zero-risk result.
- **Baseline status preserved** — the `ai_unavailable` route branch keeps
  `baseline_status="approved_baseline_found"` (resolved from the #149 merge), so
  escalation/coverage/dashboard consumers are not misled into "missing baseline".

Two new regression tests cover the override rejection and the durable
technician-declared record; the full backend suite remains green.

## 6. Production incident — demo flag leaked the placeholder (Inspection #11)

After #150 merged, a live inspection still showed `MODEL RESULT — EXPERIMENTAL`
with Debris 73% / Corrosion 77% "model observation" and the "Experimental — Not
Validated" banner, alongside the correct AI-unavailable headline. Reproduced
locally: the leak occurs when **`AI_ALLOW_DEMO_SCORING=true` is set on the
deployment** — the clinical HTTP route honored the flag and ran the deterministic
placeholder (`analysis_status="completed"`, `placeholder_scoring=true`,
`model_result.findings=[debris, corrosion]`), even though the authoritative
`ai_analysis.status` was `AI_UNAVAILABLE`. Root cause: a misconfigured
environment variable, and the only guard was a startup check scoped to
`APP_ENV=production`.

Defense in depth (two independent layers, so neither config discipline nor the
backend alone is the sole safeguard):

- **Backend — the flag is inert outside an explicit dev/test environment.**
  `AI_ALLOW_DEMO_SCORING` is honored only when `APP_ENV` is explicitly one of
  `development|dev|test|testing|local` (`Settings.demo_scoring_effective`, read
  from the raw env var so an **unset** `APP_ENV` is fail-safe NOT permitted).
  On any production / staging / misconfigured deployment the placeholder cannot
  run on a clinical route regardless of the flag — the response carries no
  placeholder findings/score/confidence (values gone, not hidden). The test
  suite marks itself `APP_ENV=test` so the segregated demo fixture still works.
- **Frontend — `NewInspectionPage` never renders placeholder output when AI is
  unavailable.** When `ai_analysis.status === AI_UNAVAILABLE`, the "Experimental
  — Not Validated" banner, the MODEL RESULT findings/supported-categories, and
  the Full-KPI-detail breakdown are suppressed and shown as "not evaluated" —
  even if a stale/misconfigured backend sends placeholder data.

Regression tests reproduce the defect (`AI_ALLOW_DEMO_SCORING=true` +
`APP_ENV=staging` → clean AI_UNAVAILABLE response) and the positive control
(`APP_ENV=test` → demo permitted). Full backend suite **3801 passed, 2 skipped**;
ruff + frontend build clean.

## 7. Deployment note (honest limitation)

Render auto‑deploys `main`. Production verification of the live services
(`lumen-ai-api`, `lumen-ai-1`) must be done from the Render dashboard or an
environment with network access to `*.onrender.com`; this CI/sandbox cannot reach
those hosts (outbound proxy returns 403), so deployment status was not confirmed
from here. Real computer vision is **not** operational — no eligible trained
model evaluated any uploaded photograph; the serving path already in place will
use a real model automatically once one is trained, calibrated and promoted.
