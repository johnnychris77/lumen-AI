import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { EvidenceNode } from "../components/EvidenceNode";
import { InstrumentCard } from "../components/InstrumentCard";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 7 — Evidence Governance (0:58–1:09).
 * The record expands into a connected, timestamped evidence chain; a digital
 * timeline of inspections builds alongside. Traceable. Reviewable. Governed.
 */
const TIMES = ["09:41:02", "09:41:04", "09:41:07", "09:41:10", "09:41:15", "09:42:01", "09:42:03", "09:42:05"];

export const EvidenceGovernance: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 64, left: 100 }}>
        <Kicker>Traceable. Reviewable. Governed.</Kicker>
      </div>

      {/* Evidence chain */}
      <div style={{ position: "absolute", top: 140, left: 100, display: "flex", flexDirection: "column", gap: 12 }}>
        {demo.evidenceChain.map((label, i) => {
          const r = reveal(frame, 6 + i * (fps * 0.18), 12);
          return (
            <EvidenceNode
              key={label}
              label={label}
              timestamp={TIMES[i]}
              opacity={r.opacity}
              translateY={r.translateY}
              emphasis={label === "Human Review"}
            />
          );
        })}
      </div>

      {/* Timeline of inspections */}
      <div style={{ position: "absolute", top: 200, right: 110, width: 560 }}>
        <div style={{ fontSize: 20, color: theme.color.onDarkSoft, marginBottom: 18 }}>Longitudinal record</div>
        <div style={{ position: "relative", paddingLeft: 26 }}>
          <div
            style={{
              position: "absolute",
              left: 8,
              top: 0,
              bottom: 0,
              width: 2,
              background: "rgba(255,255,255,0.14)",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 8,
              top: 0,
              width: 2,
              height: `${progress(frame, durationInFrames * 0.35, durationInFrames * 0.9) * 100}%`,
              background: theme.color.teal,
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {demo.inspections.map((ins, i) => {
              const r = reveal(frame, durationInFrames * 0.4 + i * (fps * 0.28), 12);
              return (
                <div key={ins.id} style={{ position: "relative" }}>
                  <span
                    style={{
                      position: "absolute",
                      left: -22,
                      top: 22,
                      width: 12,
                      height: 12,
                      borderRadius: 999,
                      background: r.opacity > 0.5 ? theme.color.teal : theme.color.inkFaint,
                    }}
                  />
                  <InstrumentCard id={ins.id} status={ins.status} opacity={r.opacity} translateY={r.translateY} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Stage>
  );
};
