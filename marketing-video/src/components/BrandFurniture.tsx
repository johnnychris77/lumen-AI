import React from "react";
import { theme } from "../theme";
import { FormatInfo } from "../format";

/**
 * Light brand furniture for the framed (square/vertical) cuts: a small wordmark
 * in the charcoal area ABOVE the scaled design band, so the letterbox reads as
 * an intentional social frame rather than empty bars. Landscape shows nothing.
 */
export const BrandFurniture: React.FC<{ fmt: FormatInfo }> = ({ fmt }) => {
  if (fmt.format === "landscape") return null;
  const topAreaHeight = fmt.bandTop;
  if (topAreaHeight < 90) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: Math.max(24, topAreaHeight * 0.34),
        left: 0,
        right: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
      }}
    >
      <svg width={34} height={34} viewBox="0 0 64 64">
        <circle cx="32" cy="32" r="26" fill="none" stroke={theme.color.teal} strokeWidth="5" />
        <circle cx="32" cy="32" r="12" fill="none" stroke={theme.color.primary} strokeWidth="5" />
        <circle cx="32" cy="32" r="3" fill={theme.color.onDark} />
      </svg>
      <span style={{ fontFamily: theme.font.sans, fontSize: 30, fontWeight: 700, color: theme.color.onDark, letterSpacing: 0.5 }}>
        LumenAI
      </span>
    </div>
  );
};
