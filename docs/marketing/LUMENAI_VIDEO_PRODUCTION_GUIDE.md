# LumenAI Explainer — Production Guide

How to build, preview, render, and ship the explainer. The project lives in
`marketing-video/` and is fully isolated from the LumenAI app (own
`package.json` / `node_modules`, no shared build, no backend changes).

## 1. Architecture

- **Engine:** Remotion + React (TypeScript).
- **Timing:** centralized in `src/timing.ts` — scene order and durations in one
  place. Components never hard-code frame offsets; they read `useVideoConfig()`
  and the timing table. The captions and storyboard tables derive from the same
  numbers.
- **Design system:** `src/theme.ts` (charcoal cinematic + clinical light,
  restrained blue/teal accents), `Stage`/`Panel`/`Kicker` primitives.
- **Reusable components:** `Caption`, `DeviceSource`, `EvidenceNode`,
  `WorkflowArrow`, `InstrumentCard`, plus `LumenImage` (procedural lumen view)
  and `anim.ts` helpers (`reveal`, `fadeInOut`, `softSpring`, `progress`).
- **Scenes:** 10 files in `src/scenes/`, one per storyboard beat.
- **Composition:** `src/compositions/LumenAIExplainer.tsx` maps the timing table
  to `<Sequence>`s and overlays captions. `src/Root.tsx` registers three sizes.

## 2. Commands

```bash
cd marketing-video
npm install
npm run typecheck     # tsc --noEmit   (passes)
npm run lint          # eslint src     (passes)
npm run dev           # Remotion Studio — scrub every scene interactively
```

## 3. Rendering

Remotion drives a headless Chromium. It must be the **old-headless**
`chrome-headless-shell` build (full Chrome's old-headless mode is removed).

```bash
# Point Remotion at a chrome-headless-shell binary (no download):
export REMOTION_BROWSER_EXECUTABLE=/path/to/chrome-headless-shell

npm run preview          # 960x540 proof of the FULL timeline
npm run render           # 1920x1080  -> out/lumenai-explainer-1920x1080.mp4
npm run render:square    # 1080x1080  -> out/lumenai-explainer-1080x1080.mp4
npm run render:vertical  # 1080x1920  -> out/lumenai-explainer-1080x1920.mp4
npm run render:all
```

`remotion.config.ts` reads `REMOTION_BROWSER_EXECUTABLE` and applies it via
`Config.setBrowserExecutable`, so the env var is all you need. Concurrency is set
to 2 for constrained environments; raise it on a bigger machine.

> In this repo's container, the pre-installed headless shell is at
> `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`.
> That value was used to render the low-res preview successfully.

## 4. Delivery sizes

| Size | Composition id | Use |
|------|----------------|-----|
| 1920×1080 | `LumenAIExplainer` | website / YouTube (primary) |
| 1080×1080 | `LumenAIExplainerSquare` | LinkedIn / social feed |
| 1080×1920 | `LumenAIExplainerVertical` | vertical / stories |

All three share one composition and one timeline. Scenes are authored on a fixed
1920×1080 **design canvas** (`src/format.ts`); square and vertical **scale that
canvas to the target width and center it** on a charcoal frame, then place the
caption in the format's lower safe area and a small LumenAI wordmark in the top
area (`CaptionTrack` + `BrandFurniture`). So the social cuts are intentionally
composed, not naively cropped or stretched. To change how a format frames, edit
`src/format.ts` / those two components — the scenes and timing stay untouched.

## 5. Assets still required (this repo ships motion + structure, not final media)

1. **Photoreal footage / stills** to replace the procedural placeholders. This
   is now **drop-in** via the media manifest — no scene edits needed:
   - put files in `public/media/`;
   - set the path in `src/media.ts` (`instrumentHero`, `lumenS1`, `lumenMonitor`,
     `lumenFeed`, `lumenCurrent`, `lumenBaseline`). `.mp4`/`.webm` render as
     `<Video>`, images as `<Img>`, clipped into the existing framing.
   Every slot is `null` by default, so renders work with zero assets and the
   procedural visuals show until you supply real ones. **No PHI in pixels or
   metadata** before adding any real image.
2. **Poster image** for the web player: `web-embed/assets/poster.jpg` (a
   generated one is committed; replace with a final art poster).
3. **Music bed** and **voiceover** — now **wired** in `src/audio.ts` and inert
   until supplied: drop `public/audio/music.mp3` and/or `public/audio/vo.mp3`
   and set the paths in the `AUDIO` manifest. A volume envelope (fade in/out +
   a **duck under the human-review scene**) is already implemented and stays in
   sync with `src/timing.ts`. **Sound design** (subtle sfx) can be added the
   same way.
4. **Brand fonts / exact brand hex**: the theme uses a system font stack and
   restrained clinical colors as safe defaults; replace with the official
   LumenAI palette/typeface when available (self-host the font, no CDN).
5. **Voiceover track** recorded from `LUMENAI_VIDEO_SCRIPT.md`.

## 6. Website integration

Use `marketing-video/web-embed/lumenai-video-embed.html` as the reference
player. It:

- **lazy-loads** (the `<video>` is only created on a real click of the poster),
- ships **captions** (`<track kind="captions">` → the WebVTT file),
- includes a full **transcript** in a `<details>` block,
- provides a **poster** image,
- **never autoplays with sound** (playback starts on the user gesture),
- respects **`prefers-reduced-motion`** (no animated poster, no autoplay),
- is **mobile-friendly** (responsive 16:9, `playsinline`).

Point `data-src` at your hosted MP4, `poster` at your poster image, and the
`<track src>` at `public/captions/lumenai-explainer.vtt`.

## 7. Caption files

- `public/captions/lumenai-explainer.srt` — the deliverable SRT.
- `public/captions/lumenai-explainer.vtt` — WebVTT for the HTML `<track>`
  (browsers don't load SRT natively). Both are generated from the same script
  and the `src/timing.ts` windows; keep them in sync if timing changes.

## 8. Known limitations

- The lumen/instrument visuals are **stylized placeholders** until real footage
  is supplied via the media manifest (§5).
- No audio is bundled; the mix is wired but silent until `music.mp3`/`vo.mp3`
  are added (§5).
- Square/vertical present the landscape design **scaled + centered** with
  format-aware captions/branding (§4). This is a deliberate, clean social frame;
  a per-scene portrait re-layout (not just framing) is a possible future step.
- The theme uses a system font stack + safe clinical colors as defaults; swap in
  the official brand font/palette (self-hosted) in `src/theme.ts`.
