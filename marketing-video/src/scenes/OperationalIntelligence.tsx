import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { theme } from "../theme";
import { reveal } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 9 — From One Instrument to Organizational Intelligence (1:20–1:29).
 * One instrument becomes many; individual records organize into an executive
 * dashboard with restrained, non-diagnostic metrics.
 */
export const OperationalIntelligence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  // Dots multiply 1 → many, then give way to the dashboard.
  const dotCount = Math.round(interpolate(frame, [4, t(0.4)], [1, 60], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const dotsOpacity = interpolate(frame, [t(0.36), t(0.5)], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dashIn = reveal(frame, t(0.44), 16);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 66, left: 100 }}>
        <Kicker>Inspection Intelligence</Kicker>
      </div>

      {/* Multiplying instrument records */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: dotsOpacity,
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: 16, width: 620 }}>
          {Array.from({ length: 60 }).map((_, i) => (
            <div
              key={i}
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                background: i < dotCount ? "rgba(46,125,175,0.6)" : "transparent",
                border: i < dotCount ? `1px solid ${theme.color.primary}` : "1px solid transparent",
                transition: "none",
              }}
            />
          ))}
        </div>
      </div>

      {/* Executive dashboard */}
      <div
        style={{
          position: "absolute",
          left: 100,
          right: 100,
          top: 170,
          bottom: 150,
          opacity: dashIn.opacity,
          transform: `translateY(${dashIn.translateY}px)`,
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gridTemplateRows: "repeat(2, 1fr)", gap: 22, height: "100%" }}>
          {demo.metrics.map((m, i) => {
            const r = reveal(frame, t(0.48) + i * (fps * 0.12), 12);
            return (
              <div
                key={m.label}
                style={{
                  opacity: r.opacity,
                  transform: `translateY(${r.translateY}px)`,
                  background: theme.color.charcoalPanel,
                  border: `1px solid rgba(255,255,255,0.09)`,
                  borderRadius: theme.radius.md,
                  padding: "26px 30px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                }}
              >
                <div style={{ fontSize: 18, color: theme.color.onDarkSoft }}>{m.label}</div>
                <div style={{ fontSize: 46, fontWeight: 700, color: theme.color.onDark, marginTop: 6 }}>{m.value}</div>
                <div style={{ fontSize: 15, color: theme.color.inkFaint, marginTop: 4 }}>{m.sub}</div>
              </div>
            );
          })}
        </div>
      </div>
    </Stage>
  );
};
