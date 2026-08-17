import React from "react";
import { theme } from "../theme";

/**
 * Presentational caption box. Fade + placement are owned by `CaptionTrack`
 * (format-aware), so this is a pure styled box. The website player also renders
 * real <track> captions from the VTT; this burned-in line mirrors the same text
 * so the exported MP4 is self-describing.
 */
export const Caption: React.FC<{
  text: string;
  opacity: number;
  tone?: "dark" | "light";
  fontSize?: number;
  maxWidth?: number;
}> = ({ text, opacity, tone = "dark", fontSize = 30, maxWidth = 1200 }) => {
  const isDark = tone === "dark";
  return (
    <div style={{ display: "flex", justifyContent: "center", width: "100%", opacity }}>
      <div
        style={{
          maxWidth,
          textAlign: "center",
          fontFamily: theme.font.sans,
          fontSize,
          lineHeight: 1.4,
          fontWeight: 500,
          letterSpacing: 0.2,
          color: isDark ? theme.color.onDark : theme.color.ink,
          background: isDark ? "rgba(8, 14, 24, 0.42)" : "rgba(255, 255, 255, 0.7)",
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
