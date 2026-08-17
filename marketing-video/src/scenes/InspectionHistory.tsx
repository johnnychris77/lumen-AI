import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { SyntheticBadge, ResultBadge } from "../components/DataChrome";
import { theme } from "../theme";
import { reveal } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 10 — Instrument Inspection History.
 * A single inspection becomes part of the instrument's longitudinal history,
 * with Pass / Fair / Review results over time. Synthetic demonstration data.
 */
export const InspectionHistory: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 66, left: 100, right: 100, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <Kicker>Instrument Inspection History</Kicker>
          <div style={{ fontSize: 22, color: theme.color.onDarkSoft, marginTop: 8 }}>{demo.instrument.name} · {demo.instrument.id}</div>
        </div>
        <SyntheticBadge />
      </div>

      <div style={{ position: "absolute", top: 190, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ width: 900 }}>
          {demo.history.map((h, i) => {
            const r = reveal(frame, 8 + i * (fps * 0.2), 12);
            return (
              <div key={h.id} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: `1px solid rgba(255,255,255,0.08)` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 999, background: theme.color.primary }} />
                  <span style={{ fontSize: 24, fontWeight: 600, color: theme.color.onDark }}>{h.id}</span>
                </div>
                <ResultBadge result={h.result} />
              </div>
            );
          })}
        </div>
      </div>
    </Stage>
  );
};
