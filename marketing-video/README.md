# LumenAI Explainer — Marketing Video (Remotion)

An **isolated** Remotion project that renders the official ~90-second LumenAI
product explainer. It is intentionally separate from the LumenAI backend and
frontend: its own `package.json`, its own `node_modules`, no shared build, no
new backend APIs, no product capabilities added.

- **Runtime:** ~95s at 30fps (2,850 frames), inside the 85–95s target.
- **Primary output:** 1920×1080 (`LumenAIExplainer`).
- **Also:** 1080×1080 square, 1080×1920 vertical (same composition, centralized timing).

## Quick start

```bash
cd marketing-video
npm install
npm run typecheck        # tsc --noEmit
npm run lint             # eslint src
npm run dev              # Remotion Studio (interactive preview)
```

## Rendering

Remotion needs a Chromium. In CI/containers where one is pre-installed, point
Remotion at it (no download):

```bash
export REMOTION_BROWSER_EXECUTABLE=/path/to/chrome     # optional
npm run preview          # fast low-res proof (960×540)
npm run render           # 1920×1080 -> out/lumenai-explainer-1920x1080.mp4
npm run render:square    # 1080×1080
npm run render:vertical  # 1080×1920
npm run render:all
```

## Where things live

```
src/
  timing.ts                 # SINGLE source of truth for scene order + durations
  theme.ts                  # design tokens (charcoal / clinical / restrained accents)
  data/demo.ts              # synthetic demo content ONLY (no PHI, no real data)
  components/                # Caption, DeviceSource, EvidenceNode, WorkflowArrow,
                             #   InstrumentCard, Stage, LumenImage, anim helpers
  scenes/                    # 10 scenes (1 file each)
  compositions/LumenAIExplainer.tsx  # stitches scenes + captions
  Root.tsx / index.ts        # registers the 3 sizes
public/captions/             # lumenai-explainer.srt (+ .vtt for web <track>)
web-embed/                   # accessible, lazy-loading HTML player
```

Change a scene's length in **one** place (`src/timing.ts`) and the whole film,
the captions, and the docs stay in sync.

## Not included (assets to supply)

This project provides the **motion, structure, timing, captions, and safe
copy**. Photoreal instrument/lumen footage, the music bed, sound design, a
poster image, and final brand fonts/colors are production assets to drop in —
see `docs/marketing/LUMENAI_VIDEO_PRODUCTION_GUIDE.md`.
