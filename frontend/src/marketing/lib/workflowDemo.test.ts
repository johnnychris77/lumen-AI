/**
 * Unit tests for the interactive workflow demo state machine.
 * Run with Vitest: `npm i -D vitest && npx vitest run src/marketing`
 * (see docs/marketing/DEPLOYMENT_GUIDE.md). Pure logic — no DOM needed.
 */
import { describe, it, expect } from "vitest";
import {
  DEMO_STEPS,
  advance,
  back,
  buildDemoReport,
  canAdvance,
  computeDemoFinding,
  currentStep,
  DEMO_IMAGES,
  DEMO_INSTRUMENTS,
  reset,
} from "./workflowDemo";

describe("workflow demo state machine", () => {
  it("starts at select-instrument and cannot advance without a choice", () => {
    const s = reset();
    expect(currentStep(s)).toBe("select-instrument");
    expect(canAdvance(s)).toBe(false);
    expect(advance(s)).toBe(s); // no-op when blocked
  });

  it("advances once an instrument is selected", () => {
    const s = { ...reset(), instrument: DEMO_INSTRUMENTS[0] };
    expect(canAdvance(s)).toBe(true);
    expect(currentStep(advance(s))).toBe("select-image");
  });

  it("requires an image on the select-image step", () => {
    let s = { ...reset(), instrument: DEMO_INSTRUMENTS[0] };
    s = advance(s); // -> select-image
    expect(canAdvance(s)).toBe(false);
    s = { ...s, image: DEMO_IMAGES[0] };
    expect(canAdvance(s)).toBe(true);
  });

  it("back() never goes below zero and advance() never exceeds the last step", () => {
    const s = reset();
    expect(back(s).stepIndex).toBe(0);
    const last = { ...s, stepIndex: DEMO_STEPS.length - 1 };
    expect(advance(last).stepIndex).toBe(DEMO_STEPS.length - 1);
  });
});

describe("synthetic finding computation", () => {
  it("clean sample does not require review", () => {
    const f = computeDemoFinding(DEMO_IMAGES.find((i) => i.seed === "clean"));
    expect(f.reviewRequired).toBe(false);
    expect(f.baselineMatch).toBe("match");
    expect(f.ranking).toBe("provisional-pass");
  });

  it("debris sample deviates from baseline and holds for review", () => {
    const f = computeDemoFinding(DEMO_IMAGES.find((i) => i.seed === "debris"));
    expect(f.reviewRequired).toBe(true);
    expect(f.baselineMatch).toBe("deviation");
    expect(f.ranking).toBe("hold-for-review");
    expect(f.confidence).toBeGreaterThan(0.5);
  });
});

describe("report", () => {
  it("always carries the not-for-clinical-use disclaimer", () => {
    const s = { ...reset(), instrument: DEMO_INSTRUMENTS[0], image: DEMO_IMAGES[1] };
    const r = buildDemoReport(s, new Date("2026-01-01T00:00:00Z"));
    expect(r.disclaimer).toMatch(/Not for Clinical Use/i);
    expect(r.instrumentId).toBe(DEMO_INSTRUMENTS[0].id);
    expect(r.reportId).toMatch(/^DEMO-RPT-/);
  });
});
