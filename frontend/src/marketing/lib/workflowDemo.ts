/**
 * Pure state machine for the interactive workflow demonstration.
 *
 * Kept free of React so it can be unit-tested and reused. All data here is
 * SYNTHETIC and labeled "Demonstration Data — Not for Clinical Use". The demo
 * never calls the production API and never touches real inspection data.
 */

export interface DemoInstrument {
  id: string;
  name: string;
  type: string;
  channelMm: number;
}

export const DEMO_INSTRUMENTS: DemoInstrument[] = [
  { id: "DEMO-FLEX-014", name: "Flexible suction instrument (demo)", type: "Flexible lumened", channelMm: 3.2 },
  { id: "DEMO-RIGID-208", name: "Rigid arthroscopy cannula (demo)", type: "Rigid lumened", channelMm: 4.0 },
  { id: "DEMO-ROBOT-051", name: "Robotic wristed instrument (demo)", type: "Articulating lumened", channelMm: 2.4 },
];

export interface DemoImage {
  id: string;
  label: string;
  /** Drives the synthetic finding + baseline result deterministically. */
  seed: "clean" | "debris" | "corrosion";
}

export const DEMO_IMAGES: DemoImage[] = [
  { id: "img-clean", label: "Sample A — channel appears clear", seed: "clean" },
  { id: "img-debris", label: "Sample B — possible residual debris", seed: "debris" },
  { id: "img-corrosion", label: "Sample C — possible surface corrosion", seed: "corrosion" },
];

export const DEMO_STEPS = [
  "select-instrument",
  "select-image",
  "metadata",
  "analyze",
  "compare",
  "review",
  "record",
  "report",
] as const;

export type DemoStepId = (typeof DEMO_STEPS)[number];

export interface DemoMetadata {
  tray: string;
  location: string;
  technician: string;
}

export const DEFAULT_METADATA: DemoMetadata = {
  tray: "TRAY-DEMO-77",
  location: "Decontam Station 3 (demo)",
  technician: "Demo Technician",
};

export interface DemoState {
  stepIndex: number;
  instrument?: DemoInstrument;
  image?: DemoImage;
  metadata: DemoMetadata;
}

export const initialDemoState: DemoState = {
  stepIndex: 0,
  metadata: DEFAULT_METADATA,
};

export function currentStep(state: DemoState): DemoStepId {
  return DEMO_STEPS[state.stepIndex];
}

/** Whether the user has supplied enough to advance from the current step. */
export function canAdvance(state: DemoState): boolean {
  switch (currentStep(state)) {
    case "select-instrument":
      return Boolean(state.instrument);
    case "select-image":
      return Boolean(state.image);
    default:
      return state.stepIndex < DEMO_STEPS.length - 1;
  }
}

export function advance(state: DemoState): DemoState {
  if (!canAdvance(state)) return state;
  return { ...state, stepIndex: Math.min(state.stepIndex + 1, DEMO_STEPS.length - 1) };
}

export function back(state: DemoState): DemoState {
  return { ...state, stepIndex: Math.max(state.stepIndex - 1, 0) };
}

export function reset(): DemoState {
  return { ...initialDemoState, metadata: { ...DEFAULT_METADATA } };
}

export interface DemoFinding {
  category: string;
  confidence: number; // 0..1, SYNTHETIC
  baselineMatch: "match" | "deviation" | "no-baseline";
  ranking: "provisional-pass" | "provisional-attention" | "hold-for-review";
  reviewRequired: boolean;
  rationale: string;
}

/**
 * Deterministic synthetic result derived from the chosen sample image.
 * These numbers are illustrative only — there is no clinical inference here.
 */
export function computeDemoFinding(image?: DemoImage): DemoFinding {
  switch (image?.seed) {
    case "debris":
      return {
        category: "Possible residual debris",
        confidence: 0.72,
        baselineMatch: "deviation",
        ranking: "hold-for-review",
        reviewRequired: true,
        rationale:
          "Suggested debris signal deviates from the approved baseline. Held for qualified human review — no disposition is made automatically.",
      };
    case "corrosion":
      return {
        category: "Possible surface corrosion",
        confidence: 0.58,
        baselineMatch: "deviation",
        ranking: "provisional-attention",
        reviewRequired: true,
        rationale:
          "Lower-confidence surface signal. Flagged for reviewer attention and baseline confirmation before any decision.",
      };
    case "clean":
    default:
      return {
        category: "No suggested findings above threshold",
        confidence: 0.16,
        baselineMatch: "match",
        ranking: "provisional-pass",
        reviewRequired: false,
        rationale:
          "No suggested finding exceeded the demo threshold and the image is consistent with the approved baseline. A provisional result — a person still owns the final call.",
      };
  }
}

export interface DemoReport {
  reportId: string;
  instrumentId: string;
  finding: DemoFinding;
  metadata: DemoMetadata;
  timestamp: string;
  disclaimer: string;
}

export function buildDemoReport(state: DemoState, now: Date = new Date()): DemoReport {
  const finding = computeDemoFinding(state.image);
  return {
    reportId: `DEMO-RPT-${now.getTime().toString(36).toUpperCase()}`,
    instrumentId: state.instrument?.id ?? "DEMO-UNKNOWN",
    finding,
    metadata: state.metadata,
    timestamp: now.toISOString(),
    disclaimer: "Demonstration Data — Not for Clinical Use",
  };
}
