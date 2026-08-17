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
  | "PhysicalInspection"
  | "PhysicalDigitalTransition"
  | "UniversalCapture"
  | "IntelligencePipeline"
  | "SupervisorReview"
  | "GovernedRecord"
  | "BaselineEcosystem"
  | "InspectionHistory"
  | "DepartmentTrends"
  | "InstrumentFamilyIntelligence"
  | "OperationalCostIntelligence"
  | "LeadershipView"
  | "Closing";

export interface SceneSpec {
  id: SceneId;
  /** Duration in seconds. */
  seconds: number;
  /** On-screen caption line (mirrors the SRT / voiceover). */
  caption: string;
}

/**
 * Scene order + durations. Sums to 116s (inside the 100–120s target) at 30fps.
 * The story: person → physical borescope inspection → capture inside LumenAI →
 * structured evidence → AI-assisted analysis → baseline → supervisor review →
 * governed record → history → trends → operational intelligence → leadership.
 */
export const SCENES: readonly SceneSpec[] = [
  { id: "HiddenSurface", seconds: 5, caption: "Every inspection begins with a person — and surfaces that can't always be assessed from the outside." },
  { id: "SPDReality", seconds: 5, caption: "A sterile processing professional, an instrument, and increasingly complex lumened tools to inspect." },
  { id: "PhysicalInspection", seconds: 15, caption: "Using a compatible borescope, the technician examines the lumen directly — inside LumenAI the borescope is an image source, capturing representative evidence without leaving the inspection." },
  { id: "PhysicalDigitalTransition", seconds: 6, caption: "The physical inspection becomes a structured digital record — technician, instrument, and lumen image flowing into LumenAI." },
  { id: "UniversalCapture", seconds: 6, caption: "Designed for compatible borescope and camera sources — standardized inspection evidence, and an inspection can hold several representative images." },
  { id: "IntelligencePipeline", seconds: 10, caption: "The image becomes structured evidence — image quality, AI-assisted analysis, and comparison with an available governed baseline, surfacing information for review." },
  { id: "SupervisorReview", seconds: 13, caption: "When an inspection needs review, LumenAI routes the evidence to a supervisor, who reviews images, baseline, AI-assisted observations, and history before recording the decision. AI assists. People decide." },
  { id: "GovernedRecord", seconds: 8, caption: "Inspection, evidence, AI-assisted information, baseline, supervisor review, and disposition become one governed, auditable record." },
  { id: "BaselineEcosystem", seconds: 8, caption: "Manufacturers, vendors, and organizations contribute reference information through a governed pathway — submit, verify, approve, publish. Never auto-approved." },
  { id: "InspectionHistory", seconds: 7, caption: "Each inspection becomes part of the instrument's longitudinal history — Pass, Fair, and Review results over time." },
  { id: "DepartmentTrends", seconds: 6, caption: "Across a department, that history becomes trends — Pass, Fair, and Review activity, and how complete the evidence is." },
  { id: "InstrumentFamilyIntelligence", seconds: 6, caption: "Patterns emerge across instrument families — volume, results, recurring observations, review activity, and baseline coverage." },
  { id: "OperationalCostIntelligence", seconds: 8, caption: "Documented inspections and decisions inform maintenance and replacement trends — operational and cost intelligence, evaluated with validated organizational data. Never invented savings." },
  { id: "LeadershipView", seconds: 6, caption: "The same evidence serves SPD, quality, and executive leaders — LumenAI is the intelligence and evidence layer, not just a borescope app." },
  { id: "Closing", seconds: 7, caption: "One inspection becomes evidence. Evidence becomes history. History becomes intelligence." },
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
