# LumenAI Explainer — SPD Shot List (real footage)

A production-ready shot list for filming the real technician/borescope explainer that
drops into the `/video` page via `VITE_EXPLAINER_VIDEO_URL`. It maps 1:1 to the
ten-step workflow and to the caption cues in `frontend/public/site/lumenai-explainer.vtt`.

- **Target runtime:** ~110s (matches the current explainer). Durations below sum to ~110s.
- **Format on export:** MP4, H.264, 1080p (1920×1080), web-optimized / "faststart".
- **Aspect:** 16:9 landscape (the page frame is `aspect-video`).
- **Audio:** clean voiceover (script in `VIDEO_SCRIPT.md`) + low ambient room tone.
  The video must also make sense **muted** — every beat has on-screen text.

## PHI & safety rules (non-negotiable — keeps it consistent with the site)
- **Demo or decommissioned instruments only.** No patient-used devices on camera.
- **No patient identifiers anywhere** — trays, labels, wristbands, paperwork, monitors,
  worklists, or reflections. Blur or remove any real facility/patient detail.
- **No real facility-identifying detail** (signage, badges, room numbers) unless the
  facility approves it.
- Any on-screen software is the **demo/synthetic** view — never a live production tenant.
- Keep a persistent lower-third or corner tag: **"Demonstration — synthetic data, not for
  clinical use."**
- Follow the site's language: **assistive**, **human-reviewed**, **provisional**; never
  imply autonomous clinical decisions, FDA clearance, or HIPAA/SOC 2 certification.

## Setup / kit
- Clean decontam or inspection bench, neutral background, even lighting (softbox or
  ring light; avoid harsh glare on stainless).
- Instruments with **internal channels/lumens** (flexible + rigid examples).
- A borescope (or a stand-in scope) + monitor/tablet showing the scope feed.
- A tablet/laptop showing the **demo** LumenAI UI for the software beats.
- Tripod for locked-off shots; a slider or gimbal only if it stays subtle (no sci-fi swoops).
- Gloves + proper PPE on the technician (reads as real SPD).

## Scene-by-scene

| # | Beat | ~sec | Shot / framing | Action on camera | On-screen text (muted-safe) | Caption line |
|---|------|-----:|----------------|------------------|------------------------------|--------------|
| 0 | Title | 6 | Logo on slate-navy, or clean bench wide | Hold; gentle fade-in | **LumenAI — from instrument to governed evidence.** Demonstration — not for clinical use | "LumenAI turns lumen inspection into governed, reviewable evidence." |
| 1 | Identify the instrument | 8 | Medium over-shoulder | Tech scans/selects the instrument ID (barcode/tag) on the tablet | **1 · Identify the instrument** | "First, identify the instrument so evidence attaches to the right record." |
| 2 | Capture the lumen image | 12 | Tight insert on scope tip entering the channel + monitor feed | Tech advances borescope down the lumen; scope view on monitor | **2 · Capture the lumen image** | "Capture the internal-channel borescope image." |
| 3 | Attach metadata | 8 | Screen capture / over-shoulder of tablet | Tech taps tray, location, technician fields | **3 · Attach inspection metadata** | "Metadata — tray, location, technician — turns the image into evidence." |
| 4 | Validate evidence quality | 8 | Screen insert | UI shows a usable/blurry check; a poor frame is flagged | **4 · Validate evidence quality** | "Evidence quality is confirmed before any analysis." |
| 5 | Analyze (assistive) | 12 | Screen insert of demo result | Suggested finding + confidence appears; tech reads it | **5 · Assistive analysis — it suggests, a person decides** | "Assistive analysis suggests finding categories — it never decides." |
| 6 | Compare with baseline | 12 | Split-screen: current vs approved baseline | Side-by-side comparison on screen | **6 · Compare with an approved baseline** | "When an approved baseline exists, review side by side." |
| 7 | Provisional / final ranking | 8 | Screen insert | UI shows "Provisional — a person owns the final call" | **7 · Provisional result — not final** | "A provisional result is produced according to review status." |
| 8 | Route for human review | 12 | Two-shot: technician hands off to reviewer | Uncertain/high-risk case routed; reviewer looks at it | **8 · Route for qualified human review** | "Uncertain or higher-risk findings route to a qualified reviewer." |
| 9 | Record governed evidence | 8 | Screen insert of audit trail | Evidence, decision, timestamp written | **9 · Record governed evidence** | "Evidence, decisions and timestamps are written to the audit trail." |
| 10 | Reports & insights | 8 | Screen insert of report/trend | Report + trend view | **10 · Generate reports & insights** | "Reports and trends turn inspections into operational visibility." |
| 11 | Oversight / close | 8 | Reviewer + technician, or logo | Hold on the human decision | **Human oversight, built in.** Not a replacement for IFUs or qualified review | "Analysis is assistive; qualified people make the final decision." |

## After filming
1. Edit to ~110s; keep cuts calm and clinical (no fast whip-cuts, no neon).
2. Burn in (or overlay) the on-screen text + the persistent "Demonstration" tag.
3. Export MP4 (H.264, 1080p, faststart).
4. Update `frontend/public/site/lumenai-explainer.vtt` so the caption timings match your
   final edit (the player shows these as CC).
5. Host the MP4 at a direct URL and set `VITE_EXPLAINER_VIDEO_URL` (+ optional
   `VITE_EXPLAINER_POSTER_URL`) in the Render static-site env, then redeploy. The `/video`
   page swaps the animated storyboard for your real video automatically.
