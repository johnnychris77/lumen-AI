import { staticFile } from "remotion";

/**
 * Media manifest — footage-ready, PROCEDURAL BY DEFAULT.
 *
 * Every slot is `null`, so the scenes render their built-in stylized visuals and
 * `npm run render` works with no external files. To use real footage/stills, drop
 * files into `public/media/` and set the path here (relative to `public/`).
 * `.mp4`/`.webm` render as looping <Video>; images as <Img>.
 *
 *   instrumentHero — clean instrument beauty shot (Scenes 1 & 10)
 *   lumenS1        — borescope lumen travel (Scene 1)
 *   lumenMonitor   — lumen on the SPD monitor (Scene 2)
 *   lumenFeed      — live feed inside the inspection (Scene 3)
 *   lumenCurrent   — current inspection image (Scene 5)
 *   lumenBaseline  — approved baseline image (Scene 5)
 *
 * PHI: confirm no patient/case data in any real image's pixels or metadata
 * before adding it (a LumenAI security constraint).
 */
export type MediaSlot =
  | "instrumentHero"
  | "lumenS1"
  | "lumenMonitor"
  | "lumenFeed"
  | "lumenCurrent"
  | "lumenBaseline";

export const MEDIA: Record<MediaSlot, string | null> = {
  instrumentHero: null,
  lumenS1: null,
  lumenMonitor: null,
  lumenFeed: null,
  lumenCurrent: null,
  lumenBaseline: null,
};

/** Resolve a slot to a static URL, or null if no asset is configured. */
export const mediaSrc = (slot: MediaSlot): string | null => {
  const p = MEDIA[slot];
  return p ? staticFile(p) : null;
};

export const isVideoSrc = (src: string): boolean => /\.(mp4|webm|mov)$/i.test(src);
