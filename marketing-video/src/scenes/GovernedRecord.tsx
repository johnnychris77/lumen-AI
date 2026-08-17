import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 8 — Governed Inspection Record (closed loop).
 * The technician's inspection, evidence, AI-assisted information, baseline
 * comparison, supervisor review, disposition, and audit history combine into a
 * single governed, auditable inspection record.
 */
export const GovernedRecord: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const recordIn = reveal(frame, durationInFrames * 0.55, 16);
  const converge = progress(frame, durationInFrames * 0.5, durationInFrames * 0.66);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 60, left: 100 }}>
        <Kicker>Traceable · Reviewable · Governed</Kicker>
      </div>

      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center" }}>
        {/* inputs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 11, marginLeft: 100 }}>
          {demo.recordInputs.map((label, i) => {
            const r = reveal(frame, 6 + i * (fps * 0.14), 12);
            return (
              <div key={label} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, display: "flex", alignItems: "center", gap: 12, background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.08)`, borderRadius: theme.radius.md, padding: "11px 20px", width: 460 }}>
                <span style={{ width: 9, height: 9, borderRadius: 999, background: theme.color.primary }} />
                <span style={{ fontSize: 19, color: theme.color.onDark, fontWeight: 500 }}>{label}</span>
              </div>
            );
          })}
        </div>

        {/* converge */}
        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <WorkflowArrow direction="right" length={90} progress={converge} color={theme.color.teal} />
        </div>

        {/* governed record */}
        <div style={{ marginRight: 120 }}>
          <div style={{ opacity: recordIn.opacity, transform: `translateY(${recordIn.translateY}px)`, width: 380, padding: "30px 30px", borderRadius: theme.radius.lg, background: "linear-gradient(180deg, rgba(46,125,175,0.22), rgba(59,182,166,0.14))", border: `1px solid rgba(59,182,166,0.55)`, textAlign: "center" }}>
            <svg width={44} height={44} viewBox="0 0 24 24" fill="none" stroke={theme.color.teal} strokeWidth={1.6} style={{ margin: "0 auto 10px" }}>
              <path d="M6 3 h9 l3 3 v15 H6 Z" strokeLinejoin="round" />
              <path d="M9 12 l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div style={{ fontSize: 25, fontWeight: 700, color: theme.color.onDark }}>Governed Inspection Record</div>
            <div style={{ fontSize: 16, color: theme.color.onDarkSoft, marginTop: 8 }}>Hash-chained audit history · reviewable over time</div>
          </div>
        </div>
      </div>
    </Stage>
  );
};
