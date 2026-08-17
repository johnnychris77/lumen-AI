# LumenAI Explainer — Marketing Video (Remotion)

An **isolated** Remotion project that renders the official LumenAI product
explainer. It is intentionally separate from the LumenAI backend and frontend:
its own `package.json`, its own `node_modules`, no shared build, no new backend
APIs, no product capabilities added.

- **Runtime:** ~116s at 30fps (3,480 frames), inside the 100–120s target.
- **Story:** person → physical borescope inspection → capture inside LumenAI →
  AI-assisted analysis → baseline → supervisor review → governed record →
  history → trends → operational intelligence → leadership. 15 scenes.
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

## Three formats, one timeline

Scenes are authored at 1920×1080; square and vertical scale that band and center
it on a charcoal frame with format-aware captions + a brand wordmark
(`src/format.ts`, `CaptionTrack`, `BrandFurniture`) — composed social cuts, not
crops.

## Drop-in assets (no scene edits)

This project provides the **motion, structure, timing, captions, and safe
copy**. Real media and audio are wired to drop in:

- **Footage/stills** — put files in `public/media/`, set paths in `src/media.ts`
  (procedural visuals show until you do).
- **Music / voiceover** — put files in `public/audio/`, set paths in
  `src/audio.ts` (a fade + human-review duck envelope is already wired; silent
  until supplied).
- **Poster / brand font+palette** — a generated poster is committed; swap the
  font/colors in `src/theme.ts`.

See `docs/marketing/LUMENAI_VIDEO_PRODUCTION_GUIDE.md`.
