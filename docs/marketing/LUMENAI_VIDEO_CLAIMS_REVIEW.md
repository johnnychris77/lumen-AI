# LumenAI Explainer — Claims Review (v2)

Line-by-line audit that the explainer's copy, UI labels, dashboards, and visuals
stay within LumenAI's safety and positioning guardrails. Every scene below was
written to satisfy these rules; re-audit before each final render.

## Non-negotiable language rules

| Rule | Status | Where enforced |
|------|--------|----------------|
| Never claim to **diagnose** | ✅ | No scene/script uses "diagnose". Scene 6 uses *support / surface / compare / potential finding / review required*. |
| Never **certify** / **guarantee clean** / **determine sterility** | ✅ | No such wording anywhere. |
| Never claim **prevention of infection** or **patient-safety certification** | ✅ | Not stated; framing is inspection evidence + human review. |
| No **FDA clearance / regulatory approval** claim | ✅ | Absent from script, on-screen text, and docs. |
| No **manufacturer or hospital endorsement**; no **MUSC/pilot results** | ✅ | All data is labeled synthetic; no named endorser. |
| **AI-assisted**, human-in-control | ✅ | Scenes 6–8; Scene 7 headline **AI assists. People decide.** |
| **Universal device compatibility** not implied | ✅ | Scenes 3 & 5: *"designed for compatible borescope and camera sources."* "Works with every borescope" appears nowhere; no manufacturer named or shown. |
| Borescope is an **in-workflow image source**, not a separate app | ✅ | Scene 3 shows acquisition inside the inspection; the borescope is an image source. |
| **Multiple representative images**, not one-image-equals-inspection | ✅ | Scene 3 shows Image 1 / 2 / 3; caption 5 states an inspection can hold several. |
| Baselines: **not auto-approved**; baseline **types** distinguished | ✅ | Scene 9 Submit→Verify→Approve→Publish; Scene 6 shows manufacturer/vendor/organizational and "Available Governed Baseline · when available". |
| **No proven financial savings / ROI / avoided-cost / dollars** | ✅ | Scene 13 shows **no dollar figures**; Level 3 (Estimated Financial Impact) marked **"not shown in this animation"**; on-screen + caption: *"No dollar-value savings claimed … Never invented savings."* |
| **No failure-prediction** claim for instrument families | ✅ | Scene 12 shows volume/results/observations only; no prediction wording. |
| **No causation** language | ✅ | Trends are descriptive (Pass/Fair/Review, recurring observations). |

## Financial-claims specifics (Scene 13)

- Title is **"Operational & Cost Intelligence"**, never "Cost Savings".
- **Not displayed:** dollars saved, annual savings, ROI %, avoided-cost, financial-return.
- The gated chain is shown instead: Documented inspection → supervisor decision →
  operational action → outcome → **validated organizational cost data** →
  analysis.
- **Three levels of value:** Level 1 *Operational Metrics* (shown); Level 2
  *Cost-Associated Operational Metrics* (only *with validated organizational
  data*); Level 3 *Estimated Financial Impact* (**not shown in this animation**).
- Preferred narration used verbatim: *"…operational and cost intelligence,
  evaluated with validated organizational data. Never invented savings."*

## Dispositions (Scene 7)

Generic, documented SPD dispositions only — *Return to service · Additional
cleaning · Route for maintenance / repair · Remove from service*. No invented
clinical actions; these mirror ordinary operational outcomes and are labeled as
part of a synthetic demonstration. Confirm they match the product's actual
disposition set before publishing; adjust `demo.dispositions` if the product
uses different exact strings.

## Data / privacy

- **Synthetic content only** (`src/data/demo.ts`, `SYNTHETIC_LABEL`): no PHI, no
  real hospital/MUSC/patient data, no credentials.
- Every history/dashboard/trend scene (10, 11, 12) shows a persistent
  **"Synthetic demonstration data"** badge (`components/DataChrome.tsx`).
- Lumen imagery is procedurally generated. When real footage replaces it,
  confirm **no PHI in pixels or metadata** first.

## Visual guardrails honored

- No robots, humanoid AI, glowing brains, holographic physicians, cyberpunk, or
  neon. No graphic contamination or fear/patient imagery.
- Emotional hierarchy person → instrument → inspection → evidence → intelligence
  → technology (Scene 3 leads with the technician; Scene 7 with the supervisor).
- Areas of interest are **subtle rings**, not bounding boxes everywhere.

## Residual review notes (human sign-off before publish)

1. Confirm the CTA domain `lumenai.opsbridgesolution.com` is correct and live.
2. Legal to approve "operational and cost intelligence" and "operational
   intelligence" phrasing for the investor audience in the target jurisdiction.
3. Confirm `demo.dispositions` and Pass/Fair/Review status strings match the
   product's actual terminology; adjust if needed.
4. Final footage must pass the PHI-in-metadata check.
