import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { SyntheticBadge } from "../components/DataChrome";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 11 — Department Pass / Fair / Review Trends.
 * Longitudinal history becomes department-level trends. Illustrative synthetic
 * values only — never presented as validated outcomes.
 */
const DIST = [
  { label: "Pass", pct: 87, color: theme.color.green },
  { label: "Fair / Monitor", pct: 9, color: theme.color.amber },
  { label: "Review Required", pct: 4, color: theme.color.primary },
];

export const DepartmentTrends: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const barP = progress(frame, durationInFrames * 0.3, durationInFrames * 0.7);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 60, left: 100, right: 100, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Kicker>Department Trends</Kicker>
        <SyntheticBadge />
      </div>

      {/* metric tiles */}
      <div style={{ position: "absolute", top: 150, left: 100, right: 100 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 18 }}>
          {demo.department.map((m, i) => {
            const r = reveal(frame, 6 + i * (fps * 0.1), 12);
            return (
              <div key={m.label} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, background: theme.color.charcoalPanel, border: `1px solid rgba(255,255,255,0.09)`, borderRadius: theme.radius.md, padding: "20px 26px" }}>
                <div style={{ fontSize: 17, color: theme.color.onDarkSoft }}>{m.label}</div>
                <div style={{ fontSize: 40, fontWeight: 700, color: theme.color.onDark, marginTop: 4 }}>{m.value}</div>
                <div style={{ fontSize: 14, color: theme.color.inkFaint }}>{m.sub}</div>
              </div>
            );
          })}
        </div>

        {/* distribution bar */}
        <div style={{ marginTop: 26 }}>
          <div style={{ display: "flex", height: 34, borderRadius: 10, overflow: "hidden", border: `1px solid rgba(255,255,255,0.1)` }}>
            {DIST.map((d) => (
              <div key={d.label} style={{ width: `${d.pct * barP}%`, background: d.color, transition: "none" }} />
            ))}
            <div style={{ flex: 1, background: theme.color.charcoal2 }} />
          </div>
          <div style={{ display: "flex", gap: 24, marginTop: 12 }}>
            {DIST.map((d) => (
              <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 8, color: theme.color.onDarkSoft, fontSize: 16 }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: d.color }} />
                {d.label} · {d.pct}%
              </div>
            ))}
          </div>
        </div>
      </div>
    </Stage>
  );
};
