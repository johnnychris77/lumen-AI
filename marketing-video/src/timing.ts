/**
 * Centralized scene timing — the SINGLE source of truth for the composition.
 *
 * Component code must NOT hard-code frame offsets; it reads durations/order
 * from here. Change a scene's length in one place and the whole film re-flows,
 * and the caption timings + docs are generated from the same numbers.
 */
export const FPS = 30;

export const SIZES = {
  landscape: { id: "LumenAIExplainer", width: 1920, height: 1080 },
  square: { id: "LumenAIExplainerSquare", width: 1080, height: 1080 },
  vertical: { id: "LumenAIExplainerVertical", width: 1080, height: 1920 },
} as const;

export type SceneId =
  | "HiddenSurface"
  | "SPDReality"
  | "ImageAcquisition"
  | "UniversalCapture"
  | "IntelligencePipeline"
  | "HumanReview"
  | "EvidenceGovernance"
  | "BaselineEcosystem"
  | "OperationalIntelligence"
  | "Closing";

export interface SceneSpec {
  id: SceneId;
  /** Duration in seconds. */
  seconds: number;
  /** On-screen caption line (mirrors the SRT / voiceover). */
  caption: string;
}

/**
 * Scene order + durations. Sums to 95s (inside the 85–95s target) at 30fps.
 */
export const SCENES: readonly SceneSpec[] = [
  { id: "HiddenSurface", seconds: 8, caption: "Some of the most important surfaces of a surgical instrument are also the hardest to see." },
  { id: "SPDReality", seconds: 10, caption: "Sterile processing professionals inspect increasingly complex instruments. But seeing the image is only the beginning." },
  { id: "ImageAcquisition", seconds: 11, caption: "LumenAI brings image acquisition directly into the inspection workflow — capture from a compatible borescope or use an existing image without leaving the inspection." },
  { id: "UniversalCapture", seconds: 7, caption: "The acquisition layer is designed around compatible image sources — not a single borescope manufacturer." },
  { id: "IntelligencePipeline", seconds: 12, caption: "The image becomes structured evidence. LumenAI can support image assessment, surface visible findings, and compare with an approved baseline when one is available." },
  { id: "HumanReview", seconds: 10, caption: "When uncertainty or defined review criteria are present, LumenAI routes the inspection for qualified human review. AI assists. People decide." },
  { id: "EvidenceGovernance", seconds: 11, caption: "Each inspection can become part of a traceable record — connecting the instrument, image, baseline, findings, review history, and audit evidence over time." },
  { id: "BaselineEcosystem", seconds: 11, caption: "LumenAI creates a governed pathway for manufacturers, vendors, and healthcare organizations to contribute and use trusted reference information." },
  { id: "OperationalIntelligence", seconds: 9, caption: "What begins with one inspection can become operational intelligence — patterns across instruments, departments, and time." },
  { id: "Closing", seconds: 6, caption: "LumenAI. Inspection intelligence for Sterile Processing." },
] as const;

export const secToFrames = (s: number): number => Math.round(s * FPS);

export interface SceneWindow extends SceneSpec {
  index: number;
  from: number;
  durationInFrames: number;
  to: number;
}

/** Resolve every scene to an absolute frame window. */
export const SCENE_WINDOWS: readonly SceneWindow[] = (() => {
  let cursor = 0;
  return SCENES.map((s, index) => {
    const durationInFrames = secToFrames(s.seconds);
    const win: SceneWindow = {
      ...s,
      index,
      from: cursor,
      durationInFrames,
      to: cursor + durationInFrames,
    };
    cursor += durationInFrames;
    return win;
  });
})();

export const TOTAL_FRAMES = SCENE_WINDOWS.reduce(
  (acc, s) => acc + s.durationInFrames,
  0,
);

export const TOTAL_SECONDS = TOTAL_FRAMES / FPS;
