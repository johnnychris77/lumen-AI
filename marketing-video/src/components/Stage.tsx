import React from "react";
import { AbsoluteFill } from "remotion";
import { theme } from "../theme";

/**
 * Scene background primitive. `mode="dark"` = cinematic charcoal;
 * `mode="light"` = bright clinical environment. A subtle vignette / gradient
 * gives depth without drama.
 */
export const Stage: React.FC<{
  mode?: "dark" | "light";
  children: React.ReactNode;
}> = ({ mode = "dark", children }) => {
  const dark = mode === "dark";
  return (
    <AbsoluteFill
      style={{
        fontFamily: theme.font.sans,
        background: dark
          ? `radial-gradient(120% 120% at 50% 30%, ${theme.color.charcoal2} 0%, ${theme.color.charcoal} 70%)`
          : `linear-gradient(180deg, ${theme.color.white} 0%, ${theme.color.surface} 100%)`,
        color: dark ? theme.color.onDark : theme.color.ink,
      }}
    >
      {children}
      {/* Soft cinematic vignette on dark scenes. */}
      {dark ? (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(130% 100% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.42) 100%)",
            pointerEvents: "none",
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};

/** A bright clinical UI panel (used in the app / dashboard scenes). */
export const Panel: React.FC<{
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ style, children }) => (
  <div
    style={{
      background: theme.color.white,
      border: `1px solid ${theme.color.border}`,
      borderRadius: theme.radius.lg,
      boxShadow: theme.shadow.panel,
      ...style,
    }}
  >
    {children}
  </div>
);

/** Small uppercase eyebrow / kicker label. */
export const Kicker: React.FC<{
  children: React.ReactNode;
  tone?: "dark" | "light";
}> = ({ children, tone = "dark" }) => (
  <div
    style={{
      textTransform: "uppercase",
      letterSpacing: 3,
      fontSize: 16,
      fontWeight: 700,
      color: tone === "dark" ? theme.color.teal : theme.color.primary,
    }}
  >
    {children}
  </div>
);
