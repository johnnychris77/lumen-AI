# LumenAI — UX Guidelines

Objectives 5 (Inspection Experience) and 6 (Explainability) review. Covers the image capture flow, finding/evidence/confidence presentation, anatomy visualization, recommendation display, supervisor handoff, and — per Objective 6 — which of the required explainability fields actually reach the screen today.

## Image capture flow

Two parallel, non-integrated flows exist (see [USER_JOURNEYS.md](./USER_JOURNEYS.md) for the full duplication finding):

- **`NewInspectionPage.tsx`** (`/inspection/new`) — the production flow with AI wiring. A single scrolling form, not a multi-step wizard; a static 5-step text strip is decorative, not an actual stepper. Image capture: one required "Inspection Images" input + one optional "Borescope Images" input, both multi-file, 10 MB/file cap; **no minimum image count is enforced** — validation only requires ≥1 image total. A `GuidedCapturePanel` shows the next zone to capture, camera-angle/lighting/focus tips, and a live coverage %, but only after `instrument_type` is chosen. Per-image tagging (zone/view/quality/notes) is supported. A coverage gate can hard-block submission via `CoverageOverridePanel` if `coverage_gate_status === "blocked_pending_override"`. Upload progress feedback is limited to a single disabled-button label ("Uploading image & running AI analysis…") — no per-file progress bar or percentage. **There is no dedicated pre-submission review screen** — the AI Prediction Panel simply replaces the form in-place after a successful submit.
- **`InspectionImageUploadPage.tsx`** (`/inspection-image-upload`) — a separate, simpler form with an explicit "📷 Image Capture Guidelines" `<details>` panel (format/resolution/lighting requirements, "Borescope: 3 images minimum," a PHI warning) that `NewInspectionPage` lacks. No AI Prediction Panel exists here at all — the result is just a success/error banner with an inspection ID; **no findings, risk, or confidence are ever shown from this flow.**
- **`BaselineImageUploadPage.tsx`** (`/baseline-image-upload`, for reference images, not inspections) has its own capture-guidelines block with required angles.

**Recommendation**: consolidate the capture-guidance content (the good `<details>` panel from `InspectionImageUploadPage`) into the single production flow (`NewInspectionPage`), and add a lightweight pre-submission review step there.

## Finding display

No frontend file references the backend `InspectionFinding` model by name — findings reach the UI via two separate, independently-shaped response paths:
- **`AnalysisDetails`** (`NewInspectionPage.tsx`) renders `predicted_findings` as per-KPI cards showing type/label, probability %, severity (text), an "SPD Risk Impact" badge, and — if present — zone, zone-risk badge, zone reason, and recommended manual check.
- **`FindingsTable`** (`components/ClinicalDecisionPanel.tsx`) renders a different `Finding` type as a table with Finding/Detected/Prob %/Severity/**Confidence %**/SPD Risk columns.

Confidence is shown in the table variant but **not** in `AnalysisDetails` — the two finding-display surfaces are inconsistent about which fields they carry.

## Anatomy visualization — confirmed to not exist

This is stated directly in the code, not inferred: `components/InstrumentIntelligencePanel.tsx`'s own docstring: *"Text/card risk map. Visual anatomy maps, clickable zones, and heatmaps are a future computer-vision release (not fabricated)."* `components/ClinicalDecisionPanel.tsx`'s "Evidence Used" card states explicitly: *"(heatmaps / bounding boxes not fabricated)."* A repo-wide search for canvas/SVG/image-annotation libraries returns nothing — **there is no bounding box, heatmap, or clickable zone diagram anywhere in the codebase.** Zone is shown only as a text label + colored risk badge in a table row. This is an honest, deliberate limitation the code itself discloses (mirroring the same "no fabricated visual overlay" discipline documented in `docs/clinical-validation/AI_LIMITATIONS.md` for anatomy-zone resolution generally) — not a bug, but a real UX gap worth prioritizing given how much clinical value a real spatial overlay would add.

## Evidence/confidence presentation — three inconsistent treatments

- **`components/VeritasEvidencePanel.tsx`** (Veritas's `readiness_category`) renders a human label + "{label} — {score}/100" text, a `limitations` list, and a `next_action` line — the richest presentation found. **But this component is never imported by any page or component in the entire frontend** — it is a fully orphaned, unreachable component. The evidence-readiness score, limitations, and next-action text it's built to show are not currently visible to any user.
- **`components/ReadinessDispositionPanel.tsx`** (which IS live, mounted in `ClinicalDecisionPanel.tsx`) shows `readiness_score` as a plain number and `readiness_status` as plain text — no formatting, no color.
- **`components/ClinicalDecisionPanel.tsx`** shows "Evidence Strength" as a 5-star rating plus a text level, and "Confidence" as "{level} ({pct}%)" text.

Confidence/evidence readiness is therefore shown as a percentage+label, a 5-star rating, or a bare number depending on which component happens to render it — never a consistent progress-bar/meter treatment across the app.

## Recommendation display — the explanation text genuinely works

`disposition_engine.py::recommend_disposition()` returns a grounded, non-generic `explanation` string for each of its 7 dispositions. That explanation is threaded through `disposition_evidence_service.py` as `clinical_rationale`, and `ReadinessDispositionPanel.tsx` genuinely renders both the disposition label and the rationale text — confirmed as a real, working path, not just a backend capability with no UI consumer.

**A consistency risk, however**: `ClinicalDecisionPanel.tsx` separately renders a second "recommendation" surface (`cd.recommendation.result` / `.action_text` + a `next_actions` list) sourced from a *different* scoring/analysis pipeline than `disposition_engine.py`. Two recommendation panels can appear on the same page, from two different backends, with no guarantee they agree — worth flagging as a real risk even though this review found no confirmed instance of an actual disagreement.

## Supervisor handoff — real, but styled 5 different ways

A "needs supervisor review" state does get a distinct visual treatment, but the treatment itself is inconsistent across surfaces:
- `NewInspectionPage.tsx`: amber-bordered card, "⚠ Supervisor Review Required" vs. green "✓ AI Analysis Complete."
- `ClinicalDecisionPanel.tsx`: an orange banner strip specifically for the literal string `"SUPERVISOR REVIEW"` result (red for REPROCESS/REMOVE, green for PASS, amber for MONITOR).
- `InspectionResultsHistory.tsx`: an amber pill badge in a table's Status column.
- `FindingsQueuePage.tsx`: a purple pill, specifically for `workflow_state === "Supervisor Review"` — a different color than the amber/orange used elsewhere for the same concept.
- `CoverageOverridePanel.tsx`: a red-bordered card for the "insufficient anatomy coverage" sub-case — again a different color for what is conceptually the same "needs supervisor attention" state.

No modal/interstitial is used anywhere — handoff is always an inline banner/badge on the same page. **Recommendation**: standardize on one color (the codebase's own design tokens define `--color-warning` for exactly this purpose — see [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)) for every "needs supervisor" signal across all 5 surfaces.

## Objective 6 — the seven explainability fields, verified against what's actually on screen

Per this review's mandate, "users should understand why" is checked against real rendered UI, not backend model capability:

| Field | Surfaced to a user today? | Where |
|---|---|---|
| Finding | Yes | `AnalysisDetails`, `FindingsTable` |
| Evidence | Yes | "Evidence Used" card (`ClinicalDecisionPanel.tsx`) |
| Confidence | Yes (inconsistently formatted — see above) | Multiple components |
| Limitations | **No, in practice** | Only rendered by `VeritasEvidencePanel.tsx`, which is never mounted anywhere |
| Alternative explanations | **No** | `alternative_explanations_json` exists only in GuardianX's backend model; `AIAssuranceCenter.tsx`'s "Explainability" tab only prints instructions for calling the API manually — it never fetches or renders a record |
| Recommended action | Yes | `clinical_rationale` (`ReadinessDispositionPanel.tsx`), `action_text`/`next_actions` (`ClinicalDecisionPanel.tsx`) |
| Human reviewer required | **Partial** | Shown only as static, fixed boilerplate copy ("AI outputs include human_review_required: true"), never bound to the actual per-record boolean — it reads the same regardless of the record's real value |

**This is the most important finding for Objective 6**: "Limitations" and "Alternative explanations" are computed and stored server-side (Veritas's `limitations`, GuardianX's `alternative_explanations_json`) but have **no live path to the screen** — one via a component that's built but never mounted, the other via a component that only tells the user how to call the API themselves rather than calling it. "Human reviewer required" is asserted as fixed text rather than reflecting the real per-finding flag, which risks a false sense of unconditional review that the underlying data doesn't actually guarantee is being read correctly.

**Recommendation, in priority order**: (1) mount `VeritasEvidencePanel.tsx` somewhere in the live inspection-results flow — it already renders the "limitations" field correctly, it's simply disconnected; (2) wire `AIAssuranceCenter.tsx`'s Explainability tab to actually fetch and render GuardianX's `alternative_explanations_json`; (3) bind the "human review required" disclaimer to the real per-record boolean instead of static copy. None of these require new AI capability — the data already exists.
