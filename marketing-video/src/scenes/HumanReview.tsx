import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { theme } from "../theme";
import { reveal, progress } from "../components/anim";

/**
 * Scene 6 — Human Authority (0:48–0:58).
 * The workflow pauses on "Review Required"; a qualified reviewer examines the
 * image, baseline, findings and evidence. Ends on the film's key line:
 * "AI assists. People decide." One of the strongest moments — kept calm.
 */
export const HumanReview: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = (p: number) => durationInFrames * p;

  const badgeIn = reveal(frame, 6, 14);
  const panelIn = reveal(frame, t(0.24), 16);
  const checkP = progress(frame, t(0.34), t(0.62));
  // The key line fades up and holds in the final third.
  const lineOpacity = interpolate(frame, [t(0.62), t(0.76)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Everything else dims slightly as the line takes over.
  const dim = interpolate(frame, [t(0.66), t(0.8)], [1, 0.28], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const reviewItems = ["Current image", "Approved baseline", "Findings", "Evidence"];

  return (
    <Stage mode="dark">
      <div style={{ position: "absolute", inset: 0, opacity: dim }}>
        {/* Status badge — workflow paused */}
        <div
          style={{
            position: "absolute",
            top: 110,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: badgeIn.opacity,
            transform: `translateY(${badgeIn.translateY}px)`,
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 14,
              background: "rgba(217,164,65,0.14)",
              border: `1px solid ${theme.color.amber}`,
              color: theme.color.amber,
              padding: "14px 26px",
              borderRadius: theme.radius.pill,
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: 0.5,
            }}
          >
            <PauseIcon /> Review Required · Provisional Result
          </div>
        </div>

        {/* Reviewer panel */}
        <div
          style={{
            position: "absolute",
            top: 230,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: panelIn.opacity,
            transform: `translateY(${panelIn.translateY}px)`,
          }}
        >
          <div
            style={{
              width: 760,
              background: theme.color.charcoalPanel,
              border: `1px solid rgba(255,255,255,0.1)`,
              borderRadius: theme.radius.lg,
              padding: 30,
            }}
          >
            <div style={{ fontSize: 20, color: theme.color.onDarkSoft, marginBottom: 18 }}>
              Qualified reviewer examines
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {reviewItems.map((label, i) => {
                const shown = checkP > (i + 1) / (reviewItems.length + 1);
                return (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      padding: "16px 20px",
                      borderRadius: theme.radius.md,
                      background: theme.color.charcoal2,
                      border: `1px solid rgba(255,255,255,0.06)`,
                    }}
                  >
                    <Check on={shown} />
                    <span style={{ fontSize: 21, color: theme.color.onDark, fontWeight: 500 }}>{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* THE line */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: lineOpacity,
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 68, fontWeight: 700, color: theme.color.onDark, letterSpacing: 0.5 }}>
            AI assists. <span style={{ color: theme.color.teal }}>People decide.</span>
          </div>
        </div>
      </div>
    </Stage>
  );
};

const PauseIcon: React.FC = () => (
  <svg width={22} height={22} viewBox="0 0 24 24" fill={theme.color.amber}>
    <rect x="6" y="5" width="4" height="14" rx="1" />
    <rect x="14" y="5" width="4" height="14" rx="1" />
  </svg>
);

const Check: React.FC<{ on: boolean }> = ({ on }) => (
  <div
    style={{
      width: 26,
      height: 26,
      borderRadius: 999,
      background: on ? theme.color.teal : "transparent",
      border: `2px solid ${on ? theme.color.teal : theme.color.inkFaint}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}
  >
    {on ? (
      <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="#08131f" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12 l4 4 L19 6" />
      </svg>
    ) : null}
  </div>
);
