import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { theme } from "../theme";
import { reveal } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 14 — Leadership Visibility.
 * The same evidence creates different value for SPD, quality, executive, and
 * investor/strategic audiences — LumenAI as the intelligence & evidence layer,
 * not just a borescope application.
 */
export const LeadershipView: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 60, left: 100 }}>
        <Kicker>Leadership Visibility</Kicker>
      </div>

      <div style={{ position: "absolute", top: 150, left: 100, right: 100, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 18 }}>
        {demo.leadership.map((col, i) => {
          const r = reveal(frame, 6 + i * (fps * 0.16), 12);
          const investor = col.audience.startsWith("Investor");
          return (
            <div key={col.audience} style={{ opacity: r.opacity, transform: `translateY(${r.translateY}px)`, background: investor ? "rgba(59,182,166,0.12)" : theme.color.charcoalPanel, border: `1px solid ${investor ? "rgba(59,182,166,0.5)" : "rgba(255,255,255,0.09)"}`, borderRadius: theme.radius.md, padding: "20px 20px" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: investor ? theme.color.teal : theme.color.onDark, minHeight: 48 }}>{col.audience}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
                {col.items.map((it) => (
                  <div key={it} style={{ display: "flex", alignItems: "flex-start", gap: 9, fontSize: 15.5, color: theme.color.onDarkSoft }}>
                    <span style={{ width: 6, height: 6, borderRadius: 999, background: investor ? theme.color.teal : theme.color.primary, marginTop: 7, flexShrink: 0 }} />
                    {it}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Stage>
  );
};
