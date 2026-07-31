# LumenAI Explainer — Storyboard & Production Guide

Scene-by-scene storyboard for the ~110s explainer. The site renders an
interactive, captioned preview of this at `/site/video`
(`components/VideoStoryboard.tsx`), driven by `lib/content.ts` `VIDEO_SCENES`.

## Scene-by-scene

| # | Time | On-screen text | Animation direction | Product screen to capture |
|---|---|---|---|---|
| 1 | 0:00–0:12 | "See what traditional inspection cannot." | Camera glides from an instrument's exterior into its dark internal channel. | — (motion graphic) |
| 2 | 0:12–0:24 | "Scattered images. Spreadsheets. Paper logs." | Disconnected borescope thumbnails and spreadsheet rows drift apart. | — |
| 3 | 0:24–0:36 | "LumenAI — inspection, evidence, decision support." | Scattered pieces assemble into the LumenAI interface. | `/site` hero or app dashboard (synthetic) |
| 4 | 0:36–0:48 | "Identify · Capture · Attach metadata." | Instrument selected; image framed; metadata fields fill in. | New-inspection capture screen (demo data) |
| 5 | 0:48–1:00 | "Assistive analysis. Human confirmed." | Subtle highlight on the image; a persistent "review required" tag. **No magic-AI FX.** | AI-suggestion panel with the review tag |
| 6 | 1:00–1:11 | "Current vs. approved baseline." | Two panels slide together into a side-by-side. | Baseline comparison view (demo) |
| 7 | 1:11–1:22 | "Routed to human review." | A card slides into a reviewer queue. | Findings/review queue (demo) |
| 8 | 1:22–1:34 | "Evidence. Rationale. Audit trail." | A hash-chained timeline of events builds up. | Audit/evidence timeline (demo) |
| 9 | 1:34–1:44 | "From findings to intelligence." | Points aggregate into clean trend lines. | `/site/platform` dashboard preview |
| 10 | 1:44–1:50 | "Better visibility. Better evidence. Better decisions." | Wordmark resolves on a calm indigo gradient. | LumenAI wordmark |

## Voiceover timing

Total ~110s. Per-scene seconds are in `VIDEO_SCENES` (`content.ts`) and match
the `.vtt`. Leave ~0.5s of air between scenes; do not rush Scenes 5 and 7.

## Suggested animations

Ease-in-out, 300–500ms transitions. Prefer slides, cross-fades, and
build-on timelines. **Avoid**: glowing brains, humanoid robots, neon, sci-fi
HUDs, fast strobing. Respect reduced-motion in any web embed.

## Background music

Calm, modern, minimal — soft piano/pad bed at low level, gentle forward pulse
from Scene 3. Duck under narration (-18 to -20 dB). Resolve on Scene 10. Use a
royalty-free/licensed track; document the license in `ASSET_INVENTORY.md`.

## Thumbnail concept

Dark borescope-into-lumen image on the left; on the right, the LumenAI wordmark
over "See what traditional inspection cannot." Indigo (#4f46e5) accent. A
reusable 1200×630 version already exists at
`frontend/public/site/social-card.svg`.

## Captions

`frontend/public/site/lumenai-explainer.vtt` (WebVTT) — timings match this
storyboard. Convert to SRT with `ffmpeg -i lumenai-explainer.vtt subs.srt` if a
platform needs SRT.

## Production approach (choose one; nothing lands in the backend)

1. **Remotion (recommended for programmatic):** create a separate project at
   repo root `marketing-video/` (`npx create-video@latest`), model each scene as
   a `<Sequence>` using `VIDEO_SCENES` values, render with
   `npx remotion render src/index.ts LumenAI out/lumenai-explainer.mp4`. Keep its
   dependencies out of `frontend/` and `backend/`.
2. **Screen capture + motion graphics:** record the demo screens listed above
   (using synthetic data only), overlay on-screen text, assemble in any editor.
3. **SVG/CSS storyboard export:** the `/site/video` preview can be screen-
   captured scene-by-scene as a lightweight prototype.

### Final composition (FFmpeg)

```bash
# Mux narration + music bed under video, burn in nothing (captions stay soft):
ffmpeg -i video.mp4 -i vo.wav -i music.wav \
  -filter_complex "[2:a]volume=0.12[m];[1:a][m]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac \
  lumenai-explainer.mp4
```

## Export deliverables

- `lumenai-explainer.mp4` — 1080p, H.264, ~110s (primary).
- `lumenai-explainer-720.mp4` — 720p (email/light embeds).
- `lumenai-explainer.vtt` — captions (already in repo).
- `lumenai-explainer-thumb.png` — 1280×720 thumbnail (from social card).

## Current production status

Script, storyboard, captions, thumbnail source, and an interactive
storyboard-based preview on the site are **complete**. Rendering a final MP4 is
**pending** — it requires media assets (VO recording, licensed music) and a
render pass (Remotion or an editor), which are out of scope for the repository
build. All prerequisites needed to produce it are in this folder.
