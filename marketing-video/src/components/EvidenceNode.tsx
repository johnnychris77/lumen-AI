import React from "react";
import { theme } from "../theme";

/** A node in the governed evidence chain. */
export const EvidenceNode: React.FC<{
  label: string;
  timestamp?: string;
  opacity?: number;
  translateY?: number;
  emphasis?: boolean;
}> = ({ label, timestamp, opacity = 1, translateY = 0, emphasis = false }) => (
  <div
    style={{
      opacity,
      transform: `translateY(${translateY}px)`,
      display: "flex",
      alignItems: "center",
      gap: 14,
      background: emphasis ? "rgba(59,182,166,0.14)" : theme.color.charcoalPanel,
      border: `1px solid ${emphasis ? "rgba(59,182,166,0.55)" : "rgba(255,255,255,0.08)"}`,
      borderRadius: theme.radius.pill,
      padding: "12px 22px",
      minWidth: 300,
    }}
  >
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: 999,
        background: emphasis ? theme.color.teal : theme.color.primary,
        flexShrink: 0,
      }}
    />
    <div style={{ fontSize: 22, fontWeight: 600, color: theme.color.onDark, flex: 1 }}>{label}</div>
    {timestamp ? (
      <div style={{ fontSize: 14, fontFamily: theme.font.mono, color: theme.color.onDarkSoft }}>
        {timestamp}
      </div>
    ) : null}
  </div>
);
