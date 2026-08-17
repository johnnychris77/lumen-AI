import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { LumenImage } from "../components/LumenImage";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { mediaSrc } from "../media";

/**
 * Scene 2 — Today's Inspection Reality (0:08–0:18).
 * A modern SPD: a technician inspecting increasingly complex instruments, then
 * connecting a borescope with the internal channel on a monitor.
 * Principle: the technician is the expert; technology supports the technician.
 */
const INSTRUMENTS = [
  "Suction instrument",
  "Cannulated orthopedic",
  "Drill / reamer",
  "Rigid scope",
  "Flexible scope",
];

export const SPDReality: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const monitorReveal = reveal(frame, durationInFrames * 0.45, 18);
  const feedProgress = progress(frame, durationInFrames * 0.55, durationInFrames * 0.8);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 80, left: 100 }}>
        <Kicker>Sterile Processing</Kicker>
        <div style={{ fontSize: 30, color: theme.color.onDarkSoft, marginTop: 10, maxWidth: 720 }}>
          Increasingly complex instruments — each inspected by a professional.
        </div>
      </div>

      {/* Instrument sequence (staggered chips) */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 250,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          width: 520,
        }}
      >
        {INSTRUMENTS.map((label, i) => {
          const r = reveal(frame, 10 + i * (fps * 0.22), 14);
          const active = frame > 10 + i * (fps * 0.22) + 6;
          return (
            <div
              key={label}
              style={{
                opacity: r.opacity,
                transform: `translateX(${(1 - r.opacity) * -24}px)`,
                display: "flex",
                alignItems: "center",
                gap: 16,
                background: theme.color.charcoalPanel,
                border: `1px solid rgba(255,255,255,0.08)`,
                borderRadius: theme.radius.md,
                padding: "14px 20px",
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 999,
                  background: active ? theme.color.teal : theme.color.inkFaint,
                }}
              />
              <span style={{ fontSize: 22, color: theme.color.onDark, fontWeight: 500 }}>{label}</span>
            </div>
          );
        })}
      </div>

      {/* Borescope monitor */}
      <div
        style={{
          position: "absolute",
          right: 110,
          top: 210,
          opacity: monitorReveal.opacity,
          transform: `translateY(${monitorReveal.translateY}px)`,
        }}
      >
        <div
          style={{
            width: 560,
            background: "#0c1119",
            border: `10px solid #1c2634`,
            borderRadius: 16,
            padding: 18,
            boxShadow: theme.shadow.panel,
          }}
        >
          <div style={{ display: "flex", justifyContent: "center" }}>
            <LumenImage size={420} depth={0.35 + feedProgress * 0.3} src={mediaSrc("lumenMonitor")} />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 14,
              color: theme.color.onDarkSoft,
              fontSize: 16,
              fontFamily: theme.font.mono,
            }}
          >
            <span>BORESCOPE · LIVE</span>
            <span>CH 01 · internal channel</span>
          </div>
        </div>
        <div style={{ width: 200, height: 16, background: "#1c2634", borderRadius: 6, margin: "10px auto 0" }} />
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 230,
          left: 100,
          fontSize: 24,
          color: theme.color.teal,
          fontWeight: 600,
          letterSpacing: 1,
        }}
      >
        Inspection → Evidence → Decision
      </div>
    </Stage>
  );
};
