import React from "react";
import { theme } from "../theme";

const statusColor = (status: string): string => {
  if (/review required/i.test(status)) return theme.color.amber;
  if (/reviewed/i.test(status)) return theme.color.green;
  return theme.color.primary;
};

/** A compact inspection record card (used in history + dashboard scenes). */
export const InstrumentCard: React.FC<{
  id: string;
  status: string;
  opacity?: number;
  translateY?: number;
  scale?: number;
}> = ({ id, status, opacity = 1, translateY = 0, scale = 1 }) => (
  <div
    style={{
      opacity,
      transform: `translateY(${translateY}px) scale(${scale})`,
      background: theme.color.white,
      border: `1px solid ${theme.color.border}`,
      borderRadius: theme.radius.md,
      padding: "16px 20px",
      boxShadow: theme.shadow.soft,
      display: "flex",
      alignItems: "center",
      gap: 16,
      minWidth: 300,
    }}
  >
    <div
      style={{
        width: 44,
        height: 44,
        borderRadius: theme.radius.sm,
        background: theme.color.surfaceAlt,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      <svg width={24} height={24} viewBox="0 0 24 24">
        <path
          d="M4 14 L14 4 l6 6 L10 20 Z"
          fill="none"
          stroke={theme.color.primary}
          strokeWidth={1.8}
          strokeLinejoin="round"
        />
      </svg>
    </div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 20, fontWeight: 600, color: theme.color.ink }}>{id}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: 999,
            background: statusColor(status),
          }}
        />
        <span style={{ fontSize: 15, color: theme.color.inkSoft }}>{status}</span>
      </div>
    </div>
  </div>
);
