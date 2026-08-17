# LumenAI Explainer — Storyboard (v2)

Fifteen scenes. Timecodes and durations come from `src/timing.ts` (the single
source of truth). Total ~116s at 30fps. Emotional hierarchy: **person →
instrument → inspection → evidence → intelligence → technology** — never
AI→AI→AI→dashboard.

Narrative transformation the film delivers:

```
Technician → Select Instrument → Start Inspection →
Physical Borescope Inspection → Borescope Travels Through Lumen →
Live Internal View in LumenAI → Capture Representative Image(s) →
Image Attached → AI-Assisted Analysis → Baseline Comparison → Review Criteria →
Supervisor Review When Required → Human Decision / Disposition →
Governed Evidence Record → Instrument History → Pass / Fair / Review Trends →
Maintenance / Replacement Trends → Operational & Cost Intelligence →
Leadership Visibility
```

---

## 1 · Hidden Surface — 0:00–0:05 · dark
Instrument rotates; camera pushes into the lumen. *Every inspection begins with a person.*
`scenes/HiddenSurface.tsx`

## 2 · SPD Reality — 0:05–0:10 · dark
Modern SPD; complex lumened instruments; the technician is the expert.
`scenes/SPDReality.tsx`

## 3 · Physical Borescope Inspection — 0:10–0:25 · light *(hero scene)*
**LEFT (physical):** technician holds the instrument and advances a compatible
borescope probe through the lumen. **RIGHT (LumenAI):** *Add Inspection Image →
Capture from Borescope*; the **live internal feed** appears inside the active
inspection; technician examines, stops at an area of interest, captures →
**Retake / Use Image → Use Image → Image attached**; multiple representative
images (**Image 1 / 2 / 3**). The technician performs the inspection; the
borescope provides visual access; LumenAI captures/structures/preserves.
`scenes/PhysicalInspection.tsx`

## 4 · Physical / Digital Transition — 0:25–0:31 · dark *(core concept)*
Physical World (Technician → Instrument → Borescope → Lumen Image) **becomes**
Digital Intelligence Layer (LumenAI → Structured Inspection → Analysis →
Baseline → Review → Evidence). `scenes/PhysicalDigitalTransition.tsx`

## 5 · Universal Image Acquisition — 0:31–0:37 · dark
Compatible sources → LumenAI Image Acquisition → Standardized Inspection
Evidence. Vendor-neutral: *"designed for compatible borescope and camera
sources."* `scenes/UniversalCapture.tsx`

## 6 · Image → Intelligence — 0:37–0:47 · dark
Image Quality → AI-Assisted Analysis → Baseline Comparison → Review Criteria;
Current vs **Available Governed Baseline** (baseline types: manufacturer /
vendor / organizational; not every inspection has one). Safety language only.
`scenes/IntelligencePipeline.tsx`

## 7 · Supervisor Review — 0:47–1:00 · dark *(expanded, key moment)*
**Supervisor Review Required → Submit for Review → Supervisor Review Queue →**
cut to the SPD supervisor at another workstation, who reviews captured images,
technician observations, AI-assisted observations, baseline comparison, and
history, then **records a disposition**. Resolves to **AI assists. People
decide.** `scenes/SupervisorReview.tsx`

## 8 · Governed Inspection Record — 1:00–1:08 · dark *(closed loop)*
Technician inspection + evidence + AI-assisted information + baseline +
supervisor review + disposition + audit history → **Governed Inspection
Record**. `scenes/GovernedRecord.tsx`

## 9 · Baseline Ecosystem — 1:08–1:16 · dark
Manufacturer · Vendor · Healthcare Organization → **Submit → Verify → Approve →
Publish**. Never auto-approved. `scenes/BaselineEcosystem.tsx`

## 10 · Instrument Inspection History — 1:16–1:23 · dark
Inspection 001–006 with **Pass / Fair / Review** results. **Synthetic
demonstration data** label. `scenes/InspectionHistory.tsx`

## 11 · Department Trends — 1:23–1:29 · dark
Pass 87% · Fair/Monitor 9% · Review 4% · Evidence Complete 96% · Baseline
Coverage 84% + distribution bar. **Synthetic** label. `scenes/DepartmentTrends.tsx`

## 12 · Instrument-Family Intelligence — 1:29–1:35 · dark
Families (suction, cannulated orthopedic, scopes, powered components, other
lumened) with volume + Pass/Fair/Review distribution + supporting signals. No
failure-prediction claim. **Synthetic** label. `scenes/InstrumentFamilyIntelligence.tsx`

## 13 · Operational & Cost Intelligence — 1:35–1:43 · dark *(claims-critical)*
Progression: Inspection History → Pass/Fair/Review → Recurring Findings →
Supervisor Decisions → Maintenance → Repair/Replacement → **Operational & Cost
Intelligence**. Three value levels: L1 *shown*, L2 *with validated organizational
data*, L3 Estimated Financial Impact **not shown**. **No dollar values.**
`scenes/OperationalCostIntelligence.tsx`

## 14 · Leadership Visibility — 1:43–1:49 · dark
SPD / Quality / Executive / Investor value tiers — LumenAI is the intelligence &
evidence layer, not just a borescope app. `scenes/LeadershipView.tsx`

## 15 · Close — 1:49–1:56 · dark
*One inspection becomes evidence. Evidence becomes history. History becomes
intelligence.* → LumenAI lockup + CTA. `scenes/Closing.tsx`

---

## Scene timing table (generated from `src/timing.ts`)

| # | Scene | Start | Dur (s) |
|---|-------|-------|---------|
| 1 | HiddenSurface | 0:00 | 5 |
| 2 | SPDReality | 0:05 | 5 |
| 3 | PhysicalInspection | 0:10 | 15 |
| 4 | PhysicalDigitalTransition | 0:25 | 6 |
| 5 | UniversalCapture | 0:31 | 6 |
| 6 | IntelligencePipeline | 0:37 | 10 |
| 7 | SupervisorReview | 0:47 | 13 |
| 8 | GovernedRecord | 1:00 | 8 |
| 9 | BaselineEcosystem | 1:08 | 8 |
| 10 | InspectionHistory | 1:16 | 7 |
| 11 | DepartmentTrends | 1:23 | 6 |
| 12 | InstrumentFamilyIntelligence | 1:29 | 6 |
| 13 | OperationalCostIntelligence | 1:35 | 8 |
| 14 | LeadershipView | 1:43 | 6 |
| 15 | Closing | 1:49 | 7 |

**Total:** 3,480 frames · 116.0s.
