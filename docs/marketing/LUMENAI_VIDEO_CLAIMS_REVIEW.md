# LumenAI Explainer — Claims Review

A line-by-line check that the explainer's copy and visuals stay within
LumenAI's safety and positioning guardrails. Every narration line, on-screen
text, and visual motif below was written to satisfy these rules.

## Non-negotiable language rules

| Rule | Status | Where enforced |
|------|--------|----------------|
| Never claim to **diagnose** | ✅ | No scene/script uses "diagnose". Scene 5 uses *support, surface, compare*. |
| Never **certify** / **guarantee clean** | ✅ | No "certify" / "guarantee". Baselines are "compared", findings "surfaced". |
| Never **determine patient safety** | ✅ | Not claimed anywhere; framing is inspection evidence + human review. |
| No **FDA clearance / regulatory approval** claim | ✅ | Not stated anywhere in script, on-screen text, or docs. |
| **AI-assisted**, human-in-control | ✅ | Scene 6 is dedicated to it: *AI assists. People decide.* |
| **Vendor-neutral** — not "every borescope" | ✅ | Scene 4 uses *"Designed for compatible borescope and camera sources."* The phrase "works with every borescope" appears nowhere. |
| Borescope is an **image source**, not a separate app | ✅ | Scene 3 shows acquisition inside the inspection; on-screen note: "No separate application… LumenAI owns the workflow." |
| Uploaded baselines are **not** auto-approved | ✅ | Scene 8 shows *Submit → Verify → Approve → Publish* and states approval is required before publication. |
| **No causation** language | ✅ | No "causes/proves"; metrics are descriptive ("finding trends"), non-diagnostic. |
| Human review required framing | ✅ | Scenes 5–7 route to qualified human review; Scene 6 headline. |

## Approved phrasings used

- "**can support** image assessment, **surface** visible findings, and
  **compare** with an approved baseline **when one is available**." (Scene 5)
- "routes the inspection for **qualified human review**." (Scene 6)
- "**Designed for compatible** borescope and camera sources." (Scene 4)
- "creates a **governed pathway** … to **contribute and use trusted reference
  information**." (Scene 8)
- "**can become** operational intelligence — helping organizations understand
  **patterns**…" (Scene 9) — aspirational-but-bounded ("can", "patterns").

## Phrasings deliberately avoided

- ❌ "detects contamination" → ✅ "surface visible findings"
- ❌ "ensures the instrument is clean" → ✅ "compare with an approved baseline"
- ❌ "works with every borescope" → ✅ "compatible borescope and camera sources"
- ❌ "approved baseline" for vendor uploads → ✅ Submit → Verify → Approve → Publish
- ❌ "AI decides / clears the instrument" → ✅ "AI assists. People decide."

## Data / privacy

- **Synthetic content only** (`src/data/demo.ts`): no PHI, no real hospital
  identities, no real patient data, no credentials. Facility/technician labels
  are generic placeholders marked "(demo)/(synthetic)".
- Lumen imagery is **procedurally generated**, not a real patient/case image.
- When real footage is added, confirm **no PHI in image metadata** (a LumenAI
  security constraint) before use.

## Visual guardrails honored

- No robots, humanoid AI, glowing brains, holographic physicians, cyberpunk, or
  neon. No graphic contamination or fear-based/patient imagery.
- Interior lumen kept realistic and restrained (subtle variation, not
  dramatized).
- Areas of interest are **subtle rings**, not bounding boxes everywhere (Scene 5).

## Residual review notes (for human sign-off before publish)

1. Confirm the CTA domain `lumenai.opsbridgesolution.com` is correct and live.
2. Legal/regulatory to approve the phrase "operational intelligence" for the
   investor audience in the target jurisdiction.
3. If a voiceover actor emphasizes differently, re-check that "AI assists.
   People decide." remains the clear thesis of Scene 6.
4. Final footage must pass the PHI-in-metadata check above.
