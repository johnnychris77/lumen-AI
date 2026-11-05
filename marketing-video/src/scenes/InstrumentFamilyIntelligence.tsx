import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { SyntheticBadge } from "../components/DataChrome";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 12 — Instrument-Family Intelligence.
 * Inspection patterns across instrument families: volume, Pass/Fair/Review
 * distribution, and the supporting signals. Does NOT claim failure prediction.
 */
const ASPECTS = ["Recurring observations", "Supervisor review activity", "Evidence completeness", "Baseline coverage"];

export const InstrumentFamilyIntelligence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const barP = progress(frame, durationInFrames * 0.28, durationInFrames * 0.66);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 60, left: 100, right: 100, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Kicker>Instrument-Family Intelligence</Kicker>
        <SyntheticBadge />
      </div>

      <div style={{ position: "absolute", top: 150, left: 100, right: 100 }}>
        {demo.families.map((f, i) => {
          const r = reveal(frame, 6 + i * (fps * 0.12), 12);
          return (
            <div key={f.name} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, display: "flex", alignItems: "center", gap: 22, padding: "12px 0", borderBottom: `1px solid rgba(255,255,255,0.07)` }}>
              <div style={{ width: 360, fontSize: 21, fontWeight: 600, color: theme.color.onDark }}>{f.name}</div>
              <div style={{ width: 120, fontSize: 16, color: theme.color.onDarkSoft }}>{f.volume} insp.</div>
              <div style={{ flex: 1, display: "flex", height: 22, borderRadius: 6, overflow: "hidden", border: `1px solid rgba(255,255,255,0.1)` }}>
                <div style={{ width: `${f.pass * barP}%`, background: theme.color.green }} />
                <div style={{ width: `${f.fair * barP}%`, background: theme.color.amber }} />
                <div style={{ width: `${f.review * barP}%`, background: theme.color.primary }} />
                <div style={{ flex: 1, background: theme.color.charcoal2 }} />
              </div>
            </div>
          );
        })}

        <div style={{ display: "flex", gap: 26, marginTop: 22, flexWrap: "wrap" }}>
          {ASPECTS.map((a) => (
            <div key={a} style={{ display: "flex", alignItems: "center", gap: 8, color: theme.color.onDarkSoft, fontSize: 16 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: theme.color.teal }} />
              {a}
            </div>
          ))}
          <div style={{ display: "flex", gap: 18, marginLeft: "auto" }}>
            {[["Pass", theme.color.green], ["Fair", theme.color.amber], ["Review", theme.color.primary]].map(([l, c]) => (
              <div key={l as string} style={{ display: "flex", alignItems: "center", gap: 7, color: theme.color.onDarkSoft, fontSize: 15 }}>
                <span style={{ width: 11, height: 11, borderRadius: 3, background: c as string }} />{l as string}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Stage>
  );
};
