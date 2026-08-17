# LumenAI Explainer — Storyboard

Ten scenes. Timecodes and durations come from `src/timing.ts` (the single
source of truth); change them there, not here. Total ~95s at 30fps.

The narrative transformation the film delivers:

```
Physical Instrument → Borescope Image → Structured Inspection →
AI-Assisted Analysis → Approved Baseline Comparison → Qualified Human Review →
Governed Evidence → Instrument History → Operational Intelligence
```

---

## 1 · Hidden Surface — 0:00–0:08 · dark
- **Visual:** Clean instrument slowly rotates; camera pushes toward the distal opening and travels into the internal lumen. Subtle, realistic surface variation (discoloration, fine scratches). Not dramatic.
- **On-screen:** *What happens inside the instrument matters.*
- **File:** `scenes/HiddenSurface.tsx` · **Motion:** slow push-in + rotate, cross-fade external→interior.
- **Asset to swap:** photoreal instrument + real borescope lumen footage.

## 2 · Today's Inspection Reality — 0:08–0:18 · dark
- **Visual:** Modern SPD. A sequence of complex instruments (suction, cannulated ortho, drill/reamer, rigid scope, flexible scope). Technician connects a borescope; internal channel appears on a monitor.
- **On-screen:** *Inspection → Evidence → Decision.*
- **Principle:** the technician is the expert; technology supports the technician.
- **File:** `scenes/SPDReality.tsx`.

## 3 · Introduce LumenAI — 0:18–0:29 · light (app UI)
- **Visual:** LumenAI New Inspection screen. **Add Inspection Image** → source selector (**Capture from Borescope** / **Upload Existing Image**) → user selects *Capture from Borescope* → a **live borescope feed opens inside the inspection**.
- **On-screen:** *Capture where the work happens.*
- **Must:** no separate borescope app. The borescope is an image source; LumenAI owns the workflow.
- **File:** `scenes/ImageAcquisition.tsx`.

## 4 · Universal Image Acquisition — 0:29–0:36 · dark
- **Visual:** Multiple **compatible** sources (USB borescope, external camera, capture device, existing image) converge into **LumenAI Image Acquisition** → **Standardized Inspection Evidence**.
- **On-screen:** *Vendor-neutral image acquisition.*
- **Claim guard:** "Designed for compatible borescope and camera sources." Never "works with every borescope."
- **File:** `scenes/UniversalCapture.tsx`.

## 5 · Image Becomes Intelligence — 0:36–0:48 · dark
- **Visual:** Four stages — **Image Quality → AI-Assisted Analysis → Baseline Comparison → Review Routing**. Then restrained **Current Inspection | Approved Baseline** side-by-side with subtle areas of interest (not bounding boxes everywhere).
- **On-screen:** *From image to structured evidence.*
- **Safety language:** AI-assisted, support, surface, compare. Never diagnose / certify / guarantee clean / determine patient safety.
- **File:** `scenes/IntelligencePipeline.tsx`.

## 6 · Human Authority — 0:48–0:58 · dark *(key moment)*
- **Visual:** **Review Required · Provisional Result.** Workflow pauses. A qualified reviewer examines current image, baseline, findings, evidence. Resolve to the line.
- **On-screen:** **AI assists. People decide.**
- **File:** `scenes/HumanReview.tsx` · music dips under the line.

## 7 · Evidence Governance — 0:58–1:09 · dark
- **Visual:** Zoom out; the record expands into a connected, timestamped chain — Instrument → Inspection → Captured Image → Baseline → Finding → Human Review → Audit Record → Report. A digital timeline (Inspection 001–004) builds.
- **On-screen:** *Traceable. Reviewable. Governed.*
- **File:** `scenes/EvidenceGovernance.tsx`.

## 8 · The Baseline Ecosystem — 1:09–1:20 · dark
- **Visual:** Manufacturer · Vendor · Healthcare Organization connect through central **LumenAI** (Baseline Governance · Inspection Evidence · Instrument History). Then **Submit → Verify → Approve → Publish**.
- **Must:** uploads do NOT automatically become approved baselines.
- **File:** `scenes/BaselineEcosystem.tsx`.

## 9 · From One Instrument to Organizational Intelligence — 1:20–1:29 · dark
- **Visual:** One record becomes many; individual records organize into an executive dashboard with restrained metrics (inspection activity, review activity, baseline coverage, instrument families, finding trends, evidence completeness).
- **On-screen:** *Inspection Intelligence.*
- **File:** `scenes/OperationalIntelligence.tsx`.

## 10 · Close — 1:29–1:35 · dark
- **Visual:** Return to the instrument, now wrapped in a subtle evidence history; resolve to the LumenAI lockup + CTA.
- **On-screen:** LumenAI · Inspection Intelligence for Sterile Processing · *See more. Know more. Document what matters.* · Request a Demonstration · `lumenai.opsbridgesolution.com`.
- **File:** `scenes/Closing.tsx`.

---

## Scene timing table (generated from `src/timing.ts`)

| # | Scene | Start | Dur (s) | Frames @30 |
|---|-------|-------|---------|------------|
| 1 | HiddenSurface | 0:00 | 8 | 0–240 |
| 2 | SPDReality | 0:08 | 10 | 240–540 |
| 3 | ImageAcquisition | 0:18 | 11 | 540–870 |
| 4 | UniversalCapture | 0:29 | 7 | 870–1080 |
| 5 | IntelligencePipeline | 0:36 | 12 | 1080–1440 |
| 6 | HumanReview | 0:48 | 10 | 1440–1740 |
| 7 | EvidenceGovernance | 0:58 | 11 | 1740–2070 |
| 8 | BaselineEcosystem | 1:09 | 11 | 2070–2400 |
| 9 | OperationalIntelligence | 1:20 | 9 | 2400–2670 |
| 10 | Closing | 1:29 | 6 | 2670–2850 |

**Total:** 2,850 frames · 95.0s.
