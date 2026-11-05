import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, Kicker } from "../components/Stage";
import { DeviceSource } from "../components/DeviceSource";
import { WorkflowArrow } from "../components/WorkflowArrow";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";
import { demo } from "../data/demo";

/**
 * Scene 4 — Universal Image Acquisition (0:29–0:36).
 * Multiple COMPATIBLE image sources converge into LumenAI's acquisition layer
 * and become standardized inspection evidence. Vendor-neutral — designed around
 * compatible sources, not a single borescope manufacturer.
 */
export const UniversalCapture: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const hubIn = reveal(frame, durationInFrames * 0.4, 14);
  const lineP = progress(frame, durationInFrames * 0.42, durationInFrames * 0.7);
  const evidenceIn = reveal(frame, durationInFrames * 0.68, 14);

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", top: 70, left: 100 }}>
        <Kicker>Vendor-neutral image acquisition</Kicker>
      </div>

      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center" }}>
        {/* Sources */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18, marginLeft: 100 }}>
          {demo.imageSources.map((s, i) => {
            const r = reveal(frame, 8 + i * (fps * 0.16), 14);
            return <DeviceSource key={s.label} label={s.label} note={s.note} opacity={r.opacity} translateY={r.translateY} />;
          })}
        </div>

        {/* Converging lines */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
          <svg width={280} height={420} viewBox="0 0 280 420" style={{ opacity: lineP }}>
            {[70, 160, 250, 340].map((y) => (
              <path
                key={y}
                d={`M0 ${y} C 120 ${y}, 150 210, 280 210`}
                fill="none"
                stroke={theme.color.primary}
                strokeWidth={2.5}
                strokeDasharray={600}
                strokeDashoffset={600 * (1 - lineP)}
                opacity={0.7}
              />
            ))}
          </svg>
        </div>

        {/* Hub + output */}
        <div style={{ marginRight: 110, display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
          <div
            style={{
              opacity: hubIn.opacity,
              transform: `translateY(${hubIn.translateY}px)`,
              padding: "26px 34px",
              borderRadius: theme.radius.lg,
              background: "linear-gradient(180deg, rgba(46,125,175,0.22), rgba(59,182,166,0.14))",
              border: `1px solid rgba(59,182,166,0.5)`,
              textAlign: "center",
              minWidth: 320,
            }}
          >
            <div style={{ fontSize: 26, fontWeight: 700, color: theme.color.onDark }}>LumenAI</div>
            <div style={{ fontSize: 18, color: theme.color.onDarkSoft, marginTop: 4 }}>Image Acquisition</div>
          </div>
          <WorkflowArrow direction="down" length={40} progress={progress(frame, durationInFrames * 0.6, durationInFrames * 0.72)} color={theme.color.teal} />
          <div
            style={{
              opacity: evidenceIn.opacity,
              transform: `translateY(${evidenceIn.translateY}px)`,
              padding: "20px 28px",
              borderRadius: theme.radius.md,
              background: theme.color.charcoalPanel,
              border: `1px solid rgba(255,255,255,0.1)`,
              textAlign: "center",
              minWidth: 320,
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 600, color: theme.color.teal }}>Standardized Inspection Evidence</div>
          </div>
        </div>
      </div>

      <div style={{ position: "absolute", bottom: 230, left: 100, fontSize: 20, color: theme.color.onDarkSoft }}>
        Designed for compatible borescope and camera sources.
      </div>
    </Stage>
  );
};
