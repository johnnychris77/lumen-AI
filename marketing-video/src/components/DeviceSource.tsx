import React from "react";
import { theme } from "../theme";

/** Simple, brand-neutral device glyphs (no manufacturer marks). */
const Glyph: React.FC<{ kind: string; color: string }> = ({ kind, color }) => {
  const common = { fill: "none", stroke: color, strokeWidth: 2.4, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (kind === "USB Borescope") {
    return (
      <svg width={40} height={40} viewBox="0 0 40 40">
        <circle cx={12} cy={20} r={6} {...common} />
        <path d="M18 20 H34" {...common} />
        <path d="M30 16 v8" {...common} />
      </svg>
    );
  }
  if (kind === "External Camera") {
    return (
      <svg width={40} height={40} viewBox="0 0 40 40">
        <rect x={7} y={12} width={26} height={18} rx={3} {...common} />
        <circle cx={20} cy={21} r={5} {...common} />
        <path d="M14 12 l2-3 h8 l2 3" {...common} />
      </svg>
    );
  }
  if (kind === "Capture Device") {
    return (
      <svg width={40} height={40} viewBox="0 0 40 40">
        <rect x={8} y={11} width={24} height={18} rx={3} {...common} />
        <path d="M12 33 h16" {...common} />
        <path d="M20 29 v4" {...common} />
      </svg>
    );
  }
  // Existing Image / upload
  return (
    <svg width={40} height={40} viewBox="0 0 40 40">
      <rect x={8} y={9} width={24} height={22} rx={3} {...common} />
      <circle cx={16} cy={17} r={2.5} {...common} />
      <path d="M11 29 l7-7 5 5 3-3 3 3" {...common} />
    </svg>
  );
};

export const DeviceSource: React.FC<{
  label: string;
  note?: string;
  opacity?: number;
  translateY?: number;
  accent?: string;
}> = ({ label, note, opacity = 1, translateY = 0, accent = theme.color.primary }) => (
  <div
    style={{
      opacity,
      transform: `translateY(${translateY}px)`,
      display: "flex",
      alignItems: "center",
      gap: 16,
      background: theme.color.charcoalPanel,
      border: `1px solid rgba(255,255,255,0.08)`,
      borderRadius: theme.radius.md,
      padding: "16px 22px",
      minWidth: 320,
      boxShadow: theme.shadow.card,
    }}
  >
    <div
      style={{
        width: 60,
        height: 60,
        borderRadius: theme.radius.sm,
        background: "rgba(46,125,175,0.12)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      <Glyph kind={label} color={accent} />
    </div>
    <div>
      <div style={{ fontSize: 24, fontWeight: 600, color: theme.color.onDark }}>{label}</div>
      {note ? (
        <div style={{ fontSize: 16, color: theme.color.onDarkSoft, marginTop: 2 }}>{note}</div>
      ) : null}
    </div>
  </div>
);
