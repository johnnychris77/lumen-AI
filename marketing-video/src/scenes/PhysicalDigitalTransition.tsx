import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";

/**
 * Scene 4 — Physical / Digital transition (core concept).
 * The physical inspection (Technician → Instrument → Borescope → Lumen Image)
 * flows into LumenAI's digital intelligence layer (Structured Inspection →
 * Analysis → Baseline → Review → Evidence).
 */
const PHYSICAL = ["Technician", "Instrument", "Borescope", "Internal Lumen Image"];
const DIGITAL = ["LumenAI", "Structured Inspection", "Analysis", "Baseline", "Review", "Evidence"];

export const PhysicalDigitalTransition: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const bridge = progress(frame, durationInFrames * 0.42, durationInFrames * 0.66);

  return (
    <Stage mode="dark">
      <Column x={130} title="Physical World" items={PHYSICAL} frame={frame} fps={fps} startDelay={6} accent={theme.color.primary} />

      {/* bridge */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 300, display: "flex", justifyContent: "center", alignItems: "center", gap: 16 }}>
        <div style={{ width: 120, height: 3, background: `linear-gradient(90deg, ${theme.color.primary}, ${theme.color.teal})`, opacity: bridge, transformOrigin: "left", transform: `scaleX(${bridge})` }} />
        <div style={{ opacity: bridge, color: theme.color.onDarkSoft, fontSize: 16, fontWeight: 600, letterSpacing: 1 }}>becomes</div>
        <WorkflowArrow direction="right" length={60} progress={bridge} color={theme.color.teal} />
      </div>

      <Column x={undefined} right={130} title="Digital Intelligence Layer" items={DIGITAL} frame={frame} fps={fps} startDelay={durationInFrames * 0.5} accent={theme.color.teal} />
    </Stage>
  );
};

const Column: React.FC<{
  x?: number;
  right?: number;
  title: string;
  items: readonly string[];
  frame: number;
  fps: number;
  startDelay: number;
  accent: string;
}> = ({ x, right, title, items, frame, fps, startDelay, accent }) => (
  <div style={{ position: "absolute", top: 90, left: x, right, width: 520 }}>
    <Kicker>{title}</Kicker>
    <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 18 }}>
      {items.map((label, i) => {
        const r = reveal(frame, startDelay + i * (fps * 0.16), 12);
        return (
          <div
            key={label}
            style={{
              opacity: r.opacity,
              transform: `translateY(${r.translateY}px)`,
              display: "flex",
              alignItems: "center",
              gap: 14,
              background: theme.color.charcoalPanel,
              border: `1px solid rgba(255,255,255,0.08)`,
              borderRadius: theme.radius.md,
              padding: "13px 20px",
            }}
          >
            <span style={{ width: 10, height: 10, borderRadius: 999, background: accent }} />
            <span style={{ fontSize: 21, fontWeight: 600, color: theme.color.onDark }}>{label}</span>
          </div>
        );
      })}
    </div>
  </div>
);
