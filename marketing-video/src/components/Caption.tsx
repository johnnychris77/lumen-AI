import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../theme";

/**
 * Burned-in caption line. The website player also renders real <track> captions
 * from the SRT; this on-screen line mirrors the same text so the exported MP4 is
 * self-describing on platforms that don't show the sidecar track.
 */
export const Caption: React.FC<{
  text: string;
  durationInFrames: number;
  tone?: "dark" | "light";
}> = ({ text, durationInFrames, tone = "dark" }) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);
  const isDark = tone === "dark";

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 64,
        display: "flex",
        justifyContent: "center",
        padding: "0 8%",
        opacity,
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          textAlign: "center",
          fontFamily: theme.font.sans,
          fontSize: 30,
          lineHeight: 1.4,
          fontWeight: 500,
          letterSpacing: 0.2,
          color: isDark ? theme.color.onDark : theme.color.ink,
          background: isDark
            ? "rgba(8, 14, 24, 0.42)"
            : "rgba(255, 255, 255, 0.7)",
          backdropFilter: "blur(6px)",
          padding: "16px 28px",
          borderRadius: theme.radius.md,
        }}
      >
        {text}
      </div>
    </div>
  );
};
