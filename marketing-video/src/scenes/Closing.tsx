import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { theme } from "../theme";

/**
 * Scene 10 — Close (1:29–1:35).
 * Return to the instrument, now wrapped in a subtle evidence history, then
 * resolve to the LumenAI lockup + CTA.
 */
export const Closing: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  const instrOpacity = interpolate(frame, [4, 20, t(0.5), t(0.66)], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const orbit = interpolate(frame, [0, durationInFrames], [0, 40]);
  const logoIn = interpolate(frame, [t(0.6), t(0.78)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ctaIn = interpolate(frame, [t(0.78), t(0.92)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <Stage mode="dark">
      {/* Instrument + orbiting evidence history */}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: instrOpacity }}>
        <div style={{ position: "relative", width: 560, height: 380 }}>
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width={420} height={90} viewBox="0 0 420 90">
              <rect x="40" y="34" width="320" height="20" rx="10" fill="#aeb9c6" />
              <circle cx="360" cy="44" r="16" fill="#12100d" stroke="#8b97a6" strokeWidth="4" />
              <rect x="14" y="24" width="44" height="40" rx="10" fill="#8b97a6" />
            </svg>
          </div>
          {Array.from({ length: 8 }).map((_, i) => {
            const angle = (i / 8) * Math.PI * 2 + (orbit * Math.PI) / 180;
            const rx = 250;
            const ry = 150;
            const x = 280 + Math.cos(angle) * rx;
            const y = 190 + Math.sin(angle) * ry;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: x,
                  top: y,
                  width: 10,
                  height: 10,
                  marginLeft: -5,
                  marginTop: -5,
                  borderRadius: 999,
                  background: i % 2 === 0 ? theme.color.teal : theme.color.primary,
                  opacity: 0.8,
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Logo lockup */}
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: logoIn }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <LogoMark />
          <span style={{ fontSize: 64, fontWeight: 700, color: theme.color.onDark, letterSpacing: 0.5 }}>LumenAI</span>
        </div>
        <div style={{ fontSize: 26, color: theme.color.onDarkSoft, marginTop: 14 }}>
          Inspection Intelligence for Sterile Processing
        </div>
        <div style={{ fontSize: 20, color: theme.color.teal, marginTop: 10, opacity: ctaIn }}>
          See more. Know more. Document what matters.
        </div>
      </div>

      {/* CTA */}
      <div style={{ position: "absolute", bottom: 120, left: 0, right: 0, textAlign: "center", opacity: ctaIn }}>
        <div
          style={{
            display: "inline-block",
            padding: "14px 30px",
            borderRadius: theme.radius.pill,
            background: theme.color.primary,
            color: "#fff",
            fontSize: 22,
            fontWeight: 600,
          }}
        >
          Request a Demonstration
        </div>
        <div style={{ marginTop: 14, fontSize: 20, fontFamily: theme.font.mono, color: theme.color.onDarkSoft }}>
          lumenai.opsbridgesolution.com
        </div>
      </div>
    </Stage>
  );
};

const LogoMark: React.FC = () => (
  <svg width={64} height={64} viewBox="0 0 64 64">
    <circle cx="32" cy="32" r="26" fill="none" stroke={theme.color.teal} strokeWidth="4" />
    <circle cx="32" cy="32" r="12" fill="none" stroke={theme.color.primary} strokeWidth="4" />
    <circle cx="32" cy="32" r="3" fill={theme.color.onDark} />
  </svg>
);
